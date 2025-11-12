"""
Centralized logging module for market_data DAG.

Provides:
- Structured logging with contextual information
- Decorators for automatic function logging
- Metrics tracking (execution times, error rates)
- Integration support for Sentry and Datadog
- Audit logging capabilities
"""

import functools
import logging
import time
from contextlib import contextmanager
from typing import Any, Callable, Dict, Optional

from market_data.config.logging_config import LOGGING_CONFIG

# Sentry integration (optional)
try:
    import sentry_sdk
    from sentry_sdk.integrations.logging import LoggingIntegration

    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False

# Datadog integration (optional)
try:
    import ddtrace  # noqa: F401

    DATADOG_AVAILABLE = True
except ImportError:
    DATADOG_AVAILABLE = False


class MarketDataLogger:
    """
    Centralized logger for market_data module with enhanced capabilities.

    Features:
    - Contextual logging with task information
    - Structured log output
    - Metrics tracking
    - Error reporting to external services
    """

    def __init__(self, name: str):
        """
        Initialize logger.

        Args:
            name: Logger name (usually module name)
        """
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(LOGGING_CONFIG["level"])

        # Setup handler if not already configured
        if not self.logger.handlers:
            self._setup_handler()

        # Initialize integrations
        self._initialize_sentry()
        self._initialize_datadog()

        # Context storage
        self._context: Dict[str, Any] = {}

    def _setup_handler(self):
        """Setup console handler with configured format."""
        handler = logging.StreamHandler()
        handler.setLevel(LOGGING_CONFIG["level"])
        formatter = logging.Formatter(LOGGING_CONFIG["format"])
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def _initialize_sentry(self):
        """Initialize Sentry integration if configured."""
        if not SENTRY_AVAILABLE or not LOGGING_CONFIG["sentry"]:
            return

        try:
            sentry_config = LOGGING_CONFIG["sentry"]
            sentry_logging = LoggingIntegration(
                level=logging.INFO, event_level=logging.ERROR
            )

            sentry_sdk.init(
                dsn=sentry_config["dsn"],
                environment=sentry_config["environment"],
                traces_sample_rate=sentry_config["traces_sample_rate"],
                send_default_pii=sentry_config["send_default_pii"],
                integrations=[sentry_logging],
            )
            self.logger.info("Sentry integration initialized")
        except Exception as e:
            self.logger.warning(f"Failed to initialize Sentry: {e}")

    def _initialize_datadog(self):
        """Initialize Datadog integration if configured."""
        if not DATADOG_AVAILABLE or not LOGGING_CONFIG["datadog"]:
            return

        try:
            # Datadog is configured via environment variables
            # Just log that it's available
            self.logger.info("Datadog tracing available")
        except Exception as e:
            self.logger.warning(f"Failed to initialize Datadog: {e}")

    def set_context(self, **kwargs):
        """
        Set contextual information for logging.

        Args:
            **kwargs: Context key-value pairs (task_id, execution_date, etc.)
        """
        self._context.update(kwargs)

    def clear_context(self):
        """Clear all contextual information."""
        self._context.clear()

    def _format_message(self, message: str, extra: Optional[Dict] = None) -> str:
        """
        Format message with context.

        Args:
            message: Log message
            extra: Additional context

        Returns:
            str: Formatted message
        """
        context = {**self._context}
        if extra:
            context.update(extra)

        if context:
            context_str = " | ".join(f"{k}={v}" for k, v in context.items())
            return f"[{context_str}] {message}"
        return message

    def debug(self, message: str, extra: Optional[Dict] = None):
        """Log debug message."""
        self.logger.debug(self._format_message(message, extra))

    def info(self, message: str, extra: Optional[Dict] = None):
        """Log info message."""
        self.logger.info(self._format_message(message, extra))

    def warning(self, message: str, extra: Optional[Dict] = None):
        """Log warning message."""
        self.logger.warning(self._format_message(message, extra))

    def error(
        self,
        message: str,
        extra: Optional[Dict] = None,
        exc_info: bool = False,
        send_to_sentry: bool = True,
    ):
        """
        Log error message.

        Args:
            message: Error message
            extra: Additional context
            exc_info: Include exception info
            send_to_sentry: Send to Sentry if available
        """
        self.logger.error(self._format_message(message, extra), exc_info=exc_info)

        if send_to_sentry and SENTRY_AVAILABLE and LOGGING_CONFIG["sentry"]:
            try:
                sentry_sdk.capture_message(message, level="error")
            except Exception:
                pass  # Fail silently if Sentry is unavailable

    def exception(
        self, message: str, extra: Optional[Dict] = None, send_to_sentry: bool = True
    ):
        """
        Log exception with traceback.

        Args:
            message: Exception message
            extra: Additional context
            send_to_sentry: Send to Sentry if available
        """
        self.logger.exception(self._format_message(message, extra))

        if send_to_sentry and SENTRY_AVAILABLE and LOGGING_CONFIG["sentry"]:
            try:
                sentry_sdk.capture_exception()
            except Exception:
                pass  # Fail silently if Sentry is unavailable

    def metric(self, metric_name: str, value: Any, tags: Optional[Dict] = None):
        """
        Log metric for monitoring.

        Args:
            metric_name: Metric name
            value: Metric value
            tags: Additional tags
        """
        tags_str = ""
        if tags:
            tags_str = " | " + " | ".join(f"{k}={v}" for k, v in tags.items())

        self.info(f"METRIC: {metric_name}={value}{tags_str}")

    def audit(self, action: str, details: Optional[Dict] = None):
        """
        Log audit event.

        Args:
            action: Action performed
            details: Action details
        """
        details_str = ""
        if details:
            details_str = " | " + " | ".join(f"{k}={v}" for k, v in details.items())

        self.info(f"AUDIT: {action}{details_str}")

    @contextmanager
    def execution_timer(self, operation: str):
        """
        Context manager to time operation execution.

        Args:
            operation: Operation name

        Yields:
            None
        """
        start_time = time.time()
        self.info(f"Starting: {operation}")

        try:
            yield
        finally:
            elapsed_time = time.time() - start_time
            self.metric(
                f"{operation}_duration", f"{elapsed_time:.3f}s", {"unit": "seconds"}
            )
            self.info(f"Completed: {operation} in {elapsed_time:.3f}s")


