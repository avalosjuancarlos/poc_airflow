from datetime import datetime

import pandas as pd
import streamlit as st

from components.export import render_export_buttons
from components.kpi_panel import render_kpi_panel
from components.ticker_comparator import render_ticker_comparator
from config import ENVIRONMENT, TRADING_DAYS_PER_YEAR
from icons import (
    ICON_BOLLINGER,
    ICON_DATA_TABLE,
    ICON_MACD,
    ICON_MOVING_AVERAGES,
    ICON_PRICE,
    ICON_REFRESH,
    ICON_RETURNS,
    ICON_RSI,
    ICON_SETTINGS,
    ICON_SUMMARY,
    ICON_VOLATILITY,
)
from charts import (
    plot_bollinger_bands,
    plot_macd,
    plot_moving_averages,
    plot_price_chart,
    plot_returns,
    plot_rsi,
    plot_volatility,
)
from data import load_available_tickers, load_market_data, load_summary_stats


def render_market_dashboard_view(sidebar, on_empty_view=None):
    tickers = load_available_tickers()
    selected_ticker = None
    selected_tickers = []
    days = 180

    with sidebar:
        st.header(f"{ICON_SETTINGS} Market Configuration")
        
        # Mode selector: Single ticker or Comparison
        view_mode = st.radio(
            "View Mode",
            options=["Single Ticker", "Compare Tickers"],
            index=0,
            key="view_mode_selector",
            help="Analyze a single ticker or compare multiple tickers",
        )
        
        if tickers:
            if view_mode == "Single Ticker":
                selected_ticker = st.selectbox(
                    "Select Ticker",
                    options=tickers,
                    index=0,
                    help="Choose a stock ticker to analyze",
                    key="single_ticker_selector",
                )
                selected_tickers = [selected_ticker] if selected_ticker else []
            else:
                from config import MAX_RECOMMENDED_TICKERS

                selected_tickers = st.multiselect(
                    "Select Tickers to Compare",
                    options=tickers,
                    default=tickers[:2] if len(tickers) >= 2 else tickers[:1],
                    help=f"Select 2 or more tickers to compare (up to {MAX_RECOMMENDED_TICKERS} recommended)",
                    key="multi_ticker_selector",
                )
                selected_ticker = selected_tickers[0] if selected_tickers else None
        else:
            st.warning(
                "No market data available yet. You can still explore the warehouse or "
                "enter a ticker manually. Trigger the Airflow DAG to populate data."
            )
            manual_ticker = st.text_input(
                "Manual ticker (optional)",
                value="",
                placeholder="e.g. AAPL",
                help="Enter a ticker symbol to pre-select it once data exists",
                key="manual_ticker_input",
            )
            if manual_ticker.strip():
                selected_ticker = manual_ticker.strip().upper()
                selected_tickers = [selected_ticker]
            else:
                selected_ticker = None
                selected_tickers = []

        days_options = {
            "1 Month": 30,
            "3 Months": 90,
            "6 Months": 180,
            "1 Year": 365,
            "All Data": 3650,
        }
        selected_range = st.selectbox(
            "Date Range",
            options=list(days_options.keys()),
            index=2,
            key="date_range_selector",
        )
        days = days_options[selected_range]

        if st.button(f"{ICON_REFRESH} Refresh Data", key="refresh_market_data"):
            st.cache_data.clear()
            st.rerun()

        st.markdown("---")
        st.header(f"{ICON_SUMMARY} Summary")
        stats = load_summary_stats(selected_ticker) if selected_ticker else {}

        if stats:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Records", f"{stats.get('total_records', 0):,}")
            with col2:
                st.metric("Avg Price", f"${stats.get('avg_close', 0):.2f}")

            col3, col4 = st.columns(2)
            with col3:
                first_date = stats.get("first_date", "N/A")
                last_date = stats.get("last_date", "N/A")
                first_date_str = str(first_date) if first_date != "N/A" else "N/A"
                last_date_str = str(last_date) if last_date != "N/A" else "N/A"
                st.markdown(
                    f"""
                <div class="date-range-display">
                    <strong>Date Range</strong>
                    <div class="date-range-value">
                        {first_date_str}<br/>
                        to {last_date_str}
                    </div>
                </div>
                """,
                    unsafe_allow_html=True,
                )
            with col4:
                avg_vol = stats.get("avg_volatility")
                vol_count = stats.get("volatility_count", 0)
                if avg_vol is not None and not pd.isna(avg_vol) and vol_count > 0:
                    st.metric("Avg Volatility", f"{avg_vol * 100:.2f}%")
                else:
                    st.metric("Avg Volatility", "N/A")

    # Handle comparison mode
    if view_mode == "Compare Tickers" and len(selected_tickers) >= 2:
        render_ticker_comparator(selected_tickers, days)
        return
    elif view_mode == "Compare Tickers" and len(selected_tickers) < 2:
        st.info("👈 Select at least 2 tickers in the sidebar to compare them.")
        if on_empty_view:
            on_empty_view()
        return

    if not selected_ticker:
        st.info(
            "👈 Select or type a ticker in the sidebar to visualize market data. "
            "Need raw SQL access? Switch to *Warehouse Explorer* using the navigation menu."
        )
        if on_empty_view:
            on_empty_view()
        return

    with st.spinner(f"Loading data for {selected_ticker}..."):
        df = load_market_data(selected_ticker, days)

    if df.empty:
        st.warning(
            f"No market data found for `{selected_ticker}` in the configured warehouse."
        )
        st.info(
            "Verify the Airflow DAG execution or use the *Warehouse Explorer* view to inspect tables."
        )
        if on_empty_view:
            on_empty_view()
        return

    last_update = df["updated_at"].max() if "updated_at" in df.columns else "Unknown"
    st.caption(f"Last updated: {last_update}")

    # Enhanced KPI Panel
    render_kpi_panel(selected_ticker, df)

    tabs = st.tabs(
        [
            f"{ICON_PRICE} Price & Volume",
            f"{ICON_MOVING_AVERAGES} Moving Averages",
            f"{ICON_BOLLINGER} Bollinger Bands",
            f"{ICON_RSI} RSI",
            f"{ICON_MACD} MACD",
            f"{ICON_RETURNS} Returns & Volatility",
            f"{ICON_DATA_TABLE} Data Table",
        ]
    )

    with tabs[0]:
        st.plotly_chart(plot_price_chart(df, selected_ticker), use_container_width=True)
        
        # Export chart data
        chart_data = df[["date", "open", "high", "low", "close", "volume"]].copy()
        render_export_buttons(
            chart_data,
            f"{selected_ticker}_price_volume",
            prefix="price_chart_export",
        )
        
        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
        with col1:
            st.metric(
                "Current Price",
                f"${df['close'].iloc[-1]:.2f}",
                (
                    f"{df['daily_return'].iloc[-1] * 100:.2f}%"
                    if "daily_return" in df.columns
                    else None
                ),
            )
        with col2:
            st.metric("High (Period)", f"${df['high'].max():.2f}")
        with col3:
            st.metric("Low (Period)", f"${df['low'].min():.2f}")
        with col4:
            st.metric("Avg Volume", f"{df['volume'].mean():,.0f}")

    with tabs[1]:
        st.plotly_chart(
            plot_moving_averages(df, selected_ticker), use_container_width=True
        )
        
        # Export chart data
        ma_data = df[["date", "close", "sma_7", "sma_14", "sma_20"]].copy()
        render_export_buttons(
            ma_data,
            f"{selected_ticker}_moving_averages",
            prefix="ma_chart_export",
        )
        
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            st.metric(
                "SMA 7",
                f"${df['sma_7'].iloc[-1]:.2f}" if df["sma_7"].notna().any() else "N/A",
            )
        with col2:
            st.metric(
                "SMA 14",
                (
                    f"${df['sma_14'].iloc[-1]:.2f}"
                    if df["sma_14"].notna().any()
                    else "N/A"
                ),
            )
        with col3:
            st.metric(
                "SMA 20",
                (
                    f"${df['sma_20'].iloc[-1]:.2f}"
                    if df["sma_20"].notna().any()
                    else "N/A"
                ),
            )

    with tabs[2]:
        st.plotly_chart(
            plot_bollinger_bands(df, selected_ticker), use_container_width=True
        )
        
        # Export chart data
        bb_data = df[["date", "close", "bb_upper", "bb_middle", "bb_lower"]].copy()
        render_export_buttons(
            bb_data,
            f"{selected_ticker}_bollinger_bands",
            prefix="bb_chart_export",
        )
        
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            st.metric(
                "Upper Band",
                (
                    f"${df['bb_upper'].iloc[-1]:.2f}"
                    if df["bb_upper"].notna().any()
                    else "N/A"
                ),
            )
        with col2:
            st.metric(
                "Middle Band",
                (
                    f"${df['bb_middle'].iloc[-1]:.2f}"
                    if df["bb_middle"].notna().any()
                    else "N/A"
                ),
            )
        with col3:
            st.metric(
                "Lower Band",
                (
                    f"${df['bb_lower'].iloc[-1]:.2f}"
                    if df["bb_lower"].notna().any()
                    else "N/A"
                ),
            )

    with tabs[3]:
        st.plotly_chart(plot_rsi(df, selected_ticker), use_container_width=True)
        
        # Export chart data
        rsi_data = df[["date", "rsi"]].copy()
        render_export_buttons(
            rsi_data,
            f"{selected_ticker}_rsi",
            prefix="rsi_chart_export",
        )
        
        current_rsi = df["rsi"].iloc[-1] if df["rsi"].notna().any() else None
        if current_rsi:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Current RSI", f"{current_rsi:.2f}")
            with col2:
                if current_rsi > 70:
                    st.error("⚠️ Overbought (>70)")
                elif current_rsi < 30:
                    st.success("✅ Oversold (<30)")
                else:
                    st.info("➡️ Neutral (30-70)")

    with tabs[4]:
        st.plotly_chart(plot_macd(df, selected_ticker), use_container_width=True)
        
        # Export chart data
        macd_data = df[["date", "macd", "macd_signal", "macd_histogram"]].copy()
        render_export_buttons(
            macd_data,
            f"{selected_ticker}_macd",
            prefix="macd_chart_export",
        )
        
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            st.metric(
                "MACD",
                f"{df['macd'].iloc[-1]:.2f}" if df["macd"].notna().any() else "N/A",
            )
        with col2:
            st.metric(
                "Signal",
                (
                    f"{df['macd_signal'].iloc[-1]:.2f}"
                    if df["macd_signal"].notna().any()
                    else "N/A"
                ),
            )
        with col3:
            st.metric(
                "Histogram",
                (
                    f"{df['macd_histogram'].iloc[-1]:.2f}"
                    if df["macd_histogram"].notna().any()
                    else "N/A"
                ),
            )

    with tabs[5]:
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(plot_returns(df, selected_ticker), use_container_width=True)
        with col2:
            st.plotly_chart(plot_volatility(df, selected_ticker), use_container_width=True)
        
        # Export chart data
        returns_vol_data = df[["date", "daily_return", "volatility_20d"]].copy()
        render_export_buttons(
            returns_vol_data,
            f"{selected_ticker}_returns_volatility",
            prefix="returns_vol_chart_export",
        )

        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
        with col1:
            st.metric(
                "Avg Daily Return",
                (
                    f"{df['daily_return'].mean() * 100:.2f}%"
                    if df["daily_return"].notna().any()
                    else "N/A"
                ),
            )
        with col2:
            st.metric(
                "Std Dev Returns",
                (
                    f"{df['daily_return'].std() * 100:.2f}%"
                    if df["daily_return"].notna().any()
                    else "N/A"
                ),
            )
        with col3:
            avg_vol = df["volatility_20d"].mean()
            st.metric(
                "Avg Volatility",
                (
                    f"{avg_vol * 100:.2f}%"
                    if pd.notna(avg_vol) and df["volatility_20d"].notna().any()
                    else "N/A"
                ),
            )
        with col4:
            sharpe = (
                df["daily_return"].mean()
                / df["daily_return"].std()
                * (TRADING_DAYS_PER_YEAR**0.5)
                if df["daily_return"].notna().any() and df["daily_return"].std() > 0
                else 0
            )
            st.metric("Sharpe Ratio", f"{sharpe:.2f}")

    with tabs[6]:
        st.subheader(f"{ICON_DATA_TABLE} Raw Data")
        col1, _ = st.columns([1, 3])
        with col1:
            show_all_columns = st.checkbox("Show All Columns", value=False)
        if show_all_columns:
            display_df = df
        else:
            display_df = df[
                [
                    "date",
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                    "sma_7",
                    "rsi",
                    "macd",
                    "volatility_20d",
                ]
            ]
        st.dataframe(
            display_df.sort_values("date", ascending=False),
            use_container_width=True,
            height=400,
        )

        # Enhanced Export with multiple formats
        render_export_buttons(df, selected_ticker, prefix="market_data_table")

    st.markdown("---")
    st.caption(
        f"Market Data Dashboard v1.0 | Environment: {ENVIRONMENT.upper()} | "
        f"Showing {len(df)} records for {selected_ticker}"
    )

