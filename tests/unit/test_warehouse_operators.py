"""
Unit tests for warehouse operators
"""

from unittest.mock import MagicMock, patch

import pytest
from market_data.operators.warehouse_operators import load_to_warehouse


class TestLoadToWarehouse:
    """Test load_to_warehouse operator"""

    @patch("market_data.operators.warehouse_operators.warehouse_load_function")
    def test_loads_each_ticker(self, mock_warehouse_func):
        mock_warehouse_func.side_effect = [
            {
                "records_loaded": 10,
                "total_in_warehouse": 10,
                "warehouse_type": "postgresql",
            },
            {
                "records_loaded": 20,
                "total_in_warehouse": 30,
                "warehouse_type": "postgresql",
            },
        ]

        mock_ti = MagicMock()
        mock_ti.xcom_pull.return_value = ["AAPL", "MSFT"]
        mock_ti.task_id = "load_to_warehouse"

        context = {
            "task_instance": mock_ti,
            "params": {},
            "execution_date": "2023-01-01",
        }

        load_to_warehouse(**context)

        assert mock_warehouse_func.call_count == 2
        assert mock_warehouse_func.call_args_list[0][0][0] == "AAPL"
        assert mock_warehouse_func.call_args_list[1][0][0] == "MSFT"

    @patch("market_data.operators.warehouse_operators.warehouse_load_function")
    def test_returns_summary_list(self, mock_warehouse_func):
        summaries = [
            {
                "records_loaded": 10,
                "total_in_warehouse": 10,
                "warehouse_type": "postgresql",
            },
            {
                "records_loaded": 5,
                "total_in_warehouse": 15,
                "warehouse_type": "postgresql",
            },
        ]
        mock_warehouse_func.side_effect = summaries

        mock_ti = MagicMock()
        mock_ti.xcom_pull.return_value = ["AAPL", "MSFT"]
        mock_ti.task_id = "load_to_warehouse"

        context = {
            "task_instance": mock_ti,
            "params": {},
            "execution_date": "2023-01-01",
        }

        result = load_to_warehouse(**context)

        assert result == summaries
        mock_ti.xcom_push.assert_called_with(key="warehouse_summary", value=summaries)

    @patch("market_data.operators.warehouse_operators.warehouse_load_function")
    def test_raises_when_no_tickers(self, mock_warehouse_func):
        mock_ti = MagicMock()
        mock_ti.xcom_pull.return_value = []

        context = {
            "task_instance": mock_ti,
            "params": {},
            "execution_date": "2023-01-01",
        }

        with pytest.raises(ValueError):
            load_to_warehouse(**context)

        mock_warehouse_func.assert_not_called()
