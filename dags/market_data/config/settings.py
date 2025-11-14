"""
Configuration settings for Market Data DAG

This module handles configuration with a triple fallback system:
1. Airflow Variables (highest priority)
2. Environment Variables
3. Default values (lowest priority)
"""

import logging
import os

from airflow.models import Variable

logger = logging.getLogger(__name__)


def get_config_value(airflow_key, env_key, default_value, value_type=str):
    """
    Get configuration value with fallback priority:
    1. Airflow Variable (can be changed from UI without restart)
    2. Environment Variable (configured in .env)
    3. Default value (hardcoded)

    Args:
        airflow_key: Name of Airflow variable (e.g., 'market_data.default_ticker')
        env_key: Name of environment variable (e.g., 'MARKET_DATA_DEFAULT_TICKER')
        default_value: Default value if not found anywhere
        value_type: Data type to return (str, int, bool, float)

    Returns:
        Configured value of specified type

    Example:
        >>> ticker = get_config_value('market_data.default_ticker', 'MARKET_DATA_DEFAULT_TICKER', 'AAPL')
        >>> # Searches in: Airflow Variable → ENV → Default
    """
    try:
        # Priority 1: Airflow Variable
        value = Variable.get(airflow_key, default_var=None)
        if value is not None:
            logger.debug(
                f"Config '{airflow_key}' obtained from Airflow Variable: {value}"
            )
            # Special handling for booleans
            if value_type == bool:
                return value.lower() in ("true", "1", "yes", "on")
            return value_type(value)
    except Exception as e:
        logger.debug(f"Could not get Airflow Variable '{airflow_key}': {e}")

    # Priority 2: Environment Variable
    env_value = os.environ.get(env_key)
    if env_value is not None:
        logger.debug(
            f"Config '{airflow_key}' obtained from ENV '{env_key}': {env_value}"
        )
        # Special handling for booleans
        if value_type == bool:
            return env_value.lower() in ("true", "1", "yes", "on")
        return value_type(env_value)

    # Priority 3: Default value
    logger.debug(f"Config '{airflow_key}' using default value: {default_value}")
    return value_type(default_value)


# ============================================================================
# Configuration Values
# ============================================================================

# ============================================================================
# Lazy Configuration Loading
# ============================================================================


def _get_yahoo_api_url():
    """Get Yahoo Finance API base URL"""
    return os.environ.get(
        "YAHOO_FINANCE_API_BASE_URL",
        "https://query2.finance.yahoo.com/v8/finance/chart",
    )


def _get_api_timeout():
    """Get API timeout value"""
    return int(os.environ.get("MARKET_DATA_API_TIMEOUT", "30"))


def _get_default_ticker():
    """Get default ticker with fallback"""
    return get_config_value(
        airflow_key="market_data.default_ticker",
        env_key="MARKET_DATA_DEFAULT_TICKER",
        default_value="AAPL",
        value_type=str,
    )


def _get_max_retries():
    """Get max retries with fallback"""
    return get_config_value(
        airflow_key="market_data.max_retries",
        env_key="MARKET_DATA_MAX_RETRIES",
        default_value="3",
        value_type=int,
    )


def _get_retry_delay():
    """Get retry delay with fallback"""
    return get_config_value(
        airflow_key="market_data.retry_delay",
        env_key="MARKET_DATA_RETRY_DELAY",
        default_value="5",
        value_type=int,
    )


def _get_sensor_poke_interval():
    """Get sensor poke interval with fallback"""
    return get_config_value(
        airflow_key="market_data.sensor_poke_interval",
        env_key="MARKET_DATA_SENSOR_POKE_INTERVAL",
        default_value="30",
        value_type=int,
    )


def _get_sensor_timeout():
    """Get sensor timeout with fallback"""
    return get_config_value(
        airflow_key="market_data.sensor_timeout",
        env_key="MARKET_DATA_SENSOR_TIMEOUT",
        default_value="600",
        value_type=int,
    )


def _get_backfill_days():
    """Get backfill days with fallback"""
    return get_config_value(
        airflow_key="market_data.backfill_days",
        env_key="MARKET_DATA_BACKFILL_DAYS",
        default_value="120",
        value_type=int,
    )


# Eagerly loaded values (no Airflow dependency)
YAHOO_FINANCE_API_BASE_URL = _get_yahoo_api_url()
API_TIMEOUT = _get_api_timeout()

# Lazily loaded values (try to load, fallback to ENV/default)
try:
    DEFAULT_TICKER = _get_default_ticker()
    MAX_RETRIES = _get_max_retries()
    RETRY_DELAY = _get_retry_delay()
    SENSOR_POKE_INTERVAL = _get_sensor_poke_interval()
    SENSOR_TIMEOUT = _get_sensor_timeout()
    BACKFILL_DAYS = _get_backfill_days()
except Exception as e:
    logger.debug(f"Could not load Airflow Variables, using ENV/defaults: {e}")
    # Fallback to environment variables only
    DEFAULT_TICKER = os.environ.get("MARKET_DATA_DEFAULT_TICKER", "AAPL")
    MAX_RETRIES = int(os.environ.get("MARKET_DATA_MAX_RETRIES", "3"))
    RETRY_DELAY = int(os.environ.get("MARKET_DATA_RETRY_DELAY", "5"))
    SENSOR_POKE_INTERVAL = int(os.environ.get("MARKET_DATA_SENSOR_POKE_INTERVAL", "30"))
    SENSOR_TIMEOUT = int(os.environ.get("MARKET_DATA_SENSOR_TIMEOUT", "600"))
    BACKFILL_DAYS = int(os.environ.get("MARKET_DATA_BACKFILL_DAYS", "120"))

# Exponential Backoff - Keep as ENV (feature flag)
SENSOR_EXPONENTIAL_BACKOFF = (
    os.environ.get("MARKET_DATA_SENSOR_EXPONENTIAL_BACKOFF", "true").lower() == "true"
)

# Headers to avoid API blocks
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/91.0.4472.124 Safari/537.36"
    ),
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
}


def log_configuration():
    """Log current configuration values"""
    try:
        logger.info("=" * 60)
        logger.info("MARKET DATA DAG CONFIGURATION")
        logger.info("=" * 60)
        logger.info(f"API Base URL: {YAHOO_FINANCE_API_BASE_URL}")
        logger.info(f"Default Ticker: {DEFAULT_TICKER}")
        logger.info(f"API Timeout: {API_TIMEOUT}s")
        logger.info(f"Max Retries: {MAX_RETRIES}")
        logger.info(f"Retry Delay: {RETRY_DELAY}s")
        logger.info(f"Sensor Poke Interval: {SENSOR_POKE_INTERVAL}s")
        logger.info(f"Sensor Timeout: {SENSOR_TIMEOUT}s")
        logger.info(f"Sensor Exponential Backoff: {SENSOR_EXPONENTIAL_BACKOFF}")
        logger.info(f"Backfill Days: {BACKFILL_DAYS}")
        logger.info("=" * 60)
    except Exception as e:
        logger.debug(f"Could not log configuration (likely in test mode): {e}")
