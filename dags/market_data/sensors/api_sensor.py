"""
API Availability Sensor

Checks if Yahoo Finance API is available before fetching data
"""

from market_data.config import API_TIMEOUT, HEADERS, YAHOO_FINANCE_API_BASE_URL
from market_data.utils import YahooFinanceClient, get_logger, log_execution

logger = get_logger(__name__)


@log_execution()
def check_api_availability(ticker: str, **context):
    """
    Sensor function to check API availability

    Args:
        ticker: Ticker symbol to check
        context: Airflow context

    Returns:
        bool: True if API is available, False to retry

    Raises:
        ValueError: If ticker is invalid
    """
    # Initialize API client
    client = YahooFinanceClient(
        base_url=YAHOO_FINANCE_API_BASE_URL, headers=HEADERS, timeout=API_TIMEOUT
    )

    # Check availability
    return client.check_availability(ticker)
