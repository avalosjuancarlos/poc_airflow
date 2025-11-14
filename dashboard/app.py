"""
Market Data Dashboard - Streamlit Application

Web dashboard for visualizing market data and technical indicators.
Configurable for multiple environments (development, staging, production).
"""

import os
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
from sqlalchemy import create_engine, text

# ============================================================================
# Configuration
# ============================================================================

ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")
APP_TITLE = os.environ.get("DASHBOARD_TITLE", "Market Data Dashboard")
APP_PORT = int(os.environ.get("DASHBOARD_PORT", "8501"))


def get_database_config():
    """Get database configuration based on environment"""
    env = ENVIRONMENT.lower()

    if env == "development":
        # Default to warehouse-postgres for Docker, localhost for local dev
        default_host = os.environ.get("DEV_WAREHOUSE_HOST", "warehouse-postgres")
        return {
            "host": default_host,
            "port": int(os.environ.get("DEV_WAREHOUSE_PORT", "5432")),
            "database": os.environ.get(
                "DEV_WAREHOUSE_DATABASE", "market_data_warehouse"
            ),
            "user": os.environ.get("DEV_WAREHOUSE_USER", "warehouse_user"),
            "password": os.environ.get(
                "DEV_WAREHOUSE_PASSWORD", "CHANGE_ME_dev_warehouse_password"
            ),
            "type": "postgresql",
        }
    elif env == "staging":
        return {
            "host": os.environ.get("STAGING_WAREHOUSE_HOST"),
            "port": int(os.environ.get("STAGING_WAREHOUSE_PORT", "5439")),
            "database": os.environ.get("STAGING_WAREHOUSE_DATABASE"),
            "user": os.environ.get("STAGING_WAREHOUSE_USER"),
            "password": os.environ.get("STAGING_WAREHOUSE_PASSWORD"),
            "region": os.environ.get("STAGING_WAREHOUSE_REGION"),
            "type": "redshift",
        }
    else:  # production
        return {
            "host": os.environ.get("PROD_WAREHOUSE_HOST"),
            "port": int(os.environ.get("PROD_WAREHOUSE_PORT", "5439")),
            "database": os.environ.get("PROD_WAREHOUSE_DATABASE"),
            "user": os.environ.get("PROD_WAREHOUSE_USER"),
            "password": os.environ.get("PROD_WAREHOUSE_PASSWORD"),
            "region": os.environ.get("PROD_WAREHOUSE_REGION"),
            "type": "redshift",
        }


def get_connection_string():
    """Build SQLAlchemy connection string"""
    config = get_database_config()

    if config["type"] == "postgresql":
        return (
            f"postgresql://{config['user']}:{config['password']}@"
            f"{config['host']}:{config['port']}/{config['database']}"
        )
    else:  # redshift
        return (
            f"redshift+psycopg2://{config['user']}:{config['password']}@"
            f"{config['host']}:{config['port']}/{config['database']}"
        )


@st.cache_resource
def get_engine():
    """Create and cache database engine"""
    conn_string = get_connection_string()
    return create_engine(conn_string)


# ============================================================================
# Data Loading Functions
# ============================================================================


@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_available_tickers():
    """Load list of available tickers from warehouse"""
    engine = get_engine()

    query = """
    SELECT DISTINCT ticker
    FROM fact_market_data
    ORDER BY ticker
    """

    try:
        with engine.connect() as conn:
            df = pd.read_sql(text(query), conn)
            return df["ticker"].tolist()
    except Exception as e:
        st.error(f"Error loading tickers: {e}")
        return []


@st.cache_data(ttl=300)
def load_market_data(ticker, days=90):
    """Load market data for a specific ticker"""
    engine = get_engine()

    query = """
    SELECT
        date,
        open,
        high,
        low,
        close,
        volume,
        sma_7,
        sma_14,
        sma_20,
        rsi,
        macd,
        macd_signal,
        macd_histogram,
        bb_upper,
        bb_middle,
        bb_lower,
        daily_return,
        volatility_20d,
        created_at,
        updated_at
    FROM fact_market_data
    WHERE ticker = :ticker
        AND date >= CURRENT_DATE - :days * INTERVAL '1 day'
    ORDER BY date DESC
    """

    try:
        with engine.connect() as conn:
            df = pd.read_sql(
                text(query), conn, params={"ticker": ticker, "days": str(days)}
            )
            df["date"] = pd.to_datetime(df["date"])
            return df.sort_values("date")
    except Exception as e:
        st.error(f"Error loading data for {ticker}: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300)
def load_summary_stats(ticker):
    """Load summary statistics for a ticker"""
    engine = get_engine()

    query = """
    SELECT
        COUNT(*) as total_records,
        MIN(date) as first_date,
        MAX(date) as last_date,
        AVG(close) as avg_close,
        MIN(close) as min_close,
        MAX(close) as max_close,
        AVG(volume) as avg_volume,
        AVG(volatility_20d) FILTER (WHERE volatility_20d IS NOT NULL AND volatility_20d != 'NaN') as avg_volatility,
        COUNT(*) FILTER (WHERE volatility_20d IS NOT NULL AND volatility_20d != 'NaN') as volatility_count
    FROM fact_market_data
    WHERE ticker = :ticker
    """

    try:
        with engine.connect() as conn:
            df = pd.read_sql(text(query), conn, params={"ticker": ticker})
            return df.iloc[0].to_dict() if not df.empty else {}
    except Exception as e:
        st.error(f"Error loading summary for {ticker}: {e}")
        return {}


# ============================================================================
# Visualization Functions
# ============================================================================


def plot_price_chart(df, ticker):
    """Create candlestick chart with volume"""
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        subplot_titles=(f"{ticker} - Price & Volume", "Volume"),
        row_heights=[0.7, 0.3],
    )

    # Candlestick
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

    # Volume bars
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


