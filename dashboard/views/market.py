from datetime import datetime

import pandas as pd
import streamlit as st

from config import ENVIRONMENT
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
    days = 180

    with sidebar:
        st.header("⚙️ Market Configuration")
        if tickers:
            selected_ticker = st.selectbox(
                "Select Ticker",
                options=tickers,
                index=0,
                help="Choose a stock ticker to analyze",
            )
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

        if st.button("🔄 Refresh Data", key="refresh_market_data"):
            st.cache_data.clear()
            st.rerun()

        st.markdown("---")
        st.header("📈 Summary")
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

    st.subheader("Market Data Dashboard")

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

    tabs = st.tabs(
        [
            "📊 Price & Volume",
            "📈 Moving Averages",
            "📉 Bollinger Bands",
            "⚡ RSI",
            "🌊 MACD",
            "💹 Returns & Volatility",
            "📋 Data Table",
        ]
    )

    with tabs[0]:
        st.plotly_chart(plot_price_chart(df, selected_ticker), use_container_width=True)
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
                df["daily_return"].mean() / df["daily_return"].std() * (252**0.5)
                if df["daily_return"].notna().any() and df["daily_return"].std() > 0
                else 0
            )
            st.metric("Sharpe Ratio", f"{sharpe:.2f}")

    with tabs[6]:
        st.subheader("📋 Raw Data")
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

        csv = df.to_csv(index=False)
        st.download_button(
            label="⬇️ Download CSV",
            data=csv,
            file_name=f"{selected_ticker}_market_data_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )

    st.markdown("---")
    st.caption(
        f"Market Data Dashboard v1.0 | Environment: {ENVIRONMENT.upper()} | "
        f"Showing {len(df)} records for {selected_ticker}"
    )

