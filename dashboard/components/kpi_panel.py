"""Enhanced KPI Panel Component"""

from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from config import (
    RSI_NEUTRAL_THRESHOLD,
    RSI_OVERBOUGHT_THRESHOLD,
    RSI_OVERSOLD_THRESHOLD,
    VOLATILITY_HIGH_MULTIPLIER,
    VOLATILITY_LOW_MULTIPLIER,
)
from icons import ICON_KPI
from data import load_market_data


def calculate_percentage_changes(df: pd.DataFrame) -> dict:
    """Calculate percentage changes for different periods"""
    if df.empty or len(df) < 2:
        return {
            "1D": None,
            "7D": None,
            "30D": None,
            "YTD": None,
        }

    df_sorted = df.sort_values("date")
    current_price = df_sorted["close"].iloc[-1]
    current_date = df_sorted["date"].iloc[-1]

    changes = {}

    # 1 Day change
    if len(df_sorted) >= 2:
        prev_price = df_sorted["close"].iloc[-2]
        changes["1D"] = ((current_price - prev_price) / prev_price) * 100
    else:
        changes["1D"] = None

    # 7 Days change
    seven_days_ago = current_date - timedelta(days=7)
    df_7d = df_sorted[df_sorted["date"] <= seven_days_ago]
    if not df_7d.empty:
        price_7d = df_7d["close"].iloc[-1]
        changes["7D"] = ((current_price - price_7d) / price_7d) * 100
    else:
        changes["7D"] = None

    # 30 Days change
    thirty_days_ago = current_date - timedelta(days=30)
    df_30d = df_sorted[df_sorted["date"] <= thirty_days_ago]
    if not df_30d.empty:
        price_30d = df_30d["close"].iloc[-1]
        changes["30D"] = ((current_price - price_30d) / price_30d) * 100
    else:
        changes["30D"] = None

    # YTD change (from first day of current year)
    year_start = datetime(current_date.year, 1, 1)
    df_ytd = df_sorted[df_sorted["date"] <= year_start]
    if not df_ytd.empty:
        price_ytd = df_ytd["close"].iloc[-1]
        changes["YTD"] = ((current_price - price_ytd) / price_ytd) * 100
    else:
        changes["YTD"] = None

    return changes


def get_indicator_status(df: pd.DataFrame) -> dict:
    """Get status of key indicators with traffic light colors"""
    if df.empty:
        return {
            "rsi": {"value": None, "status": "neutral", "label": "N/A"},
            "macd": {"value": None, "status": "neutral", "label": "N/A"},
        }

    latest = df.iloc[-1]

    # RSI Status
    rsi = latest.get("rsi")
    if pd.notna(rsi):
        if rsi > RSI_OVERBOUGHT_THRESHOLD:
            rsi_status = "overbought"
            rsi_label = f"⚠️ Overbought (>{RSI_OVERBOUGHT_THRESHOLD:.0f})"
        elif rsi < RSI_OVERSOLD_THRESHOLD:
            rsi_status = "oversold"
            rsi_label = f"✅ Oversold (<{RSI_OVERSOLD_THRESHOLD:.0f})"
        else:
            rsi_status = "neutral"
            rsi_label = "➡️ Neutral"
    else:
        rsi_status = "neutral"
        rsi_label = "N/A"

    # MACD Status
    macd = latest.get("macd")
    macd_signal = latest.get("macd_signal")
    if pd.notna(macd) and pd.notna(macd_signal):
        if macd > macd_signal:
            macd_status = "bullish"
            macd_label = "📈 Bullish"
        else:
            macd_status = "bearish"
            macd_label = "📉 Bearish"
    else:
        macd_status = "neutral"
        macd_label = "N/A"

    return {
        "rsi": {"value": rsi, "status": rsi_status, "label": rsi_label},
        "macd": {"value": macd, "status": macd_status, "label": macd_label},
    }


