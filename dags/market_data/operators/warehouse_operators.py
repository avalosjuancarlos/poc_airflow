"""
Warehouse Operators for Market Data DAG

Operators for loading data to data warehouse.
"""

from typing import Dict, List

from market_data.utils import get_logger, log_execution
from market_data.warehouse import load_parquet_to_warehouse as warehouse_load_function

logger = get_logger(__name__)


def _get_validated_tickers(context) -> List[str]:
    ti = context["task_instance"]
    tickers = ti.xcom_pull(task_ids="validate_ticker", key="validated_tickers")
    return tickers or []


@log_execution()
def load_to_warehouse(**context) -> Dict[str, any]:
    """
    Load transformed market data from Parquet to Data Warehouse

    Reads ticker from previous task (validate_ticker) via XCom.

    Workflow:
    1. Get ticker from XCom
    2. Read Parquet file
    3. Load to Pandas DataFrame
    4. Create warehouse tables if needed
    5. Load using configured strategy (PostgreSQL dev / Redshift prod)

    Args:
        context: Airflow context

    Returns:
        Summary with load statistics
    """
    tickers = _get_validated_tickers(context)

    if not tickers:
        raise ValueError("No validated tickers available for warehouse load")

    summaries = []

    for ticker in tickers:
        logger.set_context(task_id=context["task_instance"].task_id, ticker=ticker)

        logger.info(
            f"Loading {ticker} data to warehouse",
            extra={"ticker": ticker, "task_id": context["task_instance"].task_id},
        )

        summary = warehouse_load_function(ticker, **context)

        logger.info(
            f"Warehouse load summary for {ticker}: {summary['records_loaded']} records loaded",
            extra={
                "ticker": ticker,
                "records_loaded": summary["records_loaded"],
                "total_in_warehouse": summary["total_in_warehouse"],
                "warehouse_type": summary["warehouse_type"],
            },
        )

        summaries.append(summary)

    logger.clear_context()
    context["task_instance"].xcom_push(key="warehouse_summary", value=summaries)
    return summaries
