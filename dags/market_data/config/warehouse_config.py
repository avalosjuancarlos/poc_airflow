"""
Data Warehouse Configuration

Manages multi-environment warehouse connections (PostgreSQL for dev, Redshift for staging/prod).
"""

import os
from typing import Dict, Literal

from market_data.utils import get_logger

logger = get_logger(__name__)

# Environment detection
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development").lower()

# Warehouse types
WarehouseType = Literal["postgresql", "redshift"]


def get_warehouse_config() -> Dict[str, str]:
    """
    Get warehouse configuration based on current environment

    Returns:
        Dictionary with warehouse connection parameters

    Raises:
        ValueError: If environment is not recognized
    """
    env = ENVIRONMENT

    if env == "development":
        config = {
            "type": os.environ.get("DEV_WAREHOUSE_TYPE", "postgresql"),
            "host": os.environ.get("DEV_WAREHOUSE_HOST", "warehouse-postgres"),
            "port": os.environ.get("DEV_WAREHOUSE_PORT", "5432"),
            "database": os.environ.get(
                "DEV_WAREHOUSE_DATABASE", "market_data_warehouse"
            ),
            "schema": os.environ.get("DEV_WAREHOUSE_SCHEMA", "public"),
            "user": os.environ.get("DEV_WAREHOUSE_USER", "warehouse_user"),
            "password": os.environ.get("DEV_WAREHOUSE_PASSWORD", "warehouse_pass"),
        }
    elif env == "staging":
        config = {
            "type": os.environ.get("STAGING_WAREHOUSE_TYPE", "redshift"),
            "host": os.environ.get("STAGING_WAREHOUSE_HOST"),
            "port": os.environ.get("STAGING_WAREHOUSE_PORT", "5439"),
            "database": os.environ.get("STAGING_WAREHOUSE_DATABASE"),
            "schema": os.environ.get("STAGING_WAREHOUSE_SCHEMA", "public"),
            "user": os.environ.get("STAGING_WAREHOUSE_USER"),
            "password": os.environ.get("STAGING_WAREHOUSE_PASSWORD"),
            "region": os.environ.get("STAGING_WAREHOUSE_REGION", "us-east-1"),
        }
    elif env == "production":
        config = {
            "type": os.environ.get("PROD_WAREHOUSE_TYPE", "redshift"),
            "host": os.environ.get("PROD_WAREHOUSE_HOST"),
            "port": os.environ.get("PROD_WAREHOUSE_PORT", "5439"),
            "database": os.environ.get("PROD_WAREHOUSE_DATABASE"),
            "schema": os.environ.get("PROD_WAREHOUSE_SCHEMA", "public"),
            "user": os.environ.get("PROD_WAREHOUSE_USER"),
            "password": os.environ.get("PROD_WAREHOUSE_PASSWORD"),
            "region": os.environ.get("PROD_WAREHOUSE_REGION", "us-east-1"),
        }
    else:
        raise ValueError(
            f"Unknown environment: {env}. Must be 'development', 'staging', or 'production'"
        )

    # Validate required fields
    required_fields = ["type", "host", "database", "user", "password"]
    missing_fields = [field for field in required_fields if not config.get(field)]

    if missing_fields:
        raise ValueError(
            f"Missing required warehouse config for {env}: {missing_fields}"
        )

    logger.info(
        f"Warehouse config loaded for {env}",
        extra={
            "environment": env,
            "warehouse_type": config["type"],
            "host": config["host"],
            "database": config["database"],
        },
    )

    return config


def get_connection_string() -> str:
    """
    Build SQLAlchemy connection string based on environment

    Returns:
        SQLAlchemy connection string

    Examples:
        Development: postgresql://user:pass@host:5432/db
        Staging/Prod: redshift+psycopg2://user:pass@host:5439/db
    """
    config = get_warehouse_config()
    warehouse_type = config["type"]

    if warehouse_type == "postgresql":
        conn_string = (
            f"postgresql://{config['user']}:{config['password']}@"
            f"{config['host']}:{config['port']}/{config['database']}"
        )
    elif warehouse_type == "redshift":
        conn_string = (
            f"redshift+psycopg2://{config['user']}:{config['password']}@"
            f"{config['host']}:{config['port']}/{config['database']}"
        )
    else:
        raise ValueError(f"Unsupported warehouse type: {warehouse_type}")

    # Don't log password
    safe_conn = conn_string.replace(config["password"], "****")
    logger.debug(f"Connection string: {safe_conn}")

    return conn_string


# Table names (from environment or defaults)
TABLE_MARKET_DATA = os.environ.get("WAREHOUSE_TABLE_MARKET_DATA", "fact_market_data")
TABLE_TICKERS = os.environ.get("WAREHOUSE_TABLE_TICKERS", "dim_tickers")
TABLE_DATES = os.environ.get("WAREHOUSE_TABLE_DATES", "dim_dates")

# Load strategy
LOAD_STRATEGY = os.environ.get("WAREHOUSE_LOAD_STRATEGY", "upsert")
BATCH_SIZE = int(os.environ.get("WAREHOUSE_BATCH_SIZE", "1000"))
ENABLE_PARTITIONS = os.environ.get("WAREHOUSE_ENABLE_PARTITIONS", "true").lower() in [
    "true",
    "1",
    "yes",
]

# Connection pool
POOL_SIZE = int(os.environ.get("WAREHOUSE_POOL_SIZE", "5"))
MAX_OVERFLOW = int(os.environ.get("WAREHOUSE_MAX_OVERFLOW", "10"))
POOL_TIMEOUT = int(os.environ.get("WAREHOUSE_POOL_TIMEOUT", "30"))


def log_warehouse_configuration():
    """Log current warehouse configuration"""
    config = get_warehouse_config()

    logger.info("=" * 70)
    logger.info("DATA WAREHOUSE CONFIGURATION")
    logger.info("=" * 70)
    logger.info(f"Environment: {ENVIRONMENT}")
    logger.info(f"Warehouse Type: {config['type']}")
    logger.info(f"Host: {config['host']}")
    logger.info(f"Port: {config['port']}")
    logger.info(f"Database: {config['database']}")
    logger.info(f"Schema: {config.get('schema', 'N/A')}")
    logger.info(f"User: {config['user']}")
    logger.info("-" * 70)
    logger.info(f"Table - Market Data: {TABLE_MARKET_DATA}")
    logger.info(f"Table - Tickers: {TABLE_TICKERS}")
    logger.info(f"Table - Dates: {TABLE_DATES}")
    logger.info("-" * 70)
    logger.info(f"Load Strategy: {LOAD_STRATEGY}")
    logger.info(f"Batch Size: {BATCH_SIZE}")
    logger.info(f"Enable Partitions: {ENABLE_PARTITIONS}")
    logger.info("-" * 70)
    logger.info(f"Pool Size: {POOL_SIZE}")
    logger.info(f"Max Overflow: {MAX_OVERFLOW}")
    logger.info(f"Pool Timeout: {POOL_TIMEOUT}s")
    logger.info("=" * 70)
