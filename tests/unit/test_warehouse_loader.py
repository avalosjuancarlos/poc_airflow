"""
Unit tests for warehouse loader
"""

import tempfile
from datetime import datetime
from unittest.mock import MagicMock, Mock, call, patch

import pandas as pd
import pytest
from market_data.warehouse.loader import WarehouseLoader


class TestWarehouseLoaderInit:
    """Test WarehouseLoader initialization"""

    @patch("market_data.warehouse.loader.get_warehouse_config")
    @patch("market_data.warehouse.loader.get_warehouse_connection")
    def test_init_creates_connection(self, mock_get_connection, mock_get_config):
        """Test initialization creates warehouse connection"""
        mock_config = {"type": "postgresql", "host": "localhost"}
        mock_get_config.return_value = mock_config

        loader = WarehouseLoader()

        mock_get_config.assert_called_once()
        mock_get_connection.assert_called_once_with(mock_config)

    @patch("market_data.warehouse.loader.get_warehouse_config")
    @patch("market_data.warehouse.loader.get_warehouse_connection")
    def test_init_stores_config(self, mock_get_connection, mock_get_config):
        """Test initialization stores configuration"""
        mock_config = {"type": "postgresql", "host": "localhost"}
        mock_get_config.return_value = mock_config

        loader = WarehouseLoader()

        assert loader.config == mock_config


class TestPrepareDataframe:
    """Test _prepare_dataframe method"""

    @patch("market_data.warehouse.loader.get_warehouse_config")
    @patch("market_data.warehouse.loader.get_warehouse_connection")
    def test_prepare_filters_null_close_prices(
        self, mock_get_connection, mock_get_config
    ):
        """Test preparation filters out records with null close prices"""
        loader = WarehouseLoader()

        df = pd.DataFrame(
            {
                "date": ["2023-01-01", "2023-01-02", "2023-01-03"],
                "ticker": ["AAPL", "AAPL", "AAPL"],
                "close": [150.0, None, 155.0],
                "quote": [{"close": 150.0}, {"close": None}, {"close": 155.0}],
                "metadata": [{}, {}, {}],
                "timestamp": [1672531200, 1672617600, 1672704000],
                "regular_market_time": [1672531200, 1672617600, 1672704000],
            }
        )

        result = loader._prepare_dataframe(df)

        assert len(result) == 2
        assert result["close"].notna().all()

    @patch("market_data.warehouse.loader.get_warehouse_config")
    @patch("market_data.warehouse.loader.get_warehouse_connection")
    def test_prepare_converts_date_to_datetime(
        self, mock_get_connection, mock_get_config
    ):
        """Test preparation converts date column to datetime"""
        loader = WarehouseLoader()

        df = pd.DataFrame(
            {
                "date": ["2023-01-01", "2023-01-02"],
                "ticker": ["AAPL", "AAPL"],
                "close": [150.0, 155.0],
                "quote": [{}, {}],
                "metadata": [{}, {}],
            }
        )

        result = loader._prepare_dataframe(df)

        assert pd.api.types.is_datetime64_any_dtype(result["date"])

    @patch("market_data.warehouse.loader.get_warehouse_config")
    @patch("market_data.warehouse.loader.get_warehouse_connection")
    def test_prepare_excludes_nested_columns(
        self, mock_get_connection, mock_get_config
    ):
        """Test preparation excludes quote, metadata, timestamp columns"""
        loader = WarehouseLoader()

        df = pd.DataFrame(
            {
                "date": ["2023-01-01", "2023-01-02"],
                "ticker": ["AAPL", "AAPL"],
                "close": [150.0, 155.0],
                "quote": [{"close": 150.0}, {"close": 155.0}],
                "metadata": [{"symbol": "AAPL"}, {"symbol": "AAPL"}],
                "timestamp": [1672531200, 1672617600],
                "regular_market_time": [1672531200, 1672617600],
            }
        )

        result = loader._prepare_dataframe(df)

        assert "quote" not in result.columns
        assert "metadata" not in result.columns
        assert "timestamp" not in result.columns
        assert "regular_market_time" not in result.columns

    @patch("market_data.warehouse.loader.get_warehouse_config")
    @patch("market_data.warehouse.loader.get_warehouse_connection")
    def test_prepare_converts_nan_to_none(self, mock_get_connection, mock_get_config):
        """Test preparation converts NaN values to None"""
        loader = WarehouseLoader()

        df = pd.DataFrame(
            {
                "date": ["2023-01-01", "2023-01-02"],
                "ticker": ["AAPL", "AAPL"],
                "close": [150.0, 155.0],
                "sma_7": [150.0, None],
                "quote": [{}, {}],
                "metadata": [{}, {}],
            }
        )

        result = loader._prepare_dataframe(df)

        # Convert to dict to check None values
        records = result.to_dict("records")
        assert records[1]["sma_7"] is None


