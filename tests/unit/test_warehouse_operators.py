"""
Unit tests for warehouse operators
"""

from unittest.mock import MagicMock, patch

import pytest

from market_data.operators.warehouse_operators import load_to_warehouse


class TestLoadToWarehouse:
    """Test load_to_warehouse operator"""

    @patch("market_data.operators.warehouse_operators.WarehouseLoader")
    def test_load_to_warehouse_retrieves_ticker_from_xcom(self, mock_loader_class):
        """Test load_to_warehouse retrieves ticker from XCom"""
        mock_loader = MagicMock()
        mock_loader_class.return_value = mock_loader
        mock_loader.load_from_parquet.return_value = {"records_loaded": 100}

        mock_ti = MagicMock()
        mock_ti.xcom_pull.return_value = "AAPL"

        load_to_warehouse(ti=mock_ti)

        mock_ti.xcom_pull.assert_called_once_with(
            task_ids="validate_ticker", key="return_value"
        )

    @patch("market_data.operators.warehouse_operators.WarehouseLoader")
    def test_load_to_warehouse_calls_loader(self, mock_loader_class):
        """Test load_to_warehouse calls WarehouseLoader"""
        mock_loader = MagicMock()
        mock_loader_class.return_value = mock_loader
        mock_loader.load_from_parquet.return_value = {"records_loaded": 100}

        mock_ti = MagicMock()
        mock_ti.xcom_pull.return_value = "AAPL"

        load_to_warehouse(ti=mock_ti)

        mock_loader.load_from_parquet.assert_called_once_with("AAPL")

    @patch("market_data.operators.warehouse_operators.WarehouseLoader")
    def test_load_to_warehouse_returns_summary(self, mock_loader_class):
        """Test load_to_warehouse returns load summary"""
        mock_loader = MagicMock()
        mock_loader_class.return_value = mock_loader

        expected_summary = {
            "records_loaded": 100,
            "ticker": "AAPL",
            "table": "fact_market_data",
        }
        mock_loader.load_from_parquet.return_value = expected_summary

        mock_ti = MagicMock()
        mock_ti.xcom_pull.return_value = "AAPL"

        result = load_to_warehouse(ti=mock_ti)

        assert result == expected_summary

    @patch("market_data.operators.warehouse_operators.WarehouseLoader")
    def test_load_to_warehouse_handles_different_tickers(self, mock_loader_class):
        """Test load_to_warehouse handles different ticker symbols"""
        mock_loader = MagicMock()
        mock_loader_class.return_value = mock_loader
        mock_loader.load_from_parquet.return_value = {"records_loaded": 50}

        mock_ti = MagicMock()
        mock_ti.xcom_pull.return_value = "MSFT"

        load_to_warehouse(ti=mock_ti)

        mock_loader.load_from_parquet.assert_called_once_with("MSFT")

    @patch("market_data.operators.warehouse_operators.WarehouseLoader")
    def test_load_to_warehouse_raises_on_no_ticker(self, mock_loader_class):
        """Test load_to_warehouse raises error if no ticker found"""
        mock_loader = MagicMock()
        mock_loader_class.return_value = mock_loader

        mock_ti = MagicMock()
        mock_ti.xcom_pull.return_value = None

        with pytest.raises((ValueError, AttributeError, TypeError)):
            load_to_warehouse(ti=mock_ti)

    @patch("market_data.operators.warehouse_operators.WarehouseLoader")
    def test_load_to_warehouse_propagates_loader_exceptions(self, mock_loader_class):
        """Test load_to_warehouse propagates exceptions from loader"""
        mock_loader = MagicMock()
        mock_loader_class.return_value = mock_loader
        mock_loader.load_from_parquet.side_effect = Exception("Database connection failed")

        mock_ti = MagicMock()
        mock_ti.xcom_pull.return_value = "AAPL"

        with pytest.raises(Exception) as exc_info:
            load_to_warehouse(ti=mock_ti)

        assert "Database connection failed" in str(exc_info.value)

    @patch("market_data.operators.warehouse_operators.WarehouseLoader")
    def test_load_to_warehouse_creates_new_loader_instance(self, mock_loader_class):
        """Test load_to_warehouse creates a new WarehouseLoader instance"""
        mock_loader = MagicMock()
        mock_loader_class.return_value = mock_loader
        mock_loader.load_from_parquet.return_value = {"records_loaded": 100}

        mock_ti = MagicMock()
        mock_ti.xcom_pull.return_value = "AAPL"

        load_to_warehouse(ti=mock_ti)

        mock_loader_class.assert_called_once()

    @patch("market_data.operators.warehouse_operators.WarehouseLoader")
    def test_load_to_warehouse_uses_logger(self, mock_loader_class):
        """Test load_to_warehouse uses logger for info messages"""
        mock_loader = MagicMock()
        mock_loader_class.return_value = mock_loader
        mock_loader.load_from_parquet.return_value = {"records_loaded": 100}

        mock_ti = MagicMock()
        mock_ti.xcom_pull.return_value = "AAPL"

        with patch("market_data.operators.warehouse_operators.logger") as mock_logger:
            load_to_warehouse(ti=mock_ti)

            # Verify logger was used
            assert mock_logger.info.called or mock_logger.debug.called

    @patch("market_data.operators.warehouse_operators.WarehouseLoader")
    def test_load_to_warehouse_with_uppercase_ticker(self, mock_loader_class):
        """Test load_to_warehouse handles uppercase ticker"""
        mock_loader = MagicMock()
        mock_loader_class.return_value = mock_loader
        mock_loader.load_from_parquet.return_value = {"records_loaded": 100}

        mock_ti = MagicMock()
        mock_ti.xcom_pull.return_value = "GOOGL"

        load_to_warehouse(ti=mock_ti)

        mock_loader.load_from_parquet.assert_called_once_with("GOOGL")

    @patch("market_data.operators.warehouse_operators.WarehouseLoader")
    def test_load_to_warehouse_with_lowercase_ticker(self, mock_loader_class):
        """Test load_to_warehouse handles lowercase ticker"""
        mock_loader = MagicMock()
        mock_loader_class.return_value = mock_loader
        mock_loader.load_from_parquet.return_value = {"records_loaded": 100}

        mock_ti = MagicMock()
        mock_ti.xcom_pull.return_value = "tsla"

        load_to_warehouse(ti=mock_ti)

        # Ticker should be passed as-is
        mock_loader.load_from_parquet.assert_called_once_with("tsla")

