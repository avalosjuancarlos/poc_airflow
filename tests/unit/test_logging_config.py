"""
Unit tests for logging configuration
"""

import logging
import os
from unittest.mock import patch

import pytest

from dags.market_data.config.logging_config import (
    get_datadog_config,
    get_log_format,
    get_log_level,
    get_sentry_config,
)


class TestGetLogLevel:
    """Test get_log_level function"""

    @patch.dict(os.environ, {"AIRFLOW__LOGGING__LEVEL": "DEBUG"})
    def test_explicit_log_level(self):
        """Test explicit log level from environment variable"""
        level = get_log_level()
        assert level == logging.DEBUG

    @patch.dict(os.environ, {"AIRFLOW__LOGGING__LEVEL": "WARNING"})
    def test_explicit_warning_level(self):
        """Test explicit WARNING level"""
        level = get_log_level()
        assert level == logging.WARNING

    @patch.dict(os.environ, {"ENVIRONMENT": "development"}, clear=True)
    def test_development_environment(self):
        """Test log level for development environment"""
        level = get_log_level()
        assert level == logging.DEBUG

    @patch.dict(os.environ, {"ENVIRONMENT": "staging"}, clear=True)
    def test_staging_environment(self):
        """Test log level for staging environment"""
        level = get_log_level()
        assert level == logging.INFO

    @patch.dict(os.environ, {"ENVIRONMENT": "production"}, clear=True)
    def test_production_environment(self):
        """Test log level for production environment"""
        level = get_log_level()
        assert level == logging.WARNING

    def test_default_log_level(self):
        """Test default log level when no environment is set"""
        # Clear all relevant environment variables
        with patch.dict(os.environ, {}, clear=True):
            # Force module reload to pick up cleared environment
            from dags.market_data.config import logging_config
            import importlib
            importlib.reload(logging_config)
            from dags.market_data.config.logging_config import get_log_level
            
            level = get_log_level()
            assert level == logging.INFO


class TestGetLogFormat:
    """Test get_log_format function"""

    @patch.dict(os.environ, {"AIRFLOW__LOGGING__JSON_FORMAT": "true"})
    def test_json_format_enabled(self):
        """Test JSON format when enabled"""
        format_str = get_log_format()
        assert "timestamp" in format_str
        assert "logger" in format_str
        assert "level" in format_str

    @patch.dict(os.environ, {"AIRFLOW__LOGGING__JSON_FORMAT": "false"}, clear=True)
    def test_default_format(self):
        """Test default log format"""
        format_str = get_log_format()
        assert "asctime" in format_str
        assert "name" in format_str
        assert "levelname" in format_str


class TestGetSentryConfig:
    """Test get_sentry_config function"""

    @patch.dict(
        os.environ,
        {
            "SENTRY_DSN": "https://test@sentry.io/123",
            "ENVIRONMENT": "staging",
            "SENTRY_TRACES_SAMPLE_RATE": "0.5",
            "SENTRY_SEND_PII": "true",
        },
    )
    def test_sentry_config_with_all_options(self):
        """Test Sentry config with all options set"""
        config = get_sentry_config()

        assert config is not None
        assert config["dsn"] == "https://test@sentry.io/123"
        assert config["environment"] == "staging"
        assert config["traces_sample_rate"] == 0.5
        assert config["send_default_pii"] is True

    @patch.dict(
        os.environ,
        {"SENTRY_DSN": "https://test@sentry.io/123"},
        clear=True,
    )
    def test_sentry_config_with_defaults(self):
        """Test Sentry config with default values"""
        config = get_sentry_config()

        assert config is not None
        assert config["dsn"] == "https://test@sentry.io/123"
        assert config["environment"] == "development"
        assert config["traces_sample_rate"] == 0.1
        assert config["send_default_pii"] is False

    @patch.dict(os.environ, {}, clear=True)
    def test_sentry_config_not_available(self):
        """Test Sentry config when DSN is not set"""
        config = get_sentry_config()
        assert config is None


class TestGetDatadogConfig:
    """Test get_datadog_config function"""

    @patch.dict(
        os.environ,
        {
            "DD_API_KEY": "test_api_key",
            "DD_APP_KEY": "test_app_key",
            "DD_SITE": "datadoghq.eu",
            "DD_SERVICE": "custom-service",
            "ENVIRONMENT": "production",
        },
    )
    def test_datadog_config_with_all_options(self):
        """Test Datadog config with all options set"""
        config = get_datadog_config()

        assert config is not None
        assert config["api_key"] == "test_api_key"
        assert config["app_key"] == "test_app_key"
        assert config["site"] == "datadoghq.eu"
        assert config["service"] == "custom-service"
        assert config["env"] == "production"

    @patch.dict(
        os.environ,
        {"DD_API_KEY": "test_api_key"},
        clear=True,
    )
    def test_datadog_config_with_defaults(self):
        """Test Datadog config with default values"""
        config = get_datadog_config()

        assert config is not None
        assert config["api_key"] == "test_api_key"
        assert config["app_key"] is None
        assert config["site"] == "datadoghq.com"
        assert config["service"] == "airflow-market-data"
        assert config["env"] == "development"

    @patch.dict(os.environ, {}, clear=True)
    def test_datadog_config_not_available(self):
        """Test Datadog config when API key is not set"""
        config = get_datadog_config()
        assert config is None