class TestCreateTables:
    """Test create_tables method"""

    @patch("market_data.warehouse.loader.get_warehouse_config")
    @patch("market_data.warehouse.loader.get_warehouse_connection")
    def test_create_tables_generates_ddl(self, mock_get_connection, mock_get_config):
        """Test create_tables generates proper DDL"""
        mock_config = {"type": "postgresql", "schema": "public"}
        mock_get_config.return_value = mock_config
        mock_connection = MagicMock()
        mock_conn_context = MagicMock()
        mock_get_connection.return_value.get_connection.return_value.__enter__.return_value = (
            mock_conn_context
        )

        loader = WarehouseLoader()
        loader.create_tables()

        # Verify execute was called
        assert mock_conn_context.execute.called

    @patch("market_data.warehouse.loader.get_warehouse_config")
    @patch("market_data.warehouse.loader.get_warehouse_connection")
    def test_create_tables_uses_correct_schema(
        self, mock_get_connection, mock_get_config
    ):
        """Test create_tables uses correct schema"""
        mock_config = {"type": "postgresql", "schema": "custom_schema"}
        mock_get_config.return_value = mock_config
        mock_connection = MagicMock()
        mock_conn_context = MagicMock()
        mock_get_connection.return_value.get_connection.return_value.__enter__.return_value = (
            mock_conn_context
        )

        loader = WarehouseLoader()
        loader.create_tables()

        # Check that the DDL includes the custom schema
        call_args = mock_conn_context.execute.call_args_list
        ddl_statements = [str(call[0][0]) for call in call_args]
        combined_ddl = " ".join(ddl_statements)

        assert "custom_schema" in combined_ddl.lower()


