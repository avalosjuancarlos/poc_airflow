"""
Warehouse Operators for Market Data DAG

Operators for loading data to data warehouse.
"""

from typing import Dict

from market_data.utils import get_logger, log_execution
from market_data.warehouse import load_parquet_to_warehouse as warehouse_load_function

logger = get_logger(__name__)


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
    # Get ticker from previous task
    params = context.get("params", {})
    ticker = params.get("ticker") or context["task_instance"].xcom_pull(
        key="validated_ticker"
    )

    logger.set_context(task_id=context["task_instance"].task_id, ticker=ticker)

    logger.info(
        f"Loading {ticker} data to warehouse",
        extra={"ticker": ticker, "task_id": context["task_instance"].task_id},
    )

    # Call warehouse load function
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

    logger.clear_context()
    return summary
