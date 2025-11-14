"""
Unit tests for market data sensors
"""

import os
import sys
from unittest.mock import Mock, patch

import pytest

# Add dags directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../dags"))

from market_data.sensors.api_sensor import check_api_availability


class TestCheckApiAvailability:
    """Tests for API availability sensor"""

    @patch("market_data.sensors.api_sensor.YahooFinanceClient")
    def test_api_available(self, mock_client_class, mock_context):
        """Test sensor returns True when API is available"""
        # Mock client
        mock_client = Mock()
        mock_client.check_availability.return_value = True
        mock_client_class.return_value = mock_client

        mock_context["task_instance"].xcom_pull.side_effect = lambda *args, **kwargs: (
            ["AAPL"] if kwargs.get("key") == "validated_tickers" else None
        )

        # Execute
        result = check_api_availability(**mock_context)

        # Assertions
        assert result is True
        mock_client.check_availability.assert_called_once_with("AAPL")

    @patch("market_data.sensors.api_sensor.YahooFinanceClient")
    def test_api_unavailable(self, mock_client_class, mock_context):
        """Test sensor returns False when API is unavailable"""
        # Mock client
        mock_client = Mock()
        mock_client.check_availability.return_value = False
        mock_client_class.return_value = mock_client

        mock_context["task_instance"].xcom_pull.side_effect = lambda *args, **kwargs: (
            ["AAPL"] if kwargs.get("key") == "validated_tickers" else None
        )

        # Execute
        result = check_api_availability(**mock_context)

        # Assertions
        assert result is False

    @patch("market_data.sensors.api_sensor.YahooFinanceClient")
    def test_different_tickers(self, mock_client_class, mock_context):
        """Test sensor works with different tickers"""
        mock_client = Mock()
        mock_client.check_availability.return_value = True
        mock_client_class.return_value = mock_client

        tickers = ["AAPL", "GOOGL", "MSFT", "TSLA"]

        mock_context["task_instance"].xcom_pull.side_effect = lambda *args, **kwargs: (
            tickers if kwargs.get("key") == "validated_tickers" else None
        )

        result = check_api_availability(**mock_context)
        assert result is True
        assert mock_client.check_availability.call_count == len(tickers)

    @patch("market_data.sensors.api_sensor.YahooFinanceClient")
    def test_sensor_uses_correct_config(self, mock_client_class, mock_context):
        """Test sensor initializes client with correct configuration"""
        mock_client = Mock()
        mock_client.check_availability.return_value = True
        mock_client_class.return_value = mock_client

        mock_context["task_instance"].xcom_pull.side_effect = lambda *args, **kwargs: (
            ["AAPL"] if kwargs.get("key") == "validated_tickers" else None
        )

        # Execute
        check_api_availability(**mock_context)

        # Verify client was initialized with configuration
        mock_client_class.assert_called_once()
        call_kwargs = mock_client_class.call_args.kwargs

        assert "base_url" in call_kwargs
        assert "headers" in call_kwargs
        assert "timeout" in call_kwargs

    @patch("market_data.sensors.api_sensor.YahooFinanceClient")
    def test_sensor_raises_when_no_tickers(self, mock_client_class, mock_context):
        """Test sensor raises if validate_ticker did not provide tickers"""
        mock_context["task_instance"].xcom_pull.return_value = []

        with pytest.raises(ValueError, match="No tickers available"):
            check_api_availability(**mock_context)
