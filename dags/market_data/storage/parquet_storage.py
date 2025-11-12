"""
Parquet Storage Module

Handles saving and loading market data in Parquet format.
"""

import os
from pathlib import Path
from typing import Optional

import pandas as pd

from market_data.utils import get_logger, log_execution

logger = get_logger(__name__)

# Default storage location
DEFAULT_DATA_DIR = os.environ.get("MARKET_DATA_STORAGE_DIR", "/opt/airflow/data")


def get_parquet_path(ticker: str, data_dir: Optional[str] = None) -> str:
    """
    Get the path for a ticker's parquet file

    Args:
        ticker: Stock ticker symbol
        data_dir: Directory to store data (default: from env or /opt/airflow/data)

    Returns:
        Full path to parquet file
    """
    storage_dir = data_dir or DEFAULT_DATA_DIR
    Path(storage_dir).mkdir(parents=True, exist_ok=True)

    filename = f"{ticker.upper()}_market_data.parquet"
    return os.path.join(storage_dir, filename)


def check_parquet_exists(ticker: str, data_dir: Optional[str] = None) -> bool:
    """
    Check if parquet file exists for a ticker

    Args:
        ticker: Stock ticker symbol
        data_dir: Directory where data is stored

    Returns:
        True if file exists, False otherwise
    """
    file_path = get_parquet_path(ticker, data_dir)
    exists = os.path.exists(file_path)

    if exists:
        # Get file stats
        stat = os.stat(file_path)
        size_mb = stat.st_size / (1024 * 1024)
        logger.info(
            f"Parquet file exists for {ticker}",
            extra={
                "ticker": ticker,
                "path": file_path,
                "size_mb": round(size_mb, 2),
            },
        )
    else:
        logger.info(
            f"Parquet file does not exist for {ticker}",
            extra={"ticker": ticker, "expected_path": file_path},
        )

    return exists


@log_execution()
def save_to_parquet(
    df: pd.DataFrame,
    ticker: str,
    data_dir: Optional[str] = None,
    append: bool = True,
) -> str:
    """
    Save DataFrame to Parquet file

    Args:
        df: DataFrame to save
        ticker: Stock ticker symbol
        data_dir: Directory to store data
        append: If True and file exists, append new data (default: True)

    Returns:
        Path to saved file
    """
    file_path = get_parquet_path(ticker, data_dir)

    logger.info(
        f"Saving data to Parquet for {ticker}",
        extra={
            "ticker": ticker,
            "rows": len(df),
            "path": file_path,
            "append": append,
        },
    )

    # Ensure date column is datetime
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])

    if append and os.path.exists(file_path):
        # Load existing data
        logger.info("Appending to existing Parquet file")
        existing_df = pd.read_parquet(file_path)

        # Combine and deduplicate
        combined_df = pd.concat([existing_df, df], ignore_index=True)

        # Remove duplicates based on date (keep last)
        if "date" in combined_df.columns:
            combined_df = combined_df.drop_duplicates(subset=["date"], keep="last")
            combined_df = combined_df.sort_values("date").reset_index(drop=True)

        df_to_save = combined_df

        logger.info(
            "Data merged successfully",
            extra={
                "existing_rows": len(existing_df),
                "new_rows": len(df),
                "total_rows": len(df_to_save),
                "duplicates_removed": len(existing_df) + len(df) - len(df_to_save),
            },
        )
    else:
        df_to_save = df.sort_values("date").reset_index(drop=True) if "date" in df.columns else df
        logger.info("Creating new Parquet file")

    # Save to Parquet
    df_to_save.to_parquet(
        file_path,
        engine="pyarrow",
        compression="snappy",
        index=False,
    )

    # Get file stats
    stat = os.stat(file_path)
    size_mb = stat.st_size / (1024 * 1024)

    logger.info(
        f"Data saved successfully to {file_path}",
        extra={
            "ticker": ticker,
            "rows_saved": len(df_to_save),
            "file_size_mb": round(size_mb, 2),
            "path": file_path,
        },
    )

    logger.metric(
        "storage.parquet_saved",
        len(df_to_save),
        {"ticker": ticker, "size_mb": round(size_mb, 2)},
    )

    logger.audit(
        "data_persisted",
        {
            "ticker": ticker,
            "format": "parquet",
            "rows": len(df_to_save),
            "size_mb": round(size_mb, 2),
            "path": file_path,
        },
    )

    return file_path


@log_execution()
def load_from_parquet(ticker: str, data_dir: Optional[str] = None) -> pd.DataFrame:
    """
    Load DataFrame from Parquet file

    Args:
        ticker: Stock ticker symbol
        data_dir: Directory where data is stored

    Returns:
        DataFrame with market data

    Raises:
        FileNotFoundError: If parquet file doesn't exist
    """
    file_path = get_parquet_path(ticker, data_dir)

    if not os.path.exists(file_path):
        logger.error(
            f"Parquet file not found for {ticker}",
            extra={"ticker": ticker, "path": file_path},
        )
        raise FileNotFoundError(f"No parquet file found for {ticker} at {file_path}")

    logger.info(
        f"Loading data from Parquet for {ticker}",
        extra={"ticker": ticker, "path": file_path},
    )

    df = pd.read_parquet(file_path)

    # Get file stats
    stat = os.stat(file_path)
    size_mb = stat.st_size / (1024 * 1024)

    logger.info(
        f"Data loaded successfully from {file_path}",
        extra={
            "ticker": ticker,
            "rows_loaded": len(df),
            "file_size_mb": round(size_mb, 2),
            "columns": list(df.columns),
        },
    )

    logger.metric(
        "storage.parquet_loaded",
        len(df),
        {"ticker": ticker, "size_mb": round(size_mb, 2)},
    )

    logger.audit(
        "data_loaded",
        {
            "ticker": ticker,
            "format": "parquet",
            "rows": len(df),
            "date_range": f"{df['date'].min()} to {df['date'].max()}"
            if "date" in df.columns
            else "N/A",
        },
    )

    return df