def get_volatility_status(df: pd.DataFrame) -> dict:
    """Compare current volatility vs historical average"""
    if df.empty or "volatility_20d" not in df.columns:
        return {"current": None, "average": None, "status": "neutral", "label": "N/A"}

    valid_vol = df["volatility_20d"].dropna()
    if valid_vol.empty:
        return {"current": None, "average": None, "status": "neutral", "label": "N/A"}

    current_vol = valid_vol.iloc[-1] * 100
    avg_vol = valid_vol.mean() * 100

    if current_vol > avg_vol * VOLATILITY_HIGH_MULTIPLIER:
        status = "high"
        label = "⚠️ High"
    elif current_vol < avg_vol * VOLATILITY_LOW_MULTIPLIER:
        status = "low"
        label = "✅ Low"
    else:
        status = "normal"
        label = "➡️ Normal"

    return {
        "current": current_vol,
        "average": avg_vol,
        "status": status,
        "label": label,
    }


def render_kpi_panel(ticker: str, df: pd.DataFrame):
    """Render enhanced KPI panel with percentage changes and indicator status"""
    if df.empty:
        st.warning("No data available for KPI panel")
        return

    st.subheader(f"{ICON_KPI} Key Performance Indicators")

    # Calculate metrics
    changes = calculate_percentage_changes(df)
    indicators = get_indicator_status(df)
    volatility = get_volatility_status(df)

    # Current Price and Changes Row
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        current_price = df.sort_values("date")["close"].iloc[-1]
        st.metric("Current Price", f"${current_price:.2f}")

    with col2:
        delta_1d = changes.get("1D")
        if delta_1d is not None:
            st.metric("1D Change", f"{delta_1d:+.2f}%", delta=f"{delta_1d:+.2f}%")
        else:
            st.metric("1D Change", "N/A")

    with col3:
        delta_7d = changes.get("7D")
        if delta_7d is not None:
            st.metric("7D Change", f"{delta_7d:+.2f}%", delta=f"{delta_7d:+.2f}%")
        else:
            st.metric("7D Change", "N/A")

    with col4:
        delta_30d = changes.get("30D")
        if delta_30d is not None:
            st.metric("30D Change", f"{delta_30d:+.2f}%", delta=f"{delta_30d:+.2f}%")
        else:
            st.metric("30D Change", "N/A")

    with col5:
        delta_ytd = changes.get("YTD")
        if delta_ytd is not None:
            st.metric("YTD Change", f"{delta_ytd:+.2f}%", delta=f"{delta_ytd:+.2f}%")
        else:
            st.metric("YTD Change", "N/A")

    st.divider()

    # Indicators and Volatility Row
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        rsi_info = indicators["rsi"]
        rsi_value = rsi_info["value"]
        if rsi_value is not None:
            st.metric("RSI", f"{rsi_value:.2f}", delta=rsi_info["label"], delta_color="off")
        else:
            st.metric("RSI", "N/A")

    with col2:
        macd_info = indicators["macd"]
        macd_value = macd_info["value"]
        if macd_value is not None:
            st.metric("MACD Signal", macd_info["label"], delta_color="off")
        else:
            st.metric("MACD Signal", "N/A")

    with col3:
        vol_info = volatility
        if vol_info["current"] is not None:
            st.metric(
                "Volatility",
                f"{vol_info['current']:.2f}%",
                delta=f"Avg: {vol_info['average']:.2f}%",
            )
        else:
            st.metric("Volatility", "N/A")

    with col4:
        vol_status = volatility["status"]
        if vol_status != "neutral":
            st.metric("Volatility Status", volatility["label"], delta_color="off")
        else:
            st.metric("Volatility Status", "N/A")

    # Visual Alerts
    alerts = []
    if indicators["rsi"]["status"] == "overbought":
        alerts.append(
            f"⚠️ RSI indicates overbought condition (>{RSI_OVERBOUGHT_THRESHOLD:.0f})"
        )
    elif indicators["rsi"]["status"] == "oversold":
        alerts.append(
            f"✅ RSI indicates oversold condition (<{RSI_OVERSOLD_THRESHOLD:.0f})"
        )

    if indicators["macd"]["status"] == "bullish":
        alerts.append("📈 MACD shows bullish signal")
    elif indicators["macd"]["status"] == "bearish":
        alerts.append("📉 MACD shows bearish signal")

    if volatility["status"] == "high":
        alerts.append("⚠️ Volatility is significantly above average")

    if alerts:
        st.info(" | ".join(alerts))

