"""
Unit tests for configuration module
"""

import os
from unittest.mock import MagicMock, patch

import pytest


class TestGetConfigValue:
    """Tests for get_config_value function"""

    @patch("market_data.config.settings.Variable")
    def test_airflow_variable_priority(self, mock_variable):
        """Test that Airflow Variable has highest priority"""
        from market_data.config.settings import get_config_value

        # Mock Airflow Variable to return a value
        mock_variable.get.return_value = "GOOGL"

        with patch.dict(os.environ, {"TEST_ENV": "AAPL"}):
            result = get_config_value(
                airflow_key="test.ticker",
                env_key="TEST_ENV",
                default_value="MSFT",
                value_type=str,
            )

        assert result == "GOOGL"
        mock_variable.get.assert_called_once_with("test.ticker", default_var=None)

    @patch("market_data.config.settings.Variable")
    def test_env_variable_fallback(self, mock_variable):
        """Test that ENV variable is used when Airflow Variable is not available"""
        from market_data.config.settings import get_config_value

        # Mock Airflow Variable to return None
        mock_variable.get.return_value = None

        with patch.dict(os.environ, {"TEST_ENV": "TSLA"}):
            result = get_config_value(
                airflow_key="test.ticker",
                env_key="TEST_ENV",
                default_value="MSFT",
                value_type=str,
            )

        assert result == "TSLA"

    @patch("market_data.config.settings.Variable")
    def test_default_value_fallback(self, mock_variable):
        """Test that default value is used when nothing else is available"""
        from market_data.config.settings import get_config_value

        # Mock Airflow Variable to return None
        mock_variable.get.return_value = None

        with patch.dict(os.environ, {}, clear=True):
            result = get_config_value(
                airflow_key="test.ticker",
                env_key="TEST_ENV",
                default_value="AMZN",
                value_type=str,
            )

        assert result == "AMZN"

    @patch("market_data.config.settings.Variable")
    def test_int_type_conversion(self, mock_variable):
        """Test integer type conversion"""
        from market_data.config.settings import get_config_value

        mock_variable.get.return_value = "42"

        result = get_config_value(
            airflow_key="test.number",
            env_key="TEST_NUM",
            default_value="10",
            value_type=int,
        )

        assert result == 42
        assert isinstance(result, int)

    @patch("market_data.config.settings.Variable")
    def test_bool_type_conversion_true(self, mock_variable):
        """Test boolean type conversion for True values"""
        from market_data.config.settings import get_config_value

        true_values = ["true", "True", "1", "yes", "YES", "on", "ON"]

        for value in true_values:
            mock_variable.get.return_value = value
            result = get_config_value(
                airflow_key="test.bool",
                env_key="TEST_BOOL",
                default_value="false",
                value_type=bool,
            )
            assert result is True, f"Failed for value: {value}"

    @patch("market_data.config.settings.Variable")
    def test_bool_type_conversion_false(self, mock_variable):
        """Test boolean type conversion for False values"""
        from market_data.config.settings import get_config_value

        false_values = ["false", "False", "0", "no", "NO", "off", "OFF"]

        for value in false_values:
            mock_variable.get.return_value = value
            result = get_config_value(
                airflow_key="test.bool",
                env_key="TEST_BOOL",
                default_value="true",
                value_type=bool,
            )
            assert result is False, f"Failed for value: {value}"

    @patch("market_data.config.settings.Variable")
    def test_exception_handling(self, mock_variable):
        """Test exception handling when Variable.get fails"""
        from market_data.config.settings import get_config_value

        # Mock Variable.get to raise an exception
        mock_variable.get.side_effect = Exception("DB connection error")

        with patch.dict(os.environ, {"TEST_ENV": "FALLBACK"}):
            result = get_config_value(
                airflow_key="test.key",
                env_key="TEST_ENV",
                default_value="DEFAULT",
                value_type=str,
            )

        assert result == "FALLBACK"
