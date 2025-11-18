"""
Transform Operators for Market Data DAG

Operators for data transformation and persistence.
"""

from datetime import timedelta
from typing import List

import pandas as pd
from market_data.config import BACKFILL_DAYS
from market_data.storage import check_parquet_exists, load_from_parquet, save_to_parquet
from market_data.transformers import calculate_technical_indicators
from market_data.utils import get_logger, log_execution

logger = get_logger(__name__)


def _get_validated_tickers_from_xcom(context) -> List[str]:
    """Retrieve validated tickers pushed by validate_ticker task."""
    ti = context["task_instance"]
    tickers = ti.xcom_pull(task_ids="validate_ticker", key="validated_tickers")
    return tickers or []


@log_execution()
def check_and_determine_dates(**context) -> dict:
    """
    Check if parquet exists and determine dates to fetch

    If parquet doesn't exist, returns list of BACKFILL_DAYS (default 120) for backfill.
    If exists, returns only execution_date.

    Args:
        context: Airflow context

    Returns:
        Dictionary with dates to process and backfill flag
    """
    execution_date = context["execution_date"]
    results = []
    tickers = _get_validated_tickers_from_xcom(context)

    if not tickers:
        raise ValueError("No validated tickers found for determine_dates task")

    for ticker in tickers:
        logger.set_context(
            task_id=context["task_instance"].task_id,
            ticker=ticker,
            execution_date=str(execution_date),
        )

        parquet_exists = check_parquet_exists(ticker)

        if not parquet_exists:
            logger.info(
                f"No parquet file found for {ticker}. Preparing backfill of {BACKFILL_DAYS} days"
            )

            dates = []
            for i in range(BACKFILL_DAYS - 1, -1, -1):
                date = execution_date - timedelta(days=i)
                dates.append(date.strftime("%Y-%m-%d"))

            logger.info(
                f"Backfill dates prepared: {dates[0]} to {dates[-1]}",
                extra={
                    "ticker": ticker,
                    "total_days": len(dates),
                    "start_date": dates[0],
                    "end_date": dates[-1],
                },
            )

            logger.metric("backfill.days", len(dates), {"ticker": ticker})
            logger.audit(
                "backfill_initiated",
                {"ticker": ticker, "days": len(dates), "reason": "no_existing_data"},
            )

            result = {"dates": dates, "is_backfill": True, "ticker": ticker}
        else:
            date_str = execution_date.strftime("%Y-%m-%d")
            logger.info(
                f"Parquet exists for {ticker}. Processing single date: {date_str}"
            )
            result = {"dates": [date_str], "is_backfill": False, "ticker": ticker}

        results.append(result)

    # Push to XCom
    context["task_instance"].xcom_push(key="dates_to_process", value=results)

    logger.clear_context()
    return results


@log_execution()
def fetch_multiple_dates(**context) -> List[dict]:
    """
    Fetch market data for multiple dates

    Args:
        context: Airflow context

    Returns:
        List of market data dictionaries
    """
    from market_data.config import (
        API_TIMEOUT,
        HEADERS,
        MAX_RETRIES,
        RETRY_DELAY,
        YAHOO_FINANCE_API_BASE_URL,
    )
    from market_data.utils import YahooFinanceClient

    # Get dates to process from previous task
    dates_info_list = context["task_instance"].xcom_pull(key="dates_to_process") or []

    if not dates_info_list:
        raise ValueError("No dates to process were found for fetch_multiple_dates")

    client = YahooFinanceClient(
        base_url=YAHOO_FINANCE_API_BASE_URL, headers=HEADERS, timeout=API_TIMEOUT
    )

    batch_results = []

    for dates_info in dates_info_list:
        dates = dates_info["dates"]
        ticker = dates_info["ticker"]
        is_backfill = dates_info["is_backfill"]

        logger.set_context(
            task_id=context["task_instance"].task_id,
            ticker=ticker,
            is_backfill=is_backfill,
        )

        logger.info(
            f"Fetching market data for {len(dates)} dates",
            extra={
                "ticker": ticker,
                "total_dates": len(dates),
                "is_backfill": is_backfill,
                "date_range": f"{dates[0]} to {dates[-1]}",
            },
        )

        market_data_list = []
        failed_dates = []

        for i, date in enumerate(dates, 1):
            try:
                logger.info(
                    f"Fetching {i}/{len(dates)}: {date}",
                    extra={"date": date, "progress": f"{i}/{len(dates)}"},
                )

                data = client.fetch_market_data(
                    ticker=ticker,
                    date=date,
                    max_retries=MAX_RETRIES,
                    retry_delay=RETRY_DELAY,
                )

                market_data_list.append(data)
                logger.debug(f"Successfully fetched data for {date}")

            except Exception as e:
                logger.warning(
                    f"Failed to fetch data for {date}: {e}",
                    extra={"date": date, "error": str(e)},
                )
                failed_dates.append(date)

        logger.info(
            f"Fetch complete: {len(market_data_list)} successful, {len(failed_dates)} failed",
            extra={
                "ticker": ticker,
                "successful": len(market_data_list),
                "failed": len(failed_dates),
                "failed_dates": failed_dates,
            },
        )

        if len(market_data_list) == 0:
            logger.error(
                "No data fetched for any date", extra={"ticker": ticker, "dates": dates}
            )
            raise ValueError(f"Failed to fetch data for all {len(dates)} dates")

        logger.metric(
            "fetch.multiple_dates.success",
            len(market_data_list),
            {"ticker": ticker, "is_backfill": is_backfill},
        )

        if failed_dates:
            logger.metric(
                "fetch.multiple_dates.failed",
                len(failed_dates),
                {"ticker": ticker},
            )

        batch_results.append(
            {
                "ticker": ticker,
                "market_data": market_data_list,
                "failed_dates": failed_dates,
                "dates": dates,
                "is_backfill": is_backfill,
            }
        )

        logger.audit(
            "multiple_dates_fetched",
            {
                "ticker": ticker,
                "successful": len(market_data_list),
                "failed": len(failed_dates),
                "is_backfill": is_backfill,
            },
        )

    # Push to XCom
    context["task_instance"].xcom_push(key="market_data_list", value=batch_results)

    logger.clear_context()
    return batch_results


