"""
API Availability Sensor

Checks if Yahoo Finance API is available before fetching data
"""

from market_data.config import API_TIMEOUT, HEADERS, YAHOO_FINANCE_API_BASE_URL
from market_data.utils import YahooFinanceClient, get_logger, log_execution

logger = get_logger(__name__)


@log_execution()
def check_api_availability(**context):
    """
    Sensor function to check API availability

    Args:
        context: Airflow context

    Returns:
        bool: True if API is available for all requested tickers, False to retry
    """
    ti = context.get("task_instance")
    tickers = (
        ti.xcom_pull(task_ids="validate_ticker", key="validated_tickers")
        if ti
        else None
    )

    if not tickers:
        raise ValueError(
            "No tickers available for API availability check. Ensure validate_ticker produced at least one ticker."
        )

    client = YahooFinanceClient(
        base_url=YAHOO_FINANCE_API_BASE_URL, headers=HEADERS, timeout=API_TIMEOUT
    )

    for ticker in tickers:
        if not client.check_availability(ticker):
            logger.warning("API unavailable for ticker", extra={"ticker": ticker})
            return False

    return True
