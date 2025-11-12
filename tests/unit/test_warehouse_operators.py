"""
Unit tests for warehouse operators
"""

from unittest.mock import MagicMock, patch

import pytest
from market_data.operators.warehouse_operators import load_to_warehouse


class TestLoadToWarehouse:
    """Test load_to_warehouse operator"""

    @patch("market_data.operators.warehouse_operators.warehouse_load_function")
    def test_load_to_warehouse_retrieves_ticker_from_xcom(self, mock_warehouse_func):
        """Test load_to_warehouse retrieves ticker from XCom"""
        mock_warehouse_func.return_value = {
            "records_loaded": 100,
            "total_in_warehouse": 100,
            "warehouse_type": "postgresql",
        }

        mock_ti = MagicMock()
        mock_ti.xcom_pull.return_value = "AAPL"
        mock_ti.task_id = "load_to_warehouse"

        context = {
            "task_instance": mock_ti,
            "params": {},
            "execution_date": "2023-01-01",
        }

        load_to_warehouse(**context)

        mock_ti.xcom_pull.assert_called_once_with(key="validated_ticker")

    @patch("market_data.operators.warehouse_operators.warehouse_load_function")
    def test_load_to_warehouse_calls_warehouse_function(self, mock_warehouse_func):
        """Test load_to_warehouse calls warehouse load function"""
        mock_warehouse_func.return_value = {
            "records_loaded": 100,
            "total_in_warehouse": 100,
            "warehouse_type": "postgresql",
        }

        mock_ti = MagicMock()
        mock_ti.xcom_pull.return_value = "AAPL"
        mock_ti.task_id = "load_to_warehouse"

        context = {
            "task_instance": mock_ti,
            "params": {},
            "execution_date": "2023-01-01",
        }

        load_to_warehouse(**context)

        mock_warehouse_func.assert_called_once()
        call_args = mock_warehouse_func.call_args
        assert call_args[0][0] == "AAPL"  # First positional arg is ticker

    @patch("market_data.operators.warehouse_operators.warehouse_load_function")
    def test_load_to_warehouse_returns_summary(self, mock_warehouse_func):
        """Test load_to_warehouse returns load summary"""
        expected_summary = {
            "records_loaded": 100,
            "total_in_warehouse": 100,
            "warehouse_type": "postgresql",
        }
        mock_warehouse_func.return_value = expected_summary

        mock_ti = MagicMock()
        mock_ti.xcom_pull.return_value = "AAPL"
        mock_ti.task_id = "load_to_warehouse"

        context = {
            "task_instance": mock_ti,
            "params": {},
            "execution_date": "2023-01-01",
        }

        result = load_to_warehouse(**context)

        assert result == expected_summary

    @patch("market_data.operators.warehouse_operators.warehouse_load_function")
    def test_load_to_warehouse_uses_ticker_from_params(self, mock_warehouse_func):
        """Test load_to_warehouse can use ticker from params"""
        mock_warehouse_func.return_value = {
            "records_loaded": 50,
            "total_in_warehouse": 50,
            "warehouse_type": "postgresql",
        }

        mock_ti = MagicMock()
        mock_ti.task_id = "load_to_warehouse"

        context = {
            "task_instance": mock_ti,
            "params": {"ticker": "MSFT"},
            "execution_date": "2023-01-01",
        }

        load_to_warehouse(**context)

        # Should use ticker from params, not XCom
        call_args = mock_warehouse_func.call_args
        assert call_args[0][0] == "MSFT"
