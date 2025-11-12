"""
Unit tests for Yahoo Finance API Client
"""

import os
import sys
from datetime import datetime
from unittest.mock import Mock, patch

import pytest

# Add dags directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../dags"))

from market_data.utils.api_client import YahooFinanceClient


class TestYahooFinanceClient:
    """Tests for YahooFinanceClient"""

    @pytest.fixture
    def client(self):
        """Create a test client instance"""
        return YahooFinanceClient(
            base_url="https://api.test.com", headers={"User-Agent": "Test"}, timeout=10
        )

    @pytest.fixture
    def mock_success_response(self):
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

    def test_init(self, client):
        """Test client initialization"""
        assert client.base_url == "https://api.test.com"
        assert client.headers == {"User-Agent": "Test"}
        assert client.timeout == 10

    @patch("market_data.utils.api_client.requests.get")
    def test_fetch_market_data_success(self, mock_get, client, mock_success_response):
        """Test successful data fetch"""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_success_response
        mock_get.return_value = mock_response

        # Fetch data
        result = client.fetch_market_data("AAPL", "2023-11-09")

        # Assertions
        assert result["ticker"] == "AAPL"
        assert result["date"] == "2023-11-09"
        assert result["currency"] == "USD"
        assert result["quote"]["close"] == 182.41
        assert result["quote"]["volume"] == 53763500
        assert result["metadata"]["long_name"] == "Apple Inc."

    @patch("market_data.utils.api_client.requests.get")
    @patch("market_data.utils.api_client.time.sleep")
    def test_fetch_market_data_with_retries(
        self, mock_sleep, mock_get, client, mock_success_response
    ):
        """Test retry logic on failures"""
        import requests

        # Mock: first call fails with exception, second succeeds
        mock_success_response_obj = Mock()
        mock_success_response_obj.status_code = 200
        mock_success_response_obj.json.return_value = mock_success_response

        # First call raises exception, second call succeeds
        mock_get.side_effect = [
            requests.exceptions.RequestException("Connection error"),
            mock_success_response_obj,
        ]

        # Should succeed on second attempt
        result = client.fetch_market_data("AAPL", "2023-11-09", max_retries=3)

        assert result["ticker"] == "AAPL"
        assert mock_get.call_count == 2
        assert mock_sleep.call_count >= 1  # Should have slept before retry

    @patch("market_data.utils.api_client.requests.get")
    def test_fetch_market_data_rate_limit_429(
        self, mock_get, client, mock_success_response
    ):
        """Test handling of 429 rate limit error"""
        # Mock: first call 429, second succeeds
        mock_429_response = Mock()
        mock_429_response.status_code = 429
        mock_429_response.headers = {"Retry-After": "1"}

        mock_success_response_obj = Mock()
        mock_success_response_obj.status_code = 200
        mock_success_response_obj.json.return_value = mock_success_response

        mock_get.side_effect = [mock_429_response, mock_success_response_obj]

        # Should retry and succeed
        with patch("market_data.utils.api_client.time.sleep"):
            result = client.fetch_market_data("AAPL", "2023-11-09")

        assert result["ticker"] == "AAPL"
        assert mock_get.call_count == 2

    @patch("market_data.utils.api_client.requests.get")
    def test_fetch_market_data_api_error(self, mock_get, client):
        """Test handling of API error in response"""
        # Mock response with error
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "chart": {
                "result": None,
                "error": {"code": "Not Found", "description": "No data found"},
            }
        }
        mock_get.return_value = mock_response

        # Should raise ValueError
        with pytest.raises(ValueError, match="API error"):
            client.fetch_market_data("INVALID", "2023-11-09")

    @patch("market_data.utils.api_client.requests.get")
    def test_check_availability_success(self, mock_get, client, mock_success_response):
        """Test successful API availability check"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_success_response
        mock_get.return_value = mock_response

        result = client.check_availability("AAPL")

        assert result is True

    @patch("market_data.utils.api_client.requests.get")
    def test_check_availability_rate_limit(self, mock_get, client):
        """Test availability check returns False on rate limit"""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_get.return_value = mock_response

        result = client.check_availability("AAPL")

        assert result is False

    @patch("market_data.utils.api_client.requests.get")
    def test_check_availability_server_error(self, mock_get, client):
        """Test availability check returns False on server error"""
        mock_response = Mock()
        mock_response.status_code = 503
        mock_get.return_value = mock_response

        result = client.check_availability("AAPL")

        assert result is False

    @patch("market_data.utils.api_client.requests.get")
    def test_check_availability_timeout(self, mock_get, client):
        """Test availability check returns False on timeout"""
        import requests

        mock_get.side_effect = requests.exceptions.Timeout()

        result = client.check_availability("AAPL")

        assert result is False

    @patch("market_data.utils.api_client.requests.get")
    def test_check_availability_invalid_ticker(self, mock_get, client):
        """Test availability check raises ValueError for invalid ticker"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "chart": {
                "result": None,
                "error": {
                    "code": "Not Found",
                    "description": "Symbol not found: INVALID",
                },
            }
        }
        mock_get.return_value = mock_response

        with pytest.raises(ValueError, match="Invalid ticker"):
            client.check_availability("INVALID")

    def test_parse_market_data(self, client, mock_success_response):
        """Test parsing of market data"""
        result = client._parse_market_data(
            mock_success_response, "AAPL", "2023-11-09", 1699549200
        )

        assert result["ticker"] == "AAPL"
        assert result["date"] == "2023-11-09"
        assert result["timestamp"] == 1699549200
        assert result["currency"] == "USD"
        assert result["exchange"] == "NMS"
        assert result["quote"]["close"] == 182.41
        assert result["quote"]["volume"] == 53763500
        assert result["metadata"]["long_name"] == "Apple Inc."
