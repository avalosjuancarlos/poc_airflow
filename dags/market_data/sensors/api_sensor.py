"""
API Availability Sensor

Checks if Yahoo Finance API is available before fetching data
"""

import logging

from market_data.config import YAHOO_FINANCE_API_BASE_URL, HEADERS, API_TIMEOUT
from market_data.utils import YahooFinanceClient

logger = logging.getLogger(__name__)


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
