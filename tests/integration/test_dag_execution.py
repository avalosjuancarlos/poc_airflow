"""
Integration tests for DAG execution

Tests end-to-end execution of the DAG
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from airflow.models import DagBag


@pytest.mark.integration
class TestDAGExecution:
    """Test DAG execution flow"""

    @pytest.fixture(scope="class")
    def dagbag(self):
        """Load DAG"""
        return DagBag(dag_folder="dags/", include_examples=False)

    @pytest.fixture
    def mock_api_response(self):
        """Mock successful API response"""
        return {
            "chart": {
                "result": [
                    {
                        "meta": {
                            "currency": "USD",
                            "symbol": "AAPL",
                            "exchangeName": "NMS",
                            "instrumentType": "EQUITY",
                            "regularMarketPrice": 182.41,
                            "regularMarketTime": 1699549200,
                            "fiftyTwoWeekHigh": 184.95,
                            "fiftyTwoWeekLow": 124.17,
                            "longName": "Apple Inc.",
                            "shortName": "Apple Inc.",
                        },
                        "indicators": {
                            "quote": [
                                {
                                    "open": [182.96],
                                    "high": [184.12],
                                    "low": [181.81],
                                    "close": [182.41],
                                    "volume": [53763500],
                                }
                            ]
                        },
                    }
                ],
                "error": None,
            }
        }

    def test_validate_ticker_task(self, dagbag):
        """Test validate_ticker task execution"""
        dag = dagbag.get_dag("get_market_data")
        task = dag.get_task("validate_ticker")

        # Create mock context
        mock_context = {
            "dag_run": Mock(conf={"tickers": ["AAPL"], "ticker": "AAPL"}),
            "task_instance": Mock(),
        }

        # Execute task
        result = task.python_callable(**mock_context)

        # Verify result
        assert result == ["AAPL"]

    def test_validate_ticker_lowercase(self, dagbag):
        """Test validate_ticker converts to uppercase"""
        dag = dagbag.get_dag("get_market_data")
        task = dag.get_task("validate_ticker")

        mock_context = {
            "dag_run": Mock(conf={"tickers": ["aapl"], "ticker": "aapl"}),
            "task_instance": Mock(),
        }

        result = task.python_callable(**mock_context)

        assert result == ["AAPL"]

    @patch("market_data.utils.api_client.requests.get")
    def test_check_api_availability_task(self, mock_get, dagbag, mock_api_response):
        """Test check_api_availability sensor"""
        dag = dagbag.get_dag("get_market_data")
        task = dag.get_task("check_api_availability")

        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_api_response
        mock_get.return_value = mock_response

        mock_task_instance = Mock()

        def side_effect(*args, **kwargs):
            if kwargs.get("key") == "validated_tickers":
                return ["AAPL"]
            return None

        mock_task_instance.xcom_pull.side_effect = side_effect

        # Execute sensor
        result = task.python_callable(task_instance=mock_task_instance)

        assert result is True

    # NOTE: Tests for fetch_multiple_dates and transform_and_save tasks are not
    # included here as they involve complex logic (backfill, technical indicators,
    # Parquet storage) that is extensively covered by unit tests in:
    # - test_transform_operators.py (9 comprehensive tests)
    # - test_technical_indicators.py (17 tests for indicators)
    # - test_parquet_storage.py (11 tests for storage)
    #
    # Integration testing at the task execution level would require extensive
    # mocking that would essentially duplicate the unit test coverage.
