"""
Unit tests for market data operators
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch

# Add dags directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../dags"))

from market_data.operators.market_data_operators import (
    validate_ticker,
    fetch_market_data,
    process_market_data,
)


class TestValidateTickerOperator:
    """Tests for validate_ticker operator"""

    def test_validate_ticker_from_config(self, mock_context):
        """Test validate_ticker with config value"""
        result = validate_ticker(**mock_context)

        assert result == "AAPL"
        mock_context["task_instance"].xcom_push.assert_called_once_with(
            key="validated_ticker", value="AAPL"
        )

    def test_validate_ticker_lowercase(self):
        """Test validate_ticker converts lowercase to uppercase"""
        mock_context = {
            "dag_run": Mock(conf={"ticker": "googl"}),
            "task_instance": Mock(),
        }

        result = validate_ticker(**mock_context)

        assert result == "GOOGL"

    def test_validate_ticker_uses_default(self):
        """Test validate_ticker uses default when no config provided"""
        mock_context = {"dag_run": Mock(conf={}), "task_instance": Mock()}

        result = validate_ticker(**mock_context)

        assert result is not None
        assert isinstance(result, str)


class TestFetchMarketDataOperator:
    """Tests for fetch_market_data operator"""

    @patch("market_data.operators.market_data_operators.YahooFinanceClient")
    def test_fetch_market_data_success(
        self, mock_client_class, mock_context, sample_market_data
    ):
        """Test successful data fetch"""
        # Mock client instance
        mock_client = Mock()
        mock_client.fetch_market_data.return_value = sample_market_data
        mock_client_class.return_value = mock_client

        # Execute
        result = fetch_market_data(ticker="AAPL", date="2023-11-09", **mock_context)

        # Assertions
        assert result == sample_market_data
        mock_client.fetch_market_data.assert_called_once()
        mock_context["task_instance"].xcom_push.assert_called_once_with(
            key="market_data", value=sample_market_data
        )

    @patch("market_data.operators.market_data_operators.YahooFinanceClient")
    def test_fetch_market_data_calls_client_with_config(
        self, mock_client_class, mock_context
    ):
        """Test fetch_market_data uses configuration correctly"""
        mock_client = Mock()
        mock_client.fetch_market_data.return_value = {"ticker": "AAPL"}
        mock_client_class.return_value = mock_client

        # Execute
        fetch_market_data(ticker="TSLA", date="2024-01-15", **mock_context)

        # Verify client was called with correct parameters
        mock_client.fetch_market_data.assert_called_once()
        call_args = mock_client.fetch_market_data.call_args

        assert call_args.kwargs["ticker"] == "TSLA"
        assert call_args.kwargs["date"] == "2024-01-15"


class TestProcessMarketDataOperator:
    """Tests for process_market_data operator"""

    def test_process_market_data_success(self, mock_context, sample_market_data):
        """Test successful data processing"""
        # Mock XCom pull to return sample data
        mock_context["task_instance"].xcom_pull.return_value = sample_market_data

        # Execute
        result = process_market_data(**mock_context)

        # Assertions
        assert result == sample_market_data
        mock_context["task_instance"].xcom_pull.assert_called_once_with(
            task_ids="fetch_market_data", key="market_data"
        )

    def test_process_market_data_no_data(self, mock_context):
        """Test processing when no data is available"""
        # Mock XCom pull to return None
        mock_context["task_instance"].xcom_pull.return_value = None

        # Execute
        result = process_market_data(**mock_context)

        # Should return None gracefully
        assert result is None

    def test_process_market_data_logs_correctly(
        self, mock_context, sample_market_data, caplog
    ):
        """Test that processing logs data correctly"""
        import logging

        mock_context["task_instance"].xcom_pull.return_value = sample_market_data

        # Execute with logging capture
        with caplog.at_level(logging.INFO):
            result = process_market_data(**mock_context)

        # Verify key information is logged
        log_output = caplog.text
        assert "MARKET DATA PROCESSED" in log_output
        assert "AAPL" in log_output
        assert "Apple Inc." in log_output