def plot_moving_averages(df, ticker):
    """Plot price with moving averages"""
    fig = go.Figure()

    # Close price
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["close"],
            name="Close",
            line=dict(color="black", width=2),
        )
    )

    # SMA 7
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["sma_7"],
            name="SMA 7",
            line=dict(color="blue", width=1, dash="dot"),
        )
    )

    # SMA 14
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["sma_14"],
            name="SMA 14",
            line=dict(color="orange", width=1, dash="dash"),
        )
    )

    # SMA 20
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


def plot_bollinger_bands(df, ticker):
    """Plot Bollinger Bands"""
    fig = go.Figure()

    # Upper band
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["bb_upper"],
            name="Upper Band",
            line=dict(color="rgba(250, 128, 114, 0.5)", width=1),
        )
    )

    # Middle band (SMA 20)
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["bb_middle"],
            name="Middle (SMA 20)",
            line=dict(color="blue", width=1),
            fill=None,
        )
    )

    # Lower band
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

    # Close price
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


def plot_rsi(df, ticker):
    """Plot RSI indicator"""
    fig = go.Figure()

    # RSI line
    fig.add_trace(
        go.Scatter(
            x=df["date"], y=df["rsi"], name="RSI", line=dict(color="purple", width=2)
        )
    )

    # Overbought line (70)
    fig.add_hline(
        y=70, line_dash="dash", line_color="red", annotation_text="Overbought (70)"
    )

    # Oversold line (30)
    fig.add_hline(
        y=30, line_dash="dash", line_color="green", annotation_text="Oversold (30)"
    )

    # Middle line (50)
    fig.add_hline(y=50, line_dash="dot", line_color="gray", annotation_text="Neutral")

    fig.update_layout(
        title=f"{ticker} - RSI (Relative Strength Index)",
        xaxis_title="Date",
        yaxis_title="RSI",
        yaxis_range=[0, 100],
        height=400,
        hovermode="x unified",
    )

    return fig


def plot_macd(df, ticker):
    """Plot MACD indicator"""
    fig = go.Figure()

    # MACD line
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["macd"],
            name="MACD",
            line=dict(color="blue", width=2),
        )
    )

    # Signal line
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["macd_signal"],
            name="Signal",
            line=dict(color="red", width=2),
        )
    )

    # Histogram
    colors = ["green" if val >= 0 else "red" for val in df["macd_histogram"]]
    fig.add_trace(
        go.Bar(
            x=df["date"],
            y=df["macd_histogram"],
            name="Histogram",
            marker_color=colors,
        )
    )

    # Zero line
    fig.add_hline(y=0, line_dash="dot", line_color="gray")

    fig.update_layout(
        title=f"{ticker} - MACD",
        xaxis_title="Date",
        yaxis_title="MACD",
        height=400,
        hovermode="x unified",
    )

    return fig


def plot_volatility(df, ticker):
    """Plot volatility over time"""
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["volatility_20d"] * 100,  # Convert to percentage
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


