"""
Pytest configuration and shared fixtures
"""

import os
import sys
from datetime import datetime
from unittest.mock import Mock

import pytest

# Add dags directory to Python path
DAGS_DIR = os.path.join(os.path.dirname(__file__), "../dags")
sys.path.insert(0, DAGS_DIR)

# Set Airflow home for testing
os.environ["AIRFLOW_HOME"] = os.path.join(os.path.dirname(__file__), "../")
os.environ["AIRFLOW__CORE__UNIT_TEST_MODE"] = "True"
os.environ["AIRFLOW__CORE__LOAD_EXAMPLES"] = "False"


@pytest.fixture
def mock_dag_run():
    """Create a mock DAG run"""
    mock = Mock()
    mock.conf = {"ticker": "AAPL", "tickers": ["AAPL"], "date": "2023-11-09"}
    return mock


@pytest.fixture
def mock_task_instance():
    """Create a mock task instance"""
    mock = Mock()
    mock.xcom_push = Mock()
    mock.xcom_pull = Mock()
    return mock


@pytest.fixture
def mock_context(mock_dag_run, mock_task_instance):
    """Create a mock Airflow context"""
    return {
        "dag_run": mock_dag_run,
        "task_instance": mock_task_instance,
        "execution_date": datetime(2023, 11, 9),
        "dag": Mock(dag_id="get_market_data"),
        "task": Mock(task_id="test_task"),
    }


@pytest.fixture
def sample_market_data():
    """Sample market data for testing"""
    return {
        "ticker": "AAPL",
        "date": "2023-11-09",
        "timestamp": 1699549200,
        "currency": "USD",
        "exchange": "NMS",
        "instrument_type": "EQUITY",
        "regular_market_price": 182.41,
        "regular_market_time": 1699549200,
        "quote": {
            "open": 182.96,
            "high": 184.12,
            "low": 181.81,
            "close": 182.41,
            "volume": 53763500,
        },
        "metadata": {
            "fifty_two_week_high": 184.95,
            "fifty_two_week_low": 124.17,
            "long_name": "Apple Inc.",
            "short_name": "Apple Inc.",
        },
    }


@pytest.fixture
def yahoo_api_response(sample_market_data):
    """Yahoo Finance API response format"""
    return {
        "chart": {
            "result": [
                {
                    "meta": {
                        "currency": sample_market_data["currency"],
                        "symbol": sample_market_data["ticker"],
                        "exchangeName": sample_market_data["exchange"],
                        "instrumentType": sample_market_data["instrument_type"],
                        "regularMarketPrice": sample_market_data[
                            "regular_market_price"
                        ],
                        "regularMarketTime": sample_market_data["regular_market_time"],
                        "fiftyTwoWeekHigh": sample_market_data["metadata"][
                            "fifty_two_week_high"
                        ],
                        "fiftyTwoWeekLow": sample_market_data["metadata"][
                            "fifty_two_week_low"
                        ],
                        "longName": sample_market_data["metadata"]["long_name"],
                        "shortName": sample_market_data["metadata"]["short_name"],
                    },
                    "indicators": {
                        "quote": [
                            {
                                "open": [sample_market_data["quote"]["open"]],
                                "high": [sample_market_data["quote"]["high"]],
                                "low": [sample_market_data["quote"]["low"]],
                                "close": [sample_market_data["quote"]["close"]],
                                "volume": [sample_market_data["quote"]["volume"]],
                            }
                        ]
                    },
                }
            ],
            "error": None,
        }
    }
