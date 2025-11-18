import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config import (
    CHART_HEIGHT_COMPACT,
    CHART_HEIGHT_PRICE,
    CHART_HEIGHT_STANDARD,
    RSI_NEUTRAL_THRESHOLD,
    RSI_OVERBOUGHT_THRESHOLD,
    RSI_OVERSOLD_THRESHOLD,
)


def plot_price_chart(df: pd.DataFrame, ticker: str):
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        subplot_titles=(f"{ticker} - Price & Volume", "Volume"),
        row_heights=[0.7, 0.3],
    )

    # Candlestick doesn't support hovertemplate directly
    # Use hoverlabel for better formatting
    fig.add_trace(
        go.Candlestick(
            x=df["date"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="Price",
            hoverlabel=dict(
                bgcolor="rgba(255, 255, 255, 0.9)",
                bordercolor="rgba(0, 0, 0, 0.2)",
                font_size=12,
            ),
        ),
        row=1,
        col=1,
    )

    colors = [
        "green" if row["close"] >= row["open"] else "red" for _, row in df.iterrows()
    ]

    # Enhanced tooltip for volume
    hovertemplate_volume = (
        "<b>%{x|%Y-%m-%d}</b><br>"
        "Volume: %{y:,.0f}<br>"
        "<extra></extra>"
    )

    fig.add_trace(
        go.Bar(
            x=df["date"],
            y=df["volume"],
            name="Volume",
            marker_color=colors,
            hovertemplate=hovertemplate_volume,
        ),
        row=2,
        col=1,
    )

    fig.update_layout(
        height=CHART_HEIGHT_PRICE,
        showlegend=False,
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
    )

    fig.update_yaxes(title_text="Price ($)", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)
    return fig


def plot_moving_averages(df: pd.DataFrame, ticker: str):
    fig = go.Figure()

    # Enhanced tooltip template
    hovertemplate_base = (
        "<b>%{x|%Y-%m-%d}</b><br>"
        "Close: $%{y:.2f}<br>"
        "<extra></extra>"
    )

    hovertemplate_sma = (
        "<b>%{x|%Y-%m-%d}</b><br>"
        "%{fullData.name}: $%{y:.2f}<br>"
        "<extra></extra>"
    )

    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["close"],
            name="Close",
            line=dict(color="black", width=2),
            hovertemplate=hovertemplate_base,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["sma_7"],
            name="SMA 7",
            line=dict(color="blue", width=1, dash="dot"),
            hovertemplate=hovertemplate_sma,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["sma_14"],
            name="SMA 14",
            line=dict(color="orange", width=1, dash="dash"),
            hovertemplate=hovertemplate_sma,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["sma_20"],
            name="SMA 20",
            line=dict(color="red", width=1),
            hovertemplate=hovertemplate_sma,
        )
    )
    fig.update_layout(
        title=f"{ticker} - Price & Moving Averages",
        xaxis_title="Date",
        yaxis_title="Price ($)",
        height=CHART_HEIGHT_STANDARD,
        hovermode="x unified",
    )
    return fig


def plot_bollinger_bands(df: pd.DataFrame, ticker: str):
    fig = go.Figure()

    hovertemplate_band = (
        "<b>%{x|%Y-%m-%d}</b><br>"
        "%{fullData.name}: $%{y:.2f}<br>"
        "<extra></extra>"
    )

    hovertemplate_close = (
        "<b>%{x|%Y-%m-%d}</b><br>"
        "Close: $%{y:.2f}<br>"
        "<extra></extra>"
    )

    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["bb_upper"],
            name="Upper Band",
            line=dict(color="rgba(250, 128, 114, 0.5)", width=1),
            hovertemplate=hovertemplate_band,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["bb_middle"],
            name="Middle (SMA 20)",
            line=dict(color="blue", width=1),
            hovertemplate=hovertemplate_band,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["bb_lower"],
            name="Lower Band",
            line=dict(color="rgba(250, 128, 114, 0.5)", width=1),
            fill="tonexty",
            fillcolor="rgba(250, 128, 114, 0.1)",
            hovertemplate=hovertemplate_band,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["close"],
            name="Close",
            line=dict(color="black", width=2),
            hovertemplate=hovertemplate_close,
        )
    )
    fig.update_layout(
        title=f"{ticker} - Bollinger Bands",
        xaxis_title="Date",
        yaxis_title="Price ($)",
        height=CHART_HEIGHT_STANDARD,
        hovermode="x unified",
    )
    return fig