# Decorator functions
def log_execution(logger: Optional[MarketDataLogger] = None):
    """
    Decorator to log function execution.

    Args:
        logger: Logger instance (created if not provided)

    Returns:
        Callable: Decorated function
    """

    def decorator(func: Callable) -> Callable:
        nonlocal logger
        if logger is None:
            logger = get_logger(func.__module__)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            func_name = func.__qualname__
            logger.info(f"Executing function: {func_name}")

            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed_time = time.time() - start_time
                logger.metric(
                    f"function.{func_name}.duration",
                    f"{elapsed_time:.3f}s",
                    {"status": "success"},
                )
                logger.info(f"Completed function: {func_name} in {elapsed_time:.3f}s")
                return result
            except Exception as e:
                elapsed_time = time.time() - start_time
                logger.metric(
                    f"function.{func_name}.duration",
                    f"{elapsed_time:.3f}s",
                    {"status": "error"},
                )
                logger.exception(
                    f"Error in function: {func_name} after {elapsed_time:.3f}s",
                    extra={"error_type": type(e).__name__, "error": str(e)},
                )
                raise

        return wrapper

    return decorator


def log_errors(logger: Optional[MarketDataLogger] = None, reraise: bool = True):
    """
    Decorator to log and optionally suppress errors.

    Args:
        logger: Logger instance
        reraise: Whether to reraise the exception

    Returns:
        Callable: Decorated function
    """

    def decorator(func: Callable) -> Callable:
        nonlocal logger
        if logger is None:
            logger = get_logger(func.__module__)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.exception(
                    f"Error in {func.__qualname__}",
                    extra={"error_type": type(e).__name__, "error": str(e)},
                )
                if reraise:
                    raise

        return wrapper

    return decorator


# Global logger registry
_loggers: Dict[str, MarketDataLogger] = {}


def get_logger(name: str) -> MarketDataLogger:
    """
    Get or create logger for given name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        MarketDataLogger: Logger instance
    """
    if name not in _loggers:
        _loggers[name] = MarketDataLogger(name)
    return _loggers[name]


# Convenience function for DAG context
def set_dag_context(task_id: str, execution_date: str, dag_id: str = "get_market_data"):
    """
    Set DAG execution context for all loggers.

    Args:
        task_id: Airflow task ID
        execution_date: Execution date
        dag_id: DAG ID
    """
    context = {"dag_id": dag_id, "task_id": task_id, "execution_date": execution_date}

    for logger in _loggers.values():
        logger.set_context(**context)
