"""
Logging configuration for market_data DAG.

This module provides centralized logging configuration with support for:
- Structured logging (JSON format)
- Environment-based log levels
- Contextual information (task_id, execution_date, etc.)

Note: External monitoring integrations (Sentry, Datadog) can be added
by extending this module. See documentation for integration guides.
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


# Export configuration
LOGGING_CONFIG = {
    "level": get_log_level(),
    "format": get_log_format(),
}
