import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def plot_price_chart(df: pd.DataFrame, ticker: str):
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        subplot_titles=(f"{ticker} - Price & Volume", "Volume"),
        row_heights=[0.7, 0.3],
    )

    fig.add_trace(
        go.Candlestick(
            x=df["date"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="Price",
        ),
        row=1,
        col=1,
    )

    colors = [
        "green" if row["close"] >= row["open"] else "red" for _, row in df.iterrows()
    ]
    fig.add_trace(
        go.Bar(x=df["date"], y=df["volume"], name="Volume", marker_color=colors),
        row=2,
        col=1,
    )

    fig.update_layout(
        height=600,
        showlegend=False,
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
    )

    fig.update_yaxes(title_text="Price ($)", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)
    return fig


def plot_moving_averages(df: pd.DataFrame, ticker: str):
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["date"], y=df["close"], name="Close", line=dict(color="black", width=2)
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["sma_7"],
            name="SMA 7",
            line=dict(color="blue", width=1, dash="dot"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["sma_14"],
            name="SMA 14",
            line=dict(color="orange", width=1, dash="dash"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["sma_20"],
            name="SMA 20",
            line=dict(color="red", width=1),
        )
    )
    fig.update_layout(
        title=f"{ticker} - Price & Moving Averages",
        xaxis_title="Date",
        yaxis_title="Price ($)",
        height=500,
        hovermode="x unified",
    )
    return fig


def plot_bollinger_bands(df: pd.DataFrame, ticker: str):
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["bb_upper"],
            name="Upper Band",
            line=dict(color="rgba(250, 128, 114, 0.5)", width=1),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["bb_middle"],
            name="Middle (SMA 20)",
            line=dict(color="blue", width=1),
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
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["date"], y=df["close"], name="Close", line=dict(color="black", width=2)
        )
    )
    fig.update_layout(
        title=f"{ticker} - Bollinger Bands",
        xaxis_title="Date",
        yaxis_title="Price ($)",
        height=500,
        hovermode="x unified",
    )
    return fig


def plot_rsi(df: pd.DataFrame, ticker: str):
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["date"], y=df["rsi"], name="RSI", line=dict(color="purple", width=2)
        )
    )
    fig.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Overbought")
    fig.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Oversold")
    fig.add_hline(y=50, line_dash="dot", line_color="gray", annotation_text="Neutral")
    fig.update_layout(
        title=f"{ticker} - RSI",
        xaxis_title="Date",
        yaxis_title="RSI",
        yaxis_range=[0, 100],
        height=400,
        hovermode="x unified",
    )
    return fig


def plot_macd(df: pd.DataFrame, ticker: str):
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["macd"],
            name="MACD",
            line=dict(color="blue", width=2),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["macd_signal"],
            name="Signal",
            line=dict(color="red", width=2),
        )
    )
    colors = ["green" if val >= 0 else "red" for val in df["macd_histogram"]]
    fig.add_trace(
        go.Bar(
            x=df["date"],
            y=df["macd_histogram"],
            name="Histogram",
            marker_color=colors,
        )
    )
    fig.add_hline(y=0, line_dash="dot", line_color="gray")
    fig.update_layout(
        title=f"{ticker} - MACD",
        xaxis_title="Date",
        yaxis_title="MACD",
        height=400,
        hovermode="x unified",
    )
    return fig


def plot_volatility(df: pd.DataFrame, ticker: str):
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["volatility_20d"] * 100,
            name="Volatility",
            line=dict(color="orange", width=2),
            fill="tozeroy",
            fillcolor="rgba(255, 165, 0, 0.1)",
        )
    )
    fig.update_layout(
        title=f"{ticker} - 20-Day Volatility",
        xaxis_title="Date",
        yaxis_title="Volatility (%)",
        height=400,
        hovermode="x unified",
    )
    return fig


def plot_returns(df: pd.DataFrame, ticker: str):
    fig = go.Figure()
    colors = ["green" if val >= 0 else "red" for val in df["daily_return"]]
    fig.add_trace(
        go.Bar(
            x=df["date"],
            y=df["daily_return"] * 100,
            name="Daily Return",
            marker_color=colors,
        )
    )
    fig.add_hline(y=0, line_dash="dot", line_color="gray")
    fig.update_layout(
        title=f"{ticker} - Daily Returns",
        xaxis_title="Date",
        yaxis_title="Return (%)",
        height=400,
        hovermode="x unified",
    )
    return fig

