import os
import streamlit as st


ENVIRONMENT = os.environ.get("ENVIRONMENT", "development").lower()
APP_TITLE = os.environ.get("DASHBOARD_TITLE", "Market Data Dashboard")
VIEW_LABELS = {
    "market": "Market Data Dashboard",
    "warehouse": "Warehouse Explorer",
}


def _str_to_bool(value, default=True):
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


ENABLE_MARKET_VIEW = _str_to_bool(os.environ.get("ENABLE_MARKET_VIEW", "true"))
ENABLE_WAREHOUSE_VIEW = _str_to_bool(os.environ.get("ENABLE_WAREHOUSE_VIEW", "true"))
DEFAULT_VIEW_SETTING = os.environ.get("DEFAULT_DASHBOARD_VIEW", "market").strip().lower()


def get_available_views():
    views = []
    if ENABLE_MARKET_VIEW:
        views.append("market")
    if ENABLE_WAREHOUSE_VIEW:
        views.append("warehouse")
    if not views:
        views.append("market")
    return views


def get_default_view(available_views):
    return (
        DEFAULT_VIEW_SETTING
        if DEFAULT_VIEW_SETTING in available_views
        else available_views[0]
    )


def render_view_selector(sidebar, available_views):
    default_view = get_default_view(available_views)
    default_index = available_views.index(default_view)
    with sidebar:
        st.subheader("Navigation")
        selected = st.radio(
            "Select experience",
            options=available_views,
            index=default_index,
            format_func=lambda value: VIEW_LABELS[value],
            key="view_selector",
        )
        st.divider()
    return selected


def get_database_config():
    if ENVIRONMENT == "development":
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
    if ENVIRONMENT == "staging":
        return {
            "host": os.environ.get("STAGING_WAREHOUSE_HOST"),
            "port": int(os.environ.get("STAGING_WAREHOUSE_PORT", "5439")),
            "database": os.environ.get("STAGING_WAREHOUSE_DATABASE"),
            "user": os.environ.get("STAGING_WAREHOUSE_USER"),
            "password": os.environ.get("STAGING_WAREHOUSE_PASSWORD"),
            "region": os.environ.get("STAGING_WAREHOUSE_REGION"),
            "type": "redshift",
        }
    return {
        "host": os.environ.get("PROD_WAREHOUSE_HOST"),
        "port": int(os.environ.get("PROD_WAREHOUSE_PORT", "5439")),
        "database": os.environ.get("PROD_WAREHOUSE_DATABASE"),
        "user": os.environ.get("PROD_WAREHOUSE_USER"),
        "password": os.environ.get("PROD_WAREHOUSE_PASSWORD"),
        "region": os.environ.get("PROD_WAREHOUSE_REGION"),
        "type": "redshift",
    }


def _get_int_config(env_key: str, default: int) -> int:
    """Get integer configuration from environment variable"""
    value = os.environ.get(env_key)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _get_float_config(env_key: str, default: float) -> float:
    """Get float configuration from environment variable"""
    value = os.environ.get(env_key)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


# Dashboard UI Configuration
# RSI thresholds
RSI_OVERBOUGHT_THRESHOLD = _get_float_config("DASHBOARD_RSI_OVERBOUGHT", 70.0)
RSI_OVERSOLD_THRESHOLD = _get_float_config("DASHBOARD_RSI_OVERSOLD", 30.0)
RSI_NEUTRAL_THRESHOLD = _get_float_config("DASHBOARD_RSI_NEUTRAL", 50.0)

# Volatility thresholds (multipliers)
VOLATILITY_HIGH_MULTIPLIER = _get_float_config("DASHBOARD_VOLATILITY_HIGH_MULT", 1.5)
VOLATILITY_LOW_MULTIPLIER = _get_float_config("DASHBOARD_VOLATILITY_LOW_MULT", 0.5)

# Chart dimensions
CHART_HEIGHT_PRICE = _get_int_config("DASHBOARD_CHART_HEIGHT_PRICE", 600)
CHART_HEIGHT_STANDARD = _get_int_config("DASHBOARD_CHART_HEIGHT_STANDARD", 500)
CHART_HEIGHT_COMPACT = _get_int_config("DASHBOARD_CHART_HEIGHT_COMPACT", 400)

# Financial calculations
TRADING_DAYS_PER_YEAR = _get_int_config("DASHBOARD_TRADING_DAYS_YEAR", 252)
NORMALIZATION_BASE = _get_int_config("DASHBOARD_NORMALIZATION_BASE", 100)

# Comparison limits
MAX_RECOMMENDED_TICKERS = _get_int_config("DASHBOARD_MAX_TICKERS_COMPARE", 5)

# Export configuration
EXCEL_SHEET_NAME = os.environ.get("DASHBOARD_EXCEL_SHEET_NAME", "Market Data")
EXPORT_DATE_FORMAT = os.environ.get("DASHBOARD_EXPORT_DATE_FORMAT", "%Y%m%d_%H%M%S")