def plot_rsi(df: pd.DataFrame, ticker: str):
    fig = go.Figure()

    # Enhanced tooltip with RSI value and status
    hovertemplate_rsi = (
        "<b>%{x|%Y-%m-%d}</b><br>"
        "RSI: %{y:.2f}<br>"
        "%{customdata}<br>"
        "<extra></extra>"
    )

    # Add status indicator to customdata
    rsi_status = []
    for rsi_val in df["rsi"]:
        if pd.notna(rsi_val):
            if rsi_val > RSI_OVERBOUGHT_THRESHOLD:
                rsi_status.append("⚠️ Overbought")
            elif rsi_val < RSI_OVERSOLD_THRESHOLD:
                rsi_status.append("✅ Oversold")
            else:
                rsi_status.append("➡️ Neutral")
        else:
            rsi_status.append("N/A")

    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["rsi"],
            name="RSI",
            line=dict(color="purple", width=2),
            hovertemplate=hovertemplate_rsi,
            customdata=rsi_status,
        )
    )
    fig.add_hline(
        y=RSI_OVERBOUGHT_THRESHOLD,
        line_dash="dash",
        line_color="red",
        annotation_text="Overbought",
    )
    fig.add_hline(
        y=RSI_OVERSOLD_THRESHOLD,
        line_dash="dash",
        line_color="green",
        annotation_text="Oversold",
    )
    fig.add_hline(
        y=RSI_NEUTRAL_THRESHOLD,
        line_dash="dot",
        line_color="gray",
        annotation_text="Neutral",
    )
    fig.update_layout(
        title=f"{ticker} - RSI",
        xaxis_title="Date",
        yaxis_title="RSI",
        yaxis_range=[0, 100],
        height=CHART_HEIGHT_COMPACT,
        hovermode="x unified",
    )
    return fig


def plot_macd(df: pd.DataFrame, ticker: str):
    fig = go.Figure()

    # Enhanced tooltips for MACD
    hovertemplate_macd = (
        "<b>%{x|%Y-%m-%d}</b><br>"
        "MACD: %{y:.4f}<br>"
        "<extra></extra>"
    )

    hovertemplate_signal = (
        "<b>%{x|%Y-%m-%d}</b><br>"
        "Signal: %{y:.4f}<br>"
        "<extra></extra>"
    )

    hovertemplate_hist = (
        "<b>%{x|%Y-%m-%d}</b><br>"
        "Histogram: %{y:.4f}<br>"
        "<extra></extra>"
    )

    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["macd"],
            name="MACD",
            line=dict(color="blue", width=2),
            hovertemplate=hovertemplate_macd,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["macd_signal"],
            name="Signal",
            line=dict(color="red", width=2),
            hovertemplate=hovertemplate_signal,
        )
    )
    colors = ["green" if val >= 0 else "red" for val in df["macd_histogram"]]
    fig.add_trace(
        go.Bar(
            x=df["date"],
            y=df["macd_histogram"],
            name="Histogram",
            marker_color=colors,
            hovertemplate=hovertemplate_hist,
        )
    )
    fig.add_hline(y=0, line_dash="dot", line_color="gray")
    fig.update_layout(
        title=f"{ticker} - MACD",
        xaxis_title="Date",
        yaxis_title="MACD",
        height=CHART_HEIGHT_COMPACT,
        hovermode="x unified",
    )
    return fig


def plot_volatility(df: pd.DataFrame, ticker: str):
    fig = go.Figure()

    hovertemplate_vol = (
        "<b>%{x|%Y-%m-%d}</b><br>"
        "20-Day Volatility: %{y:.2f}%<br>"
        "<extra></extra>"
    )

    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["volatility_20d"] * 100,
            name="Volatility",
            line=dict(color="orange", width=2),
            fill="tozeroy",
            fillcolor="rgba(255, 165, 0, 0.1)",
            hovertemplate=hovertemplate_vol,
        )
    )
    fig.update_layout(
        title=f"{ticker} - 20-Day Volatility",
        xaxis_title="Date",
        yaxis_title="Volatility (%)",
        height=CHART_HEIGHT_COMPACT,
        hovermode="x unified",
    )
    return fig


def plot_returns(df: pd.DataFrame, ticker: str):
    fig = go.Figure()

    hovertemplate_ret = (
        "<b>%{x|%Y-%m-%d}</b><br>"
        "Daily Return: %{y:+.2f}%<br>"
        "<extra></extra>"
    )

    colors = ["green" if val >= 0 else "red" for val in df["daily_return"]]
    fig.add_trace(
        go.Bar(
            x=df["date"],
            y=df["daily_return"] * 100,
            name="Daily Return",
            marker_color=colors,
            hovertemplate=hovertemplate_ret,
        )
    )
    fig.add_hline(y=0, line_dash="dot", line_color="gray")
    fig.update_layout(
        title=f"{ticker} - Daily Returns",
        xaxis_title="Date",
        yaxis_title="Return (%)",
        height=CHART_HEIGHT_COMPACT,
        hovermode="x unified",
    )
    return fig

