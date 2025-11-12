"""
Logging configuration for market_data DAG.

This module provides centralized logging configuration with support for:
- Structured logging (JSON format)
- Environment-based log levels
- Future integration with Sentry, Datadog, or other monitoring tools
- Contextual information (task_id, execution_date, etc.)
"""

import logging
import os
from typing import Any, Dict, Optional

# Log levels by environment
LOG_LEVELS = {
    "development": logging.DEBUG,
    "dev": logging.DEBUG,
    "staging": logging.INFO,
    "production": logging.WARNING,
    "prod": logging.WARNING,
}

# Default configuration
DEFAULT_LOG_LEVEL = logging.INFO
DEFAULT_LOG_FORMAT = (
    "%(asctime)s - %(name)s - %(levelname)s - "
    "[%(filename)s:%(lineno)d] - %(message)s"
)
JSON_LOG_FORMAT = (
    '{"timestamp": "%(asctime)s", "logger": "%(name)s", '
    '"level": "%(levelname)s", "file": "%(filename)s", '
    '"line": %(lineno)d, "message": "%(message)s"}'
)


def get_log_level() -> int:
    """
    Get log level based on environment.

    Priority:
    1. AIRFLOW__LOGGING__LEVEL environment variable
    2. ENVIRONMENT environment variable (maps to preset levels)
    3. DEFAULT_LOG_LEVEL

    Returns:
        int: Logging level constant from logging module
    """
    # Check explicit log level setting
    log_level_str = os.environ.get("AIRFLOW__LOGGING__LEVEL", "").upper()
    if log_level_str and hasattr(logging, log_level_str):
        return getattr(logging, log_level_str)

    # Check environment-based log level
    environment = os.environ.get("ENVIRONMENT", "development").lower()
    return LOG_LEVELS.get(environment, DEFAULT_LOG_LEVEL)


def get_log_format() -> str:
    """
    Get log format based on configuration.

    Returns:
        str: Log format string
    """
    use_json = os.environ.get("AIRFLOW__LOGGING__JSON_FORMAT", "false").lower()
    if use_json in ("true", "1", "yes"):
        return JSON_LOG_FORMAT
    return DEFAULT_LOG_FORMAT


def get_sentry_config() -> Optional[Dict[str, Any]]:
    """
    Get Sentry configuration if available.

    Returns:
        Optional[Dict[str, Any]]: Sentry configuration dict or None
    """
    sentry_dsn = os.environ.get("SENTRY_DSN")
    if not sentry_dsn:
        return None

    return {
        "dsn": sentry_dsn,
        "environment": os.environ.get("ENVIRONMENT", "development"),
        "traces_sample_rate": float(
            os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.1")
        ),
        "send_default_pii": os.environ.get("SENTRY_SEND_PII", "false").lower()
        in ("true", "1", "yes"),
    }


def get_datadog_config() -> Optional[Dict[str, Any]]:
    """
    Get Datadog configuration if available.

    Returns:
        Optional[Dict[str, Any]]: Datadog configuration dict or None
    """
    dd_api_key = os.environ.get("DD_API_KEY")
    if not dd_api_key:
        return None

    return {
        "api_key": dd_api_key,
        "app_key": os.environ.get("DD_APP_KEY"),
        "site": os.environ.get("DD_SITE", "datadoghq.com"),
        "service": os.environ.get("DD_SERVICE", "airflow-market-data"),
        "env": os.environ.get("ENVIRONMENT", "development"),
    }


# Export configuration
LOGGING_CONFIG = {
    "level": get_log_level(),
    "format": get_log_format(),
    "sentry": get_sentry_config(),
    "datadog": get_datadog_config(),
}

