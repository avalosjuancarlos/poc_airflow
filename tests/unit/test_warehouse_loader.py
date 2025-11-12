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
