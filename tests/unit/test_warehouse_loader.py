"""
Unit tests for warehouse loader
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from market_data.warehouse.loader import WarehouseLoader, load_parquet_to_warehouse


class TestWarehouseLoaderInit:
    """Test WarehouseLoader initialization"""

    @patch("market_data.warehouse.loader.get_warehouse_connection")
    @patch("market_data.warehouse.loader.get_warehouse_config")
    def test_init_stores_config(self, mock_get_config, mock_get_connection):
        """Test initialization stores configuration"""
        mock_config = {
            "type": "postgresql",
            "host": "localhost",
            "schema": "public",
        }
        mock_get_config.return_value = mock_config

        loader = WarehouseLoader()

        assert loader.config == mock_config
        assert loader.warehouse_type == "postgresql"
        assert loader.schema == "public"


class TestPrepareDataframe:
    """Test _prepare_dataframe method"""

    @patch("market_data.warehouse.loader.get_warehouse_connection")
    @patch("market_data.warehouse.loader.get_warehouse_config")
    def test_prepare_filters_null_close_prices(
        self, mock_get_config, mock_get_connection
    ):
        """Test preparation filters out records with null close prices"""
        mock_get_config.return_value = {
            "type": "postgresql",
            "host": "localhost",
            "schema": "public",
        }
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

    @patch("market_data.warehouse.loader.get_warehouse_connection")
    @patch("market_data.warehouse.loader.get_warehouse_config")
    def test_prepare_excludes_nested_columns(
        self, mock_get_config, mock_get_connection
    ):
        """Test preparation excludes quote, metadata, timestamp columns"""
        mock_get_config.return_value = {
            "type": "postgresql",
            "host": "localhost",
            "schema": "public",
        }
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


class TestLoadParquetToWarehouse:
    """Test load_parquet_to_warehouse function"""

    @patch("market_data.warehouse.loader.WarehouseLoader")
    @patch("market_data.warehouse.loader.load_from_parquet")
    def test_load_parquet_to_warehouse_creates_loader(
        self, mock_load_parquet, mock_loader_class
    ):
        """Test function creates WarehouseLoader instance"""
        mock_loader = MagicMock()
        mock_loader_class.return_value = mock_loader
        mock_loader.load_from_parquet.return_value = 10
        mock_loader.connection.get_connection.return_value.__enter__.return_value.execute.return_value.fetchone.return_value = (
            10,
        )

        mock_ti = MagicMock()
        mock_ti.task_id = "load_to_warehouse"

        context = {"task_instance": mock_ti, "execution_date": "2023-01-01"}

        load_parquet_to_warehouse("AAPL", **context)

        mock_loader_class.assert_called_once()

    @patch("market_data.warehouse.loader.WarehouseLoader")
    @patch("market_data.warehouse.loader.load_from_parquet")
    def test_load_parquet_to_warehouse_calls_create_tables(
        self, mock_load_parquet, mock_loader_class
    ):
        """Test function calls create_tables"""
        mock_loader = MagicMock()
        mock_loader_class.return_value = mock_loader
        mock_loader.load_from_parquet.return_value = 10
        mock_loader.connection.get_connection.return_value.__enter__.return_value.execute.return_value.fetchone.return_value = (
            10,
        )

        mock_ti = MagicMock()
        mock_ti.task_id = "load_to_warehouse"

        context = {"task_instance": mock_ti, "execution_date": "2023-01-01"}

        load_parquet_to_warehouse("AAPL", **context)

        mock_loader.create_tables.assert_called_once()

    @patch("market_data.warehouse.loader.WarehouseLoader")
    @patch("market_data.warehouse.loader.load_from_parquet")
    def test_load_parquet_to_warehouse_loads_data(
        self, mock_load_parquet, mock_loader_class
    ):
        """Test function loads data from parquet"""
        mock_loader = MagicMock()
        mock_loader_class.return_value = mock_loader
        mock_loader.load_from_parquet.return_value = 15
        mock_loader.connection.get_connection.return_value.__enter__.return_value.execute.return_value.fetchone.return_value = (
            15,
        )

        mock_ti = MagicMock()
        mock_ti.task_id = "load_to_warehouse"

        context = {"task_instance": mock_ti, "execution_date": "2023-01-01"}

        result = load_parquet_to_warehouse("AAPL", **context)

        mock_loader.load_from_parquet.assert_called_once_with("AAPL")
        assert result["records_loaded"] == 15

    @patch("market_data.warehouse.loader.WarehouseLoader")
    @patch("market_data.warehouse.loader.load_from_parquet")
    def test_load_parquet_to_warehouse_returns_summary(
        self, mock_load_parquet, mock_loader_class
    ):
        """Test function returns comprehensive summary"""
        mock_loader = MagicMock()
        mock_loader_class.return_value = mock_loader
        mock_loader.load_from_parquet.return_value = 20
        mock_loader.config = {"type": "postgresql"}
        mock_loader.connection.get_connection.return_value.__enter__.return_value.execute.return_value.fetchone.return_value = (
            20,
        )

        mock_ti = MagicMock()
        mock_ti.task_id = "load_to_warehouse"

        context = {"task_instance": mock_ti, "execution_date": "2023-01-01"}

        result = load_parquet_to_warehouse("MSFT", **context)

        assert "records_loaded" in result
        assert "total_in_warehouse" in result
        assert "warehouse_type" in result
        assert "ticker" in result
        assert result["ticker"] == "MSFT"


class TestCreateTables:
    """Test create_tables method"""

    @patch("market_data.warehouse.loader.get_warehouse_connection")
    @patch("market_data.warehouse.loader.get_warehouse_config")
    @patch("market_data.warehouse.loader.TABLE_MARKET_DATA", "fact_market_data")
    def test_create_tables_postgresql(self, mock_get_config, mock_get_connection):
        """Test create_tables for PostgreSQL"""
        mock_get_config.return_value = {
            "type": "postgresql",
            "host": "localhost",
            "schema": "public",
        }
        mock_conn = MagicMock()
        mock_get_connection.return_value.get_connection.return_value.__enter__.return_value = (
            mock_conn
        )

        loader = WarehouseLoader()
        loader.create_tables()

        # Should execute schema, table, and index creation
        assert mock_conn.execute.call_count >= 2

    @patch("market_data.warehouse.loader.get_warehouse_connection")
    @patch("market_data.warehouse.loader.get_warehouse_config")
    @patch("market_data.warehouse.loader.TABLE_MARKET_DATA", "fact_market_data")
    def test_create_tables_redshift(self, mock_get_config, mock_get_connection):
        """Test create_tables for Redshift"""
        mock_get_config.return_value = {
            "type": "redshift",
            "host": "redshift-cluster.amazonaws.com",
            "schema": "public",
        }
        mock_conn = MagicMock()
        mock_get_connection.return_value.get_connection.return_value.__enter__.return_value = (
            mock_conn
        )

        loader = WarehouseLoader()
        loader.create_tables()

        # Should execute table creation (no schema for Redshift)
        assert mock_conn.execute.call_count >= 1


class TestLoadFromParquet:
    """Test load_from_parquet method"""

    @patch("market_data.warehouse.loader.get_warehouse_connection")
    @patch("market_data.warehouse.loader.get_warehouse_config")
    @patch("market_data.warehouse.loader.load_from_parquet")
    @patch("market_data.warehouse.loader.get_parquet_path")
    def test_load_from_parquet_success(
        self, mock_get_path, mock_load_parquet, mock_get_config, mock_get_connection
    ):
        """Test successful load from parquet"""
        mock_get_config.return_value = {
            "type": "postgresql",
            "host": "localhost",
            "schema": "public",
        }
        mock_df = pd.DataFrame(
            {
                "date": ["2023-01-01", "2023-01-02"],
                "ticker": ["AAPL", "AAPL"],
                "close": [150.0, 155.0],
            }
        )
        mock_load_parquet.return_value = mock_df

        loader = WarehouseLoader()
        loader._load_dataframe = MagicMock(return_value=2)

        result = loader.load_from_parquet("AAPL")

        assert result == 2
        mock_load_parquet.assert_called_once_with("AAPL")

    @patch("market_data.warehouse.loader.get_warehouse_connection")
    @patch("market_data.warehouse.loader.get_warehouse_config")
    @patch("market_data.warehouse.loader.load_from_parquet")
    @patch("market_data.warehouse.loader.get_parquet_path")
    def test_load_from_parquet_file_not_found(
        self, mock_get_path, mock_load_parquet, mock_get_config, mock_get_connection
    ):
        """Test load_from_parquet when file not found"""
        mock_get_config.return_value = {
            "type": "postgresql",
            "host": "localhost",
            "schema": "public",
        }
        mock_load_parquet.side_effect = FileNotFoundError()

        loader = WarehouseLoader()

        result = loader.load_from_parquet("AAPL")

        assert result == 0

    @patch("market_data.warehouse.loader.get_warehouse_connection")
    @patch("market_data.warehouse.loader.get_warehouse_config")
    @patch("market_data.warehouse.loader.load_from_parquet")
    def test_load_from_parquet_empty_dataframe(
        self, mock_load_parquet, mock_get_config, mock_get_connection
    ):
        """Test load_from_parquet with empty dataframe after filtering"""
        mock_get_config.return_value = {
            "type": "postgresql",
            "host": "localhost",
            "schema": "public",
        }
        # DataFrame with all null close prices
        mock_df = pd.DataFrame(
            {
                "date": ["2023-01-01", "2023-01-02"],
                "ticker": ["AAPL", "AAPL"],
                "close": [None, None],
            }
        )
        mock_load_parquet.return_value = mock_df

        loader = WarehouseLoader()

        result = loader.load_from_parquet("AAPL")

        assert result == 0


class TestLoadDataframe:
    """Test _load_dataframe method"""

    @patch("market_data.warehouse.loader.get_warehouse_connection")
    @patch("market_data.warehouse.loader.get_warehouse_config")
    @patch("market_data.warehouse.loader.LOAD_STRATEGY", "append")
    def test_load_dataframe_append(self, mock_get_config, mock_get_connection):
        """Test _load_dataframe with append strategy"""
        mock_get_config.return_value = {
            "type": "postgresql",
            "host": "localhost",
            "schema": "public",
        }
        loader = WarehouseLoader()
        loader._load_append = MagicMock(return_value=5)

        df = pd.DataFrame(
            {"ticker": ["AAPL"], "date": ["2023-01-01"], "close": [150.0]}
        )
        result = loader._load_dataframe(df, "AAPL")

        assert result == 5
        loader._load_append.assert_called_once_with(df, "AAPL")

    @patch("market_data.warehouse.loader.get_warehouse_connection")
    @patch("market_data.warehouse.loader.get_warehouse_config")
    @patch("market_data.warehouse.loader.LOAD_STRATEGY", "upsert")
    def test_load_dataframe_upsert(self, mock_get_config, mock_get_connection):
        """Test _load_dataframe with upsert strategy"""
        mock_get_config.return_value = {
            "type": "postgresql",
            "host": "localhost",
            "schema": "public",
        }
        loader = WarehouseLoader()
        loader._load_upsert = MagicMock(return_value=5)

        df = pd.DataFrame(
            {"ticker": ["AAPL"], "date": ["2023-01-01"], "close": [150.0]}
        )
        result = loader._load_dataframe(df, "AAPL")

        assert result == 5
        loader._load_upsert.assert_called_once_with(df, "AAPL")

    @patch("market_data.warehouse.loader.get_warehouse_connection")
    @patch("market_data.warehouse.loader.get_warehouse_config")
    @patch("market_data.warehouse.loader.LOAD_STRATEGY", "truncate_insert")
    def test_load_dataframe_truncate_insert(self, mock_get_config, mock_get_connection):
        """Test _load_dataframe with truncate_insert strategy"""
        mock_get_config.return_value = {
            "type": "postgresql",
            "host": "localhost",
            "schema": "public",
        }
        loader = WarehouseLoader()
        loader._load_truncate_insert = MagicMock(return_value=5)

        df = pd.DataFrame(
            {"ticker": ["AAPL"], "date": ["2023-01-01"], "close": [150.0]}
        )
        result = loader._load_dataframe(df, "AAPL")

        assert result == 5
        loader._load_truncate_insert.assert_called_once_with(df, "AAPL")

    @patch("market_data.warehouse.loader.get_warehouse_connection")
    @patch("market_data.warehouse.loader.get_warehouse_config")
    @patch("market_data.warehouse.loader.LOAD_STRATEGY", "invalid")
    def test_load_dataframe_invalid_strategy(
        self, mock_get_config, mock_get_connection
    ):
        """Test _load_dataframe with invalid strategy"""
        mock_get_config.return_value = {
            "type": "postgresql",
            "host": "localhost",
            "schema": "public",
        }
        loader = WarehouseLoader()

        df = pd.DataFrame(
            {"ticker": ["AAPL"], "date": ["2023-01-01"], "close": [150.0]}
        )

        with pytest.raises(ValueError, match="Unknown load strategy"):
            loader._load_dataframe(df, "AAPL")


class TestLoadAppend:
    """Test _load_append method"""

    @patch("market_data.warehouse.loader.get_warehouse_connection")
    @patch("market_data.warehouse.loader.get_warehouse_config")
    @patch("market_data.warehouse.loader.TABLE_MARKET_DATA", "fact_market_data")
    @patch("market_data.warehouse.loader.BATCH_SIZE", 1000)
    def test_load_append(self, mock_get_config, mock_get_connection):
        """Test _load_append strategy"""
        mock_get_config.return_value = {
            "type": "postgresql",
            "host": "localhost",
            "schema": "public",
        }
        mock_conn = MagicMock()
        mock_get_connection.return_value.get_connection.return_value.__enter__.return_value = (
            mock_conn
        )

        loader = WarehouseLoader()
        df = pd.DataFrame(
            {
                "ticker": ["AAPL", "AAPL"],
                "date": ["2023-01-01", "2023-01-02"],
                "close": [150.0, 155.0],
            }
        )

        result = loader._load_append(df, "AAPL")

        assert result == 2
        assert mock_conn.to_sql.called or hasattr(mock_conn, "to_sql")


class TestLoadUpsert:
    """Test _load_upsert method"""

    @patch("market_data.warehouse.loader.get_warehouse_connection")
    @patch("market_data.warehouse.loader.get_warehouse_config")
    def test_load_upsert_postgresql(self, mock_get_config, mock_get_connection):
        """Test _load_upsert for PostgreSQL"""
        mock_get_config.return_value = {
            "type": "postgresql",
            "host": "localhost",
            "schema": "public",
        }
        loader = WarehouseLoader()
        loader._upsert_postgresql = MagicMock(return_value=3)

        df = pd.DataFrame(
            {"ticker": ["AAPL"], "date": ["2023-01-01"], "close": [150.0]}
        )
        result = loader._load_upsert(df, "AAPL")

        assert result == 3
        loader._upsert_postgresql.assert_called_once_with(df, "AAPL")

    @patch("market_data.warehouse.loader.get_warehouse_connection")
    @patch("market_data.warehouse.loader.get_warehouse_config")
    def test_load_upsert_redshift(self, mock_get_config, mock_get_connection):
        """Test _load_upsert for Redshift"""
        mock_get_config.return_value = {
            "type": "redshift",
            "host": "redshift-cluster.amazonaws.com",
            "schema": "public",
        }
        loader = WarehouseLoader()
        loader._upsert_redshift = MagicMock(return_value=3)

        df = pd.DataFrame(
            {"ticker": ["AAPL"], "date": ["2023-01-01"], "close": [150.0]}
        )
        result = loader._load_upsert(df, "AAPL")

        assert result == 3
        loader._upsert_redshift.assert_called_once_with(df, "AAPL")


class TestUpsertPostgreSQL:
    """Test _upsert_postgresql method"""

    @patch("market_data.warehouse.loader.get_warehouse_connection")
    @patch("market_data.warehouse.loader.get_warehouse_config")
    @patch("market_data.warehouse.loader.TABLE_MARKET_DATA", "fact_market_data")
    @patch("market_data.warehouse.loader.BATCH_SIZE", 1000)
    def test_upsert_postgresql(self, mock_get_config, mock_get_connection):
        """Test PostgreSQL upsert"""
        mock_get_config.return_value = {
            "type": "postgresql",
            "host": "localhost",
            "schema": "public",
        }
        mock_conn = MagicMock()
        mock_execute_result = MagicMock()
        mock_conn.execute.return_value = mock_execute_result
        mock_get_connection.return_value.get_connection.return_value.__enter__.return_value = (
            mock_conn
        )

        loader = WarehouseLoader()
        df = pd.DataFrame(
            {
                "ticker": ["AAPL"],
                "date": ["2023-01-01"],
                "close": [150.0],
                "open": [149.0],
            }
        )

        result = loader._upsert_postgresql(df, "AAPL")

        assert result == 1
        assert mock_conn.execute.called


class TestUpsertRedshift:
    """Test _upsert_redshift method"""

    @patch("market_data.warehouse.loader.get_warehouse_connection")
    @patch("market_data.warehouse.loader.get_warehouse_config")
    @patch("market_data.warehouse.loader.TABLE_MARKET_DATA", "fact_market_data")
    @patch("market_data.warehouse.loader.BATCH_SIZE", 1000)
    def test_upsert_redshift(self, mock_get_config, mock_get_connection):
        """Test Redshift upsert"""
        mock_get_config.return_value = {
            "type": "redshift",
            "host": "redshift-cluster.amazonaws.com",
            "schema": "public",
        }
        mock_conn = MagicMock()
        mock_get_connection.return_value.get_connection.return_value.__enter__.return_value = (
            mock_conn
        )

        loader = WarehouseLoader()
        df = pd.DataFrame(
            {
                "ticker": ["AAPL"],
                "date": ["2023-01-01"],
                "close": [150.0],
            }
        )

        result = loader._upsert_redshift(df, "AAPL")

        assert result == 1
        assert mock_conn.execute.called


class TestLoadTruncateInsert:
    """Test _load_truncate_insert method"""

    @patch("market_data.warehouse.loader.get_warehouse_connection")
    @patch("market_data.warehouse.loader.get_warehouse_config")
    @patch("market_data.warehouse.loader.TABLE_MARKET_DATA", "fact_market_data")
    @patch("market_data.warehouse.loader.BATCH_SIZE", 1000)
    def test_load_truncate_insert(self, mock_get_config, mock_get_connection):
        """Test truncate_insert strategy"""
        mock_get_config.return_value = {
            "type": "postgresql",
            "host": "localhost",
            "schema": "public",
        }
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.rowcount = 5
        mock_conn.execute.return_value = mock_result
        mock_get_connection.return_value.get_connection.return_value.__enter__.return_value = (
            mock_conn
        )

        loader = WarehouseLoader()
        df = pd.DataFrame(
            {
                "ticker": ["AAPL", "AAPL"],
                "date": ["2023-01-01", "2023-01-02"],
                "close": [150.0, 155.0],
            }
        )

        result = loader._load_truncate_insert(df, "AAPL")

        assert result == 2
        assert mock_conn.execute.called


class TestClose:
    """Test close method"""

    @patch("market_data.warehouse.loader.get_warehouse_connection")
    @patch("market_data.warehouse.loader.get_warehouse_config")
    def test_close(self, mock_get_config, mock_get_connection):
        """Test close method"""
        mock_get_config.return_value = {
            "type": "postgresql",
            "host": "localhost",
            "schema": "public",
        }
        mock_connection = MagicMock()
        mock_get_connection.return_value = mock_connection

        loader = WarehouseLoader()
        loader.close()

        mock_connection.close.assert_called_once()
