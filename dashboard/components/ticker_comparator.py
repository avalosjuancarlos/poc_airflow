"""Multi-Ticker Comparator Component"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.export import render_export_buttons
from config import (
    CHART_HEIGHT_COMPACT,
    CHART_HEIGHT_STANDARD,
    MAX_RECOMMENDED_TICKERS,
    NORMALIZATION_BASE,
    TRADING_DAYS_PER_YEAR,
)
from icons import ICON_BATCH, ICON_COMPARISON, ICON_CORRELATION, ICON_METRICS
from data import load_market_data


def normalize_prices(df: pd.DataFrame, base_date=None):
    """Normalize prices to start at configured base value for comparison"""
    if df.empty:
        return df

    df_sorted = df.sort_values("date")
    if base_date is None:
        base_date = df_sorted["date"].iloc[0]

    base_price = df_sorted[df_sorted["date"] <= base_date]["close"].iloc[-1]
    if base_price == 0:
        return df

    df_normalized = df_sorted.copy()
    df_normalized["normalized_close"] = (df_sorted["close"] / base_price) * NORMALIZATION_BASE
    return df_normalized


def plot_comparison(ticker_dfs: dict[str, pd.DataFrame]):
    """Plot normalized price comparison for multiple tickers"""
    fig = go.Figure()

    base_date = None
    for ticker, df in ticker_dfs.items():
        if not df.empty:
            if base_date is None:
                base_date = df.sort_values("date")["date"].iloc[0]
            df_norm = normalize_prices(df, base_date)
            fig.add_trace(
                go.Scatter(
                    x=df_norm["date"],
                    y=df_norm["normalized_close"],
                    name=ticker,
                    mode="lines",
                    line=dict(width=2),
                )
            )

    fig.update_layout(
        title=f"Price Comparison (Normalized to {NORMALIZATION_BASE})",
        xaxis_title="Date",
        yaxis_title=f"Normalized Price (Base = {NORMALIZATION_BASE})",
        height=CHART_HEIGHT_STANDARD,
        hovermode="x unified",
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
    )

    return fig


def calculate_correlation(ticker_dfs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Calculate correlation matrix between tickers"""
    if len(ticker_dfs) < 2:
        return pd.DataFrame()

    # Get overlapping dates
    all_dates = None
    for df in ticker_dfs.values():
        if not df.empty:
            df_dates = set(df["date"].dt.date)
            if all_dates is None:
                all_dates = df_dates
            else:
                all_dates = all_dates.intersection(df_dates)

    if not all_dates:
        return pd.DataFrame()

    # Create correlation dataframe
    correlation_data = {}
    for ticker, df in ticker_dfs.items():
        if not df.empty:
            df_filtered = df[df["date"].dt.date.isin(all_dates)].sort_values("date")
            if "daily_return" in df_filtered.columns:
                correlation_data[ticker] = df_filtered["daily_return"].values

    if len(correlation_data) < 2:
        return pd.DataFrame()

    corr_df = pd.DataFrame(correlation_data)
    return corr_df.corr()


def render_ticker_comparator(selected_tickers: list[str], days: int):
    """Render multi-ticker comparison view"""
    if not selected_tickers or len(selected_tickers) < 2:
        st.info("Select at least 2 tickers to compare")
        return

    st.subheader(f"{ICON_COMPARISON} Multi-Ticker Comparison")

    # Load data for all tickers
    ticker_dfs = {}
    with st.spinner("Loading comparison data..."):
        for ticker in selected_tickers:
            df = load_market_data(ticker, days)
            if not df.empty:
                ticker_dfs[ticker] = df

    if len(ticker_dfs) < 2:
        st.warning("Not enough data available for comparison")
        return

    # Comparison Chart
    st.plotly_chart(plot_comparison(ticker_dfs), use_container_width=True)

    # Comparative Metrics Table
    st.subheader(f"{ICON_METRICS} Comparative Metrics")

    metrics_data = []
    for ticker, df in ticker_dfs.items():
        if not df.empty:
            df_sorted = df.sort_values("date")
            latest = df_sorted.iloc[-1]
            first = df_sorted.iloc[0]

            total_return = ((latest["close"] - first["close"]) / first["close"]) * 100
            avg_vol = df["volatility_20d"].mean() * 100 if "volatility_20d" in df.columns else None
            current_rsi = latest.get("rsi")
            sharpe = (
                df["daily_return"].mean()
                / df["daily_return"].std()
                * (TRADING_DAYS_PER_YEAR**0.5)
                if "daily_return" in df.columns
                and df["daily_return"].notna().any()
                and df["daily_return"].std() > 0
                else None
            )

            metrics_data.append(
                {
                    "Ticker": ticker,
                    "Current Price": f"${latest['close']:.2f}",
                    "Total Return": f"{total_return:+.2f}%",
                    "Avg Volatility": f"{avg_vol:.2f}%" if avg_vol else "N/A",
                    "RSI": f"{current_rsi:.2f}" if pd.notna(current_rsi) else "N/A",
                    "Sharpe Ratio": f"{sharpe:.2f}" if sharpe else "N/A",
                }
            )

    if metrics_data:
        metrics_df = pd.DataFrame(metrics_data)
        st.dataframe(metrics_df, use_container_width=True, hide_index=True)

    # Correlation Analysis
    if len(ticker_dfs) >= 2:
        st.subheader(f"{ICON_CORRELATION} Correlation Analysis")
        corr_matrix = calculate_correlation(ticker_dfs)
        if not corr_matrix.empty:
            fig_corr = go.Figure(
                data=go.Heatmap(
                    z=corr_matrix.values,
                    x=corr_matrix.columns,
                    y=corr_matrix.index,
                    colorscale="RdBu",
                    zmid=0,
                    text=corr_matrix.values,
                    texttemplate="%{text:.2f}",
                    textfont={"size": 10},
                )
            )
            fig_corr.update_layout(
                title="Returns Correlation Matrix",
                height=CHART_HEIGHT_COMPACT,
            )
            st.plotly_chart(fig_corr, use_container_width=True)

    # Batch export for all tickers
    st.markdown("---")
    st.subheader(f"{ICON_BATCH} Batch Export")
    
    export_options = st.multiselect(
        "Select tickers to export",
        options=selected_tickers,
        default=selected_tickers,
        help="Select which tickers to include in the batch export",
        key="batch_export_tickers",
    )
    
    if export_options:
        # Combine all selected ticker data
        combined_data = []
        for ticker in export_options:
            if ticker in ticker_dfs and not ticker_dfs[ticker].empty:
                df = ticker_dfs[ticker].copy()
                combined_data.append(df)
        
        if combined_data:
            combined_df = pd.concat(combined_data, ignore_index=True)
            export_name = f"batch_{'_'.join(export_options)}"
            render_export_buttons(combined_df, export_name, prefix="batch_export")
        else:
            st.warning("No data available for selected tickers")

