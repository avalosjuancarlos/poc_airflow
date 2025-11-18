"""
Storage module for Market Data

Handles data persistence in various formats.
"""

from .parquet_storage import (
    check_parquet_exists,
    get_parquet_path,
    load_from_parquet,
    save_to_parquet,
)

__all__ = [
    "save_to_parquet",
    "load_from_parquet",
    "check_parquet_exists",
    "get_parquet_path",
]
