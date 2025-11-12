"""
Unit tests for Parquet storage
"""

import os
import tempfile
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from dags.market_data.storage.parquet_storage import (
    check_parquet_exists,
    get_parquet_path,
    load_from_parquet,
    save_to_parquet,
)


class TestGetParquetPath:
    """Test get_parquet_path function"""

    def test_default_directory(self):
        """Test with default directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {"MARKET_DATA_STORAGE_DIR": tmpdir}, clear=True):
                # Reload module to pick up new env var
                import importlib
                from dags.market_data.storage import parquet_storage
                importlib.reload(parquet_storage)
                
                path = parquet_storage.get_parquet_path("AAPL")
                assert tmpdir in path
                assert "AAPL_market_data.parquet" in path

    def test_custom_directory(self):
        """Test with custom directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = get_parquet_path("TSLA", data_dir=tmpdir)
            assert path == f"{tmpdir}/TSLA_market_data.parquet"

    def test_ticker_uppercase(self):
        """Test ticker is uppercased"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = get_parquet_path("aapl", data_dir=tmpdir)
            assert "AAPL_market_data.parquet" in path


class TestCheckParquetExists:
    """Test check_parquet_exists function"""

    def test_file_exists(self):
        """Test when file exists"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test parquet file
            test_path = os.path.join(tmpdir, "AAPL_market_data.parquet")
            df = pd.DataFrame({"col": [1, 2, 3]})
            df.to_parquet(test_path)

            exists = check_parquet_exists("AAPL", data_dir=tmpdir)
            assert exists is True

    def test_file_not_exists(self):
        """Test when file doesn't exist"""
        with tempfile.TemporaryDirectory() as tmpdir:
            exists = check_parquet_exists("AAPL", data_dir=tmpdir)
            assert exists is False


class TestSaveToParquet:
    """Test save_to_parquet function"""

    def test_save_new_file(self):
        """Test saving to new file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            df = pd.DataFrame(
                {
                    "date": pd.date_range("2023-11-01", periods=5),
                    "ticker": ["AAPL"] * 5,
                    "close": [100, 101, 102, 103, 104],
                }
            )

            file_path = save_to_parquet(df, "AAPL", data_dir=tmpdir, append=False)

            assert os.path.exists(file_path)
            assert "AAPL_market_data.parquet" in file_path

            # Verify content
            loaded = pd.read_parquet(file_path)
            assert len(loaded) == 5
            assert list(loaded.columns) == ["date", "ticker", "close"]

    def test_save_with_append(self):
        """Test appending to existing file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create initial file
            df1 = pd.DataFrame(
                {
                    "date": pd.date_range("2023-11-01", periods=3),
                    "ticker": ["AAPL"] * 3,
                    "close": [100, 101, 102],
                }
            )
            save_to_parquet(df1, "AAPL", data_dir=tmpdir, append=False)

            # Append new data
            df2 = pd.DataFrame(
                {
                    "date": pd.date_range("2023-11-04", periods=2),
                    "ticker": ["AAPL"] * 2,
                    "close": [103, 104],
                }
            )
            file_path = save_to_parquet(df2, "AAPL", data_dir=tmpdir, append=True)

            # Verify combined data
            loaded = pd.read_parquet(file_path)
            assert len(loaded) == 5
            assert loaded["close"].tolist() == [100, 101, 102, 103, 104]

    def test_save_with_duplicates(self):
        """Test deduplication when appending"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create initial file
            df1 = pd.DataFrame(
                {
                    "date": pd.date_range("2023-11-01", periods=3),
                    "ticker": ["AAPL"] * 3,
                    "close": [100, 101, 102],
                }
            )
            save_to_parquet(df1, "AAPL", data_dir=tmpdir, append=False)

            # Append with overlapping dates (should deduplicate)
            df2 = pd.DataFrame(
                {
                    "date": pd.date_range("2023-11-02", periods=3),
                    "ticker": ["AAPL"] * 3,
                    "close": [101.5, 102.5, 103.0],  # Updated values
                }
            )
            file_path = save_to_parquet(df2, "AAPL", data_dir=tmpdir, append=True)

            # Verify deduplication (should keep last values)
            loaded = pd.read_parquet(file_path)
            assert len(loaded) == 4  # Not 6
            # Should have kept last value for 2023-11-02
            nov2_value = loaded[loaded["date"] == "2023-11-02"]["close"].iloc[0]
            assert nov2_value == 101.5


class TestLoadFromParquet:
    """Test load_from_parquet function"""

    def test_load_existing_file(self):
        """Test loading existing parquet file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create file
            df = pd.DataFrame(
                {
                    "date": pd.date_range("2023-11-01", periods=5),
                    "ticker": ["AAPL"] * 5,
                    "close": [100, 101, 102, 103, 104],
                }
            )
            save_to_parquet(df, "AAPL", data_dir=tmpdir, append=False)

            # Load it back
            loaded = load_from_parquet("AAPL", data_dir=tmpdir)

            assert len(loaded) == 5
            assert loaded["ticker"].iloc[0] == "AAPL"
            pd.testing.assert_frame_equal(loaded, df)

    def test_load_nonexistent_file(self):
        """Test loading nonexistent file raises error"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(FileNotFoundError, match="No parquet file found"):
                load_from_parquet("AAPL", data_dir=tmpdir)

    def test_load_preserves_datatypes(self):
        """Test that datatypes are preserved"""
        with tempfile.TemporaryDirectory() as tmpdir:
            df = pd.DataFrame(
                {
                    "date": pd.to_datetime(["2023-11-01", "2023-11-02"]),
                    "ticker": ["AAPL", "AAPL"],
                    "close": [100.5, 101.5],
                    "volume": [1000000, 1100000],
                }
            )

            save_to_parquet(df, "AAPL", data_dir=tmpdir, append=False)
            loaded = load_from_parquet("AAPL", data_dir=tmpdir)

            assert loaded["date"].dtype == "datetime64[ns]"
            assert loaded["close"].dtype == "float64"
            assert loaded["volume"].dtype == "int64"