class TestLoadFromParquet:
    """Test load_from_parquet method"""

    @patch("market_data.warehouse.loader.get_warehouse_config")
    @patch("market_data.warehouse.loader.get_warehouse_connection")
    @patch("market_data.warehouse.loader.load_from_parquet")
    @patch("market_data.warehouse.loader.LOAD_STRATEGY", "upsert")
    def test_load_from_parquet_upsert_strategy(
        self, mock_load_parquet, mock_get_connection, mock_get_config
    ):
        """Test load_from_parquet with UPSERT strategy"""
        mock_config = {"type": "postgresql", "schema": "public"}
        mock_get_config.return_value = mock_config

        mock_df = pd.DataFrame(
            {
                "date": ["2023-01-01", "2023-01-02"],
                "ticker": ["AAPL", "AAPL"],
                "close": [150.0, 155.0],
            }
        )
        mock_load_parquet.return_value = mock_df

        mock_connection = MagicMock()
        mock_get_connection.return_value = mock_connection

        loader = WarehouseLoader()

        with patch.object(loader, "_load_upsert") as mock_upsert:
            loader.load_from_parquet("AAPL")
            mock_upsert.assert_called_once()

    @patch("market_data.warehouse.loader.get_warehouse_config")
    @patch("market_data.warehouse.loader.get_warehouse_connection")
    @patch("market_data.warehouse.loader.load_from_parquet")
    @patch("market_data.warehouse.loader.LOAD_STRATEGY", "append")
    def test_load_from_parquet_append_strategy(
        self, mock_load_parquet, mock_get_connection, mock_get_config
    ):
        """Test load_from_parquet with APPEND strategy"""
        mock_config = {"type": "postgresql", "schema": "public"}
        mock_get_config.return_value = mock_config

        mock_df = pd.DataFrame(
            {
                "date": ["2023-01-01", "2023-01-02"],
                "ticker": ["AAPL", "AAPL"],
                "close": [150.0, 155.0],
            }
        )
        mock_load_parquet.return_value = mock_df

        mock_connection = MagicMock()
        mock_get_connection.return_value = mock_connection

        loader = WarehouseLoader()

        with patch.object(loader, "_load_append") as mock_append:
            loader.load_from_parquet("AAPL")
            mock_append.assert_called_once()

    @patch("market_data.warehouse.loader.get_warehouse_config")
    @patch("market_data.warehouse.loader.get_warehouse_connection")
    @patch("market_data.warehouse.loader.load_from_parquet")
    @patch("market_data.warehouse.loader.LOAD_STRATEGY", "truncate_insert")
    def test_load_from_parquet_truncate_strategy(
        self, mock_load_parquet, mock_get_connection, mock_get_config
    ):
        """Test load_from_parquet with TRUNCATE_INSERT strategy"""
        mock_config = {"type": "postgresql", "schema": "public"}
        mock_get_config.return_value = mock_config

        mock_df = pd.DataFrame(
            {
                "date": ["2023-01-01", "2023-01-02"],
                "ticker": ["AAPL", "AAPL"],
                "close": [150.0, 155.0],
            }
        )
        mock_load_parquet.return_value = mock_df

        mock_connection = MagicMock()
        mock_get_connection.return_value = mock_connection

        loader = WarehouseLoader()

        with patch.object(loader, "_load_truncate_insert") as mock_truncate:
            loader.load_from_parquet("AAPL")
            mock_truncate.assert_called_once()

    @patch("market_data.warehouse.loader.get_warehouse_config")
    @patch("market_data.warehouse.loader.get_warehouse_connection")
    @patch("market_data.warehouse.loader.load_from_parquet")
    def test_load_from_parquet_creates_tables_if_not_exist(
        self, mock_load_parquet, mock_get_connection, mock_get_config
    ):
        """Test load_from_parquet creates tables if they don't exist"""
        mock_config = {"type": "postgresql", "schema": "public"}
        mock_get_config.return_value = mock_config

        mock_df = pd.DataFrame(
            {
                "date": ["2023-01-01"],
                "ticker": ["AAPL"],
                "close": [150.0],
            }
        )
        mock_load_parquet.return_value = mock_df

        mock_connection = MagicMock()
        mock_get_connection.return_value = mock_connection

        loader = WarehouseLoader()

        with patch.object(loader, "create_tables") as mock_create:
            with patch.object(loader, "_load_upsert"):
                loader.load_from_parquet("AAPL")
                mock_create.assert_called_once()


class TestLoadUpsert:
    """Test _load_upsert method"""

    @patch("market_data.warehouse.loader.get_warehouse_config")
    @patch("market_data.warehouse.loader.get_warehouse_connection")
    def test_upsert_processes_in_batches(self, mock_get_connection, mock_get_config):
        """Test UPSERT processes data in batches"""
        mock_config = {"type": "postgresql", "schema": "public"}
        mock_get_config.return_value = mock_config

        mock_connection = MagicMock()
        mock_conn_context = MagicMock()
        mock_get_connection.return_value = mock_connection
        mock_connection.get_connection.return_value.__enter__.return_value = (
            mock_conn_context
        )

        loader = WarehouseLoader()

        # Create dataframe with 2500 rows (should be 3 batches with BATCH_SIZE=1000)
        df = pd.DataFrame(
            {
                "date": [datetime(2023, 1, 1)] * 2500,
                "ticker": ["AAPL"] * 2500,
                "close": [150.0] * 2500,
            }
        )

        with patch("market_data.warehouse.loader.BATCH_SIZE", 1000):
            loader._load_upsert(df)

        # Should be called 3 times (3 batches)
        assert mock_conn_context.execute.call_count == 3

    @patch("market_data.warehouse.loader.get_warehouse_config")
    @patch("market_data.warehouse.loader.get_warehouse_connection")
    def test_upsert_returns_record_count(self, mock_get_connection, mock_get_config):
        """Test UPSERT returns correct record count"""
        mock_config = {"type": "postgresql", "schema": "public"}
        mock_get_config.return_value = mock_config

        mock_connection = MagicMock()
        mock_conn_context = MagicMock()
        mock_get_connection.return_value = mock_connection
        mock_connection.get_connection.return_value.__enter__.return_value = (
            mock_conn_context
        )

        loader = WarehouseLoader()

        df = pd.DataFrame(
            {
                "date": [datetime(2023, 1, 1), datetime(2023, 1, 2)],
                "ticker": ["AAPL", "AAPL"],
                "close": [150.0, 155.0],
            }
        )

        result = loader._load_upsert(df)

        assert result == 2


