"""
Operators for Market Data DAG

Contains all the callable functions used by PythonOperators
"""

import json

from market_data.config import (
    API_TIMEOUT,
    DEFAULT_TICKERS,
    HEADERS,
    MAX_RETRIES,
    RETRY_DELAY,
    YAHOO_FINANCE_API_BASE_URL,
)
from market_data.utils import (
    YahooFinanceClient,
    get_logger,
    log_execution,
    validate_ticker_format,
)

logger = get_logger(__name__)


def _parse_ticker_inputs(raw_value):
    """Normalize ticker input into list of strings."""
    if raw_value is None:
        return []

    if isinstance(raw_value, (list, tuple, set)):
        candidates = list(raw_value)
    else:
        string_value = str(raw_value).strip()
        if not string_value:
            return []
        if string_value.startswith("[") and string_value.endswith("]"):
            try:
                parsed = json.loads(string_value)
                if isinstance(parsed, list):
                    candidates = parsed
                else:
                    candidates = [string_value]
            except json.JSONDecodeError:
                candidates = string_value.split(",")
        elif "," in string_value:
            candidates = string_value.split(",")
        else:
            candidates = [string_value]

    normalized = []
    for candidate in candidates:
        if candidate is None:
            continue
        ticker_str = str(candidate).strip()
        if not ticker_str:
            continue
        parts = [part.strip() for part in ticker_str.split(",") if part.strip()]
        normalized.extend(parts if parts else [ticker_str])
    return normalized


def _resolve_requested_tickers(context):
    """Resolve configured tickers from dag_run, params, or defaults."""
    dag_run = context.get("dag_run")
    conf = dag_run.conf if dag_run else {}
    params = context.get("params", {}) or {}

    candidates = (
        _parse_ticker_inputs(conf.get("tickers"))
        or _parse_ticker_inputs(conf.get("ticker"))
        or _parse_ticker_inputs(params.get("tickers"))
        or _parse_ticker_inputs(params.get("ticker"))
        or list(DEFAULT_TICKERS)
    )

    normalized = []
    for ticker in candidates:
        upper = ticker.strip().upper()
        if upper and upper not in normalized:
            normalized.append(upper)

    logger.info(
        "Resolved ticker request",
        extra={"requested": candidates, "resolved": normalized},
    )
    return normalized


@log_execution()
def validate_ticker(**context):
    """
    Validate ticker configuration (supports multiple tickers)

    Args:
        context: Airflow context

    Returns:
        List of validated ticker symbols

    Raises:
        ValueError: If any ticker is invalid
    """
    resolved_tickers = _resolve_requested_tickers(context)

    if not resolved_tickers:
        raise ValueError(
            "No tickers provided. Configure `tickers` in dag_run.conf/params or set MARKET_DATA_DEFAULT_TICKERS."
        )

    logger.info(f"Validating tickers: {resolved_tickers}")
    validated = [validate_ticker_format(ticker) for ticker in resolved_tickers]

    logger.info(f"Tickers validated: {validated}")

    context["task_instance"].xcom_push(key="validated_tickers", value=validated)
    return validated


@log_execution()
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


@log_execution()
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
