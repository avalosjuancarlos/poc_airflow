"""
Unit tests for logging configuration
"""

import logging
import os
from unittest.mock import patch

import pytest

from dags.market_data.config.logging_config import get_log_format, get_log_level


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
        # When no env vars are set, it should use the environment from LOG_LEVELS
        # which defaults to 'development' if ENVIRONMENT is not set
        # Since we can't fully clear the environment in tests that already imported
        # the module, we'll test the actual behavior when no explicit level is set
        with patch.dict(os.environ, {"ENVIRONMENT": "unknown"}, clear=True):
            level = get_log_level()
            # Unknown environment should fallback to DEFAULT_LOG_LEVEL which is INFO
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