@log_execution()
def transform_and_save(**context) -> dict:
    """
    Transform market data with technical indicators and save to Parquet

    This function ensures technical indicators are calculated correctly by:
    1. Loading existing historical data from Parquet (if exists)
    2. Combining with new data
    3. Recalculating ALL indicators on the complete dataset
    4. Saving the updated dataset back to Parquet

    Args:
        context: Airflow context

    Returns:
        Dictionary with transformation results
    """
    # Get data from previous task
    market_data_batches = (
        context["task_instance"].xcom_pull(key="market_data_list") or []
    )

    if not market_data_batches:
        raise ValueError("No market data batches found for transformation")

    summaries = []

    for batch in market_data_batches:
        ticker = batch["ticker"]
        market_data_list = batch["market_data"]
        is_backfill = batch["is_backfill"]

        logger.set_context(
            task_id=context["task_instance"].task_id,
            ticker=ticker,
            is_backfill=is_backfill,
        )

        logger.info(
            f"Starting transformation for {ticker}",
            extra={
                "ticker": ticker,
                "new_records": len(market_data_list),
                "is_backfill": is_backfill,
            },
        )

        historical_df = None
        if not is_backfill and check_parquet_exists(ticker):
            logger.info(
                f"Loading existing Parquet for {ticker} to recalculate indicators"
            )
            historical_df = load_from_parquet(ticker)
            logger.info(
                f"Loaded {len(historical_df)} historical records",
                extra={"historical_records": len(historical_df)},
            )

        df_transformed = calculate_technical_indicators(
            market_data_list, ticker, historical_df=historical_df
        )

        logger.info(
            f"Transformation complete. DataFrame shape: {df_transformed.shape}",
            extra={
                "rows": df_transformed.shape[0],
                "columns": df_transformed.shape[1],
                "column_names": list(df_transformed.columns),
            },
        )

        file_path = save_to_parquet(df_transformed, ticker, append=True)

        summary = {
            "ticker": ticker,
            "rows_processed": len(df_transformed),
            "columns": list(df_transformed.columns),
            "date_range": {
                "start": (
                    str(df_transformed["date"].min())
                    if not df_transformed.empty
                    else None
                ),
                "end": (
                    str(df_transformed["date"].max())
                    if not df_transformed.empty
                    else None
                ),
            },
            "file_path": file_path,
            "is_backfill": is_backfill,
        }

        if len(df_transformed) > 0:
            latest = df_transformed.iloc[-1]
            summary["latest_indicators"] = {
                "date": str(latest["date"]),
                "close": float(latest["close"]) if pd.notna(latest["close"]) else None,
                "sma_20": (
                    float(latest["sma_20"]) if pd.notna(latest["sma_20"]) else None
                ),
                "rsi": float(latest["rsi"]) if pd.notna(latest["rsi"]) else None,
                "macd": float(latest["macd"]) if pd.notna(latest["macd"]) else None,
            }

        logger.info(
            "Transform and save complete",
            extra={
                "ticker": ticker,
                "total_rows": len(df_transformed),
                "file_path": file_path,
            },
        )

        summaries.append(summary)

        logger.audit(
            "transformation_completed",
            {
                "ticker": ticker,
                "rows": len(df_transformed),
                "indicators_calculated": 12,
                "persisted": True,
            },
        )

    context["task_instance"].xcom_push(key="transformation_summary", value=summaries)
    logger.clear_context()
    return summaries
