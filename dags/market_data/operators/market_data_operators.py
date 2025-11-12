"""
Operators for Market Data DAG

Contains all the callable functions used by PythonOperators
"""

import logging

from market_data.config import (
    API_TIMEOUT,
    DEFAULT_TICKER,
    HEADERS,
    MAX_RETRIES,
    RETRY_DELAY,
    YAHOO_FINANCE_API_BASE_URL,
)
from market_data.utils import YahooFinanceClient, validate_ticker_format

logger = logging.getLogger(__name__)


def validate_ticker(**context):
    """
    Validate ticker configuration

    Args:
        context: Airflow context

    Returns:
        Validated ticker symbol

    Raises:
        ValueError: If ticker is invalid
    """
    dag_run = context["dag_run"]
    ticker = dag_run.conf.get("ticker", DEFAULT_TICKER)

    logger.info(f"Validating ticker: {ticker}")
    logger.info(f"Default ticker configured: {DEFAULT_TICKER}")

    # Validate and normalize ticker
    validated_ticker = validate_ticker_format(ticker)

    logger.info(f"Ticker validated: {validated_ticker}")

    # Save to XCom for downstream tasks
    context["task_instance"].xcom_push(key="validated_ticker", value=validated_ticker)

    return validated_ticker


def fetch_market_data(ticker: str, date: str, **context):
    """
    Fetch market data from Yahoo Finance API

    Args:
        ticker: Stock ticker symbol
        date: Date in YYYY-MM-DD format
        context: Airflow context

    Returns:
        Dictionary with market data
    """
    # Initialize API client
    client = YahooFinanceClient(
        base_url=YAHOO_FINANCE_API_BASE_URL, headers=HEADERS, timeout=API_TIMEOUT
    )

    # Fetch data
    market_data = client.fetch_market_data(
        ticker=ticker, date=date, max_retries=MAX_RETRIES, retry_delay=RETRY_DELAY
    )

    # Save to XCom
    context["task_instance"].xcom_push(key="market_data", value=market_data)

    return market_data


def process_market_data(**context):
    """
    Process and display market data

    Args:
        context: Airflow context

    Returns:
        Processed market data
    """
    # Get data from XCom
    market_data = context["task_instance"].xcom_pull(
        task_ids="fetch_market_data", key="market_data"
    )

    if not market_data:
        logger.warning("No market data retrieved")
        return None

    # Display formatted output
    logger.info("=" * 60)
    logger.info("MARKET DATA PROCESSED")
    logger.info("=" * 60)
    logger.info(f"Ticker: {market_data['ticker']}")
    logger.info(f"Date: {market_data['date']}")
    logger.info(f"Company: {market_data['metadata']['long_name']}")
    logger.info(f"Exchange: {market_data['exchange']}")
    logger.info(f"Currency: {market_data['currency']}")
    logger.info("-" * 60)
    logger.info("PRICES:")
    logger.info(f"  Open:   ${market_data['quote'].get('open')}")
    logger.info(f"  High:   ${market_data['quote'].get('high')}")
    logger.info(f"  Low:    ${market_data['quote'].get('low')}")
    logger.info(f"  Close:  ${market_data['quote'].get('close')}")

    volume = market_data["quote"].get("volume")
    if volume:
        logger.info(f"  Volume: {volume:,}")

    logger.info("-" * 60)
    logger.info(f"52-Week High: ${market_data['metadata']['fifty_two_week_high']}")
    logger.info(f"52-Week Low:  ${market_data['metadata']['fifty_two_week_low']}")
    logger.info("=" * 60)

    return market_data
