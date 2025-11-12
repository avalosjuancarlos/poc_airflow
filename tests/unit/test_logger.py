"""
Unit tests for centralized logging system
"""

import logging
import os
from unittest.mock import MagicMock, patch

import pytest

from dags.market_data.utils.logger import (
    MarketDataLogger,
    get_logger,
    log_errors,
    log_execution,
)


class TestMarketDataLogger:
    """Test MarketDataLogger class"""

    def test_logger_initialization(self):
        """Test logger initialization"""
        logger = MarketDataLogger("test_logger")
        assert logger.name == "test_logger"
        assert logger.logger is not None
        assert isinstance(logger.logger, logging.Logger)

    def test_set_and_clear_context(self):
        """Test setting and clearing context"""
        logger = MarketDataLogger("test_logger")

        # Set context
        logger.set_context(task_id="test_task", execution_date="2023-11-09")
        assert logger._context["task_id"] == "test_task"
        assert logger._context["execution_date"] == "2023-11-09"

        # Clear context
        logger.clear_context()
        assert len(logger._context) == 0

    def test_format_message_with_context(self):
        """Test message formatting with context"""
        logger = MarketDataLogger("test_logger")
        logger.set_context(task_id="test_task")

        message = logger._format_message(
            "Test message", extra={"key": "value"}
        )
        assert "task_id=test_task" in message
        assert "key=value" in message
        assert "Test message" in message

    def test_format_message_without_context(self):
        """Test message formatting without context"""
        logger = MarketDataLogger("test_logger")
        message = logger._format_message("Test message")
        assert message == "Test message"

    @patch("dags.market_data.utils.logger.MarketDataLogger.logger")
    def test_debug_logging(self, mock_logger):
        """Test debug level logging"""
        logger = MarketDataLogger("test_logger")
        logger.logger = mock_logger

        logger.debug("Debug message", extra={"key": "value"})
        mock_logger.debug.assert_called_once()

    @patch("dags.market_data.utils.logger.MarketDataLogger.logger")
    def test_info_logging(self, mock_logger):
        """Test info level logging"""
        logger = MarketDataLogger("test_logger")
        logger.logger = mock_logger

        logger.info("Info message", extra={"key": "value"})
        mock_logger.info.assert_called_once()

    @patch("dags.market_data.utils.logger.MarketDataLogger.logger")
    def test_warning_logging(self, mock_logger):
        """Test warning level logging"""
        logger = MarketDataLogger("test_logger")
        logger.logger = mock_logger

        logger.warning("Warning message", extra={"key": "value"})
        mock_logger.warning.assert_called_once()

    @patch("dags.market_data.utils.logger.MarketDataLogger.logger")
    def test_error_logging(self, mock_logger):
        """Test error level logging"""
        logger = MarketDataLogger("test_logger")
        logger.logger = mock_logger

        logger.error("Error message", extra={"key": "value"}, exc_info=True)
        mock_logger.error.assert_called_once()

    @patch("dags.market_data.utils.logger.MarketDataLogger.logger")
    def test_exception_logging(self, mock_logger):
        """Test exception logging"""
        logger = MarketDataLogger("test_logger")
        logger.logger = mock_logger

        logger.exception("Exception message", extra={"key": "value"})
        mock_logger.exception.assert_called_once()

    @patch("dags.market_data.utils.logger.MarketDataLogger.logger")
    def test_metric_logging(self, mock_logger):
        """Test metric logging"""
        logger = MarketDataLogger("test_logger")
        logger.logger = mock_logger

        logger.metric("test_metric", 100, tags={"environment": "test"})
        mock_logger.info.assert_called_once()
        args = mock_logger.info.call_args[0]
        assert "METRIC: test_metric=100" in args[0]
        assert "environment=test" in args[0]

    @patch("dags.market_data.utils.logger.MarketDataLogger.logger")
    def test_audit_logging(self, mock_logger):
        """Test audit logging"""
        logger = MarketDataLogger("test_logger")
        logger.logger = mock_logger

        logger.audit("user_action", details={"user": "test_user", "action": "login"})
        mock_logger.info.assert_called_once()
        args = mock_logger.info.call_args[0]
        assert "AUDIT: user_action" in args[0]
        assert "user=test_user" in args[0]
        assert "action=login" in args[0]

    @patch("dags.market_data.utils.logger.MarketDataLogger.logger")
    def test_execution_timer(self, mock_logger):
        """Test execution timer context manager"""
        logger = MarketDataLogger("test_logger")
        logger.logger = mock_logger

        with logger.execution_timer("test_operation"):
            pass  # Simulate operation

        # Should log start, metric, and completion
        assert mock_logger.info.call_count >= 2


class TestLogExecutionDecorator:
    """Test log_execution decorator"""

    @patch("dags.market_data.utils.logger.get_logger")
    def test_log_execution_success(self, mock_get_logger):
        """Test decorator logs successful execution"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        @log_execution()
        def test_function():
            return "success"

        result = test_function()

        assert result == "success"
        assert mock_logger.info.call_count >= 2  # Start and completion
        assert mock_logger.metric.called

    @patch("dags.market_data.utils.logger.get_logger")
    def test_log_execution_with_exception(self, mock_get_logger):
        """Test decorator logs exceptions"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        @log_execution()
        def test_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            test_function()

        assert mock_logger.exception.called
        assert mock_logger.metric.called


class TestLogErrorsDecorator:
    """Test log_errors decorator"""

    @patch("dags.market_data.utils.logger.get_logger")
    def test_log_errors_with_reraise(self, mock_get_logger):
        """Test decorator logs and reraises errors"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        @log_errors(reraise=True)
        def test_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            test_function()

        assert mock_logger.exception.called

    @patch("dags.market_data.utils.logger.get_logger")
    def test_log_errors_without_reraise(self, mock_get_logger):
        """Test decorator logs but suppresses errors"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        @log_errors(reraise=False)
        def test_function():
            raise ValueError("Test error")

        # Should not raise
        test_function()

        assert mock_logger.exception.called


class TestGetLogger:
    """Test get_logger function"""

    def test_get_logger_creates_new(self):
        """Test getting a new logger"""
        logger = get_logger("test.new.logger")
        assert isinstance(logger, MarketDataLogger)
        assert logger.name == "test.new.logger"

    def test_get_logger_returns_existing(self):
        """Test getting an existing logger"""
        logger1 = get_logger("test.existing.logger")
        logger2 = get_logger("test.existing.logger")

        # Should return the same instance
        assert logger1 is logger2