def plot_returns(df, ticker):
    """Plot daily returns"""
    fig = go.Figure()

    colors = ["green" if val >= 0 else "red" for val in df["daily_return"]]

    fig.add_trace(
        go.Bar(
            x=df["date"],
            y=df["daily_return"] * 100,  # Convert to percentage
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


# ============================================================================
# Streamlit App
# ============================================================================


def main():
    """Main dashboard application"""

    # Page config
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Header
    st.title(f"📊 {APP_TITLE}")
    st.markdown(
        f"**Environment**: `{ENVIRONMENT}` | **Database**: `{get_database_config()['type'].upper()}`"
    )

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")

        # Ticker selection
        tickers = load_available_tickers()

        if not tickers:
            st.error("No tickers found in database. Run the DAG first!")
            st.stop()

        selected_ticker = st.selectbox(
            "Select Ticker",
            options=tickers,
            index=0 if tickers else None,
            help="Choose a stock ticker to analyze",
        )

        # Date range selection
        days_options = {
            "1 Month": 30,
            "3 Months": 90,
            "6 Months": 180,
            "1 Year": 365,
            "All Data": 3650,
        }

        selected_range = st.selectbox(
            "Date Range", options=list(days_options.keys()), index=2
        )

        days = days_options[selected_range]

        # Refresh data button
        if st.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.rerun()

        st.markdown("---")

        # Summary stats - Better layout for all screen sizes
        st.header("📈 Summary")
        stats = load_summary_stats(selected_ticker)

        if stats:
            # Two rows of two columns for better mobile/desktop consistency
            # First row
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Total Records", f"{stats.get('total_records', 0):,}")
            
            with col2:
                st.metric("Avg Price", f"${stats.get('avg_close', 0):.2f}")
            
            # Second row
            col3, col4 = st.columns(2)
            
            with col3:
                # Format date range with consistent styling matching metrics
                first_date = stats.get('first_date', 'N/A')
                last_date = stats.get('last_date', 'N/A')
                # Convert dates to strings if they are date objects
                first_date_str = str(first_date) if first_date != 'N/A' else 'N/A'
                last_date_str = str(last_date) if last_date != 'N/A' else 'N/A'
                
                st.markdown(f"""
                <div class="date-range-display">
                    <strong>Date Range</strong>
                    <div class="date-range-value">
                        {first_date_str}<br/>
                        to {last_date_str}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            with col4:
                # Calculate volatility properly - check if data exists first
                avg_vol = stats.get('avg_volatility')
                vol_count = stats.get('volatility_count', 0)
                
                if avg_vol is not None and not pd.isna(avg_vol) and vol_count > 0:
                    st.metric("Avg Volatility", f"{avg_vol * 100:.2f}%")
                else:
                    st.metric("Avg Volatility", "N/A")

    # Main content
    if not selected_ticker:
        st.info("👈 Select a ticker from the sidebar to view data")
        st.stop()

    # Load data
    with st.spinner(f"Loading data for {selected_ticker}..."):
        df = load_market_data(selected_ticker, days)

    if df.empty:
        st.warning(f"No data found for {selected_ticker}")
        st.stop()

    # Display last update
    last_update = df["updated_at"].max() if "updated_at" in df.columns else "Unknown"
    st.caption(f"Last updated: {last_update}")

    # Tabs for different visualizations
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

    # Tab 1: Price & Volume
    with tabs[0]:
        st.plotly_chart(plot_price_chart(df, selected_ticker), use_container_width=True)

        # Responsive columns
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

    # Tab 2: Moving Averages
    with tabs[1]:
        st.plotly_chart(
            plot_moving_averages(df, selected_ticker), use_container_width=True
        )

        # Responsive columns
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

    # Tab 3: Bollinger Bands
    with tabs[2]:
        st.plotly_chart(
            plot_bollinger_bands(df, selected_ticker), use_container_width=True
        )

        # Responsive columns
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

    # Tab 4: RSI
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

    # Tab 5: MACD
    with tabs[4]:
        st.plotly_chart(plot_macd(df, selected_ticker), use_container_width=True)

        # Responsive columns
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

    # Tab 6: Returns & Volatility
    with tabs[5]:
        col1, col2 = st.columns(2)

        with col1:
            st.plotly_chart(plot_returns(df, selected_ticker), use_container_width=True)

        with col2:
            st.plotly_chart(
                plot_volatility(df, selected_ticker), use_container_width=True
            )

        # Stats
        # Responsive columns
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
            # Calculate average volatility with proper NaN handling
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

    # Tab 7: Data Table
    with tabs[6]:
        st.subheader("📋 Raw Data")

        # Display options
        col1, col2 = st.columns([1, 3])
        with col1:
            show_all_columns = st.checkbox("Show All Columns", value=False)

        # Select columns to display
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

        # Display table
        st.dataframe(
            display_df.sort_values("date", ascending=False),
            use_container_width=True,
            height=400,
        )

        # Download button
        csv = df.to_csv(index=False)
        st.download_button(
            label="⬇️ Download CSV",
            data=csv,
            file_name=f"{selected_ticker}_market_data_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )

    # Footer
    st.markdown("---")
    st.caption(
        f"Market Data Dashboard v1.0 | Environment: {ENVIRONMENT} | "
        f"Showing {len(df)} records for {selected_ticker}"
    )


if __name__ == "__main__":
    main()