class TestLoadAppend:
    """Test _load_append method"""

    @patch("market_data.warehouse.loader.get_warehouse_config")
    @patch("market_data.warehouse.loader.get_warehouse_connection")
    def test_append_inserts_all_records(self, mock_get_connection, mock_get_config):
        """Test APPEND inserts all records"""
        mock_config = {"type": "postgresql", "schema": "public"}
        mock_get_config.return_value = mock_config

        mock_connection = MagicMock()
        mock_conn_context = MagicMock()
        mock_get_connection.return_value = mock_connection
        mock_connection.get_connection.return_value.__enter__.return_value = (
            mock_conn_context
        )

        loader = WarehouseLoader()

        df = pd.DataFrame(
            {
                "date": [datetime(2023, 1, 1), datetime(2023, 1, 2)],
                "ticker": ["AAPL", "AAPL"],
                "close": [150.0, 155.0],
            }
        )

        result = loader._load_append(df)

        assert result == 2
        assert mock_conn_context.execute.called


class TestLoadTruncateInsert:
    """Test _load_truncate_insert method"""

    @patch("market_data.warehouse.loader.get_warehouse_config")
    @patch("market_data.warehouse.loader.get_warehouse_connection")
    def test_truncate_deletes_existing_ticker_data(
        self, mock_get_connection, mock_get_config
    ):
        """Test TRUNCATE_INSERT deletes existing ticker data first"""
        mock_config = {"type": "postgresql", "schema": "public"}
        mock_get_config.return_value = mock_config

        mock_connection = MagicMock()
        mock_conn_context = MagicMock()
        mock_get_connection.return_value = mock_connection
        mock_connection.get_connection.return_value.__enter__.return_value = (
            mock_conn_context
        )

        loader = WarehouseLoader()

        df = pd.DataFrame(
            {
                "date": [datetime(2023, 1, 1)],
                "ticker": ["AAPL"],
                "close": [150.0],
            }
        )

        loader._load_truncate_insert(df)

        # Should call execute at least twice: DELETE + INSERT
        assert mock_conn_context.execute.call_count >= 2

        # First call should be DELETE
        first_call_sql = str(mock_conn_context.execute.call_args_list[0][0][0])
        assert "DELETE" in first_call_sql.upper()

    @patch("market_data.warehouse.loader.get_warehouse_config")
    @patch("market_data.warehouse.loader.get_warehouse_connection")
    def test_truncate_then_inserts_new_data(self, mock_get_connection, mock_get_config):
        """Test TRUNCATE_INSERT inserts data after deletion"""
        mock_config = {"type": "postgresql", "schema": "public"}
        mock_get_config.return_value = mock_config

        mock_connection = MagicMock()
        mock_conn_context = MagicMock()
        mock_get_connection.return_value = mock_connection
        mock_connection.get_connection.return_value.__enter__.return_value = (
            mock_conn_context
        )

        loader = WarehouseLoader()

        df = pd.DataFrame(
            {
                "date": [datetime(2023, 1, 1), datetime(2023, 1, 2)],
                "ticker": ["AAPL", "AAPL"],
                "close": [150.0, 155.0],
            }
        )

        result = loader._load_truncate_insert(df)

        assert result == 2
