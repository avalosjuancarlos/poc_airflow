"""
Warehouse Connection Manager

Manages database connections for PostgreSQL (dev) and Redshift (staging/prod).
"""

from contextlib import contextmanager
from typing import Dict, Generator

from market_data.config.warehouse_config import (
    MAX_OVERFLOW,
    POOL_SIZE,
    POOL_TIMEOUT,
    get_connection_string,
    get_warehouse_config,
)
from market_data.utils import get_logger, log_execution
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool, QueuePool

logger = get_logger(__name__)


class WarehouseConnection:
    """
    Manages warehouse database connections

    Supports:
    - PostgreSQL (development)
    - Redshift (staging/production)
    """

    def __init__(self, config: Dict[str, str] = None):
        """
        Initialize warehouse connection

        Args:
            config: Optional warehouse configuration dict
                   If None, uses environment-based config
        """
        self.config = config or get_warehouse_config()
        self.warehouse_type = self.config["type"]
        self.engine: Engine = None

        logger.set_context(
            warehouse_type=self.warehouse_type, environment=self.config.get("schema")
        )

        logger.info(
            f"Initializing {self.warehouse_type} warehouse connection",
            extra={
                "warehouse_type": self.warehouse_type,
                "host": self.config["host"],
                "database": self.config["database"],
            },
        )

    @log_execution()
    def create_engine(self) -> Engine:
        """
        Create SQLAlchemy engine based on warehouse type

        Returns:
            SQLAlchemy Engine instance
        """
        conn_string = get_connection_string()

        # Configure connection pool based on warehouse type
        if self.warehouse_type == "postgresql":
            # PostgreSQL - use connection pooling
            engine = create_engine(
                conn_string,
                poolclass=QueuePool,
                pool_size=POOL_SIZE,
                max_overflow=MAX_OVERFLOW,
                pool_timeout=POOL_TIMEOUT,
                pool_pre_ping=True,  # Verify connections before use
                echo=False,
            )
            logger.info(
                "PostgreSQL engine created with connection pooling",
                extra={"pool_size": POOL_SIZE, "max_overflow": MAX_OVERFLOW},
            )

        elif self.warehouse_type == "redshift":
            # Redshift - use NullPool (Redshift manages connections)
            engine = create_engine(
                conn_string,
                poolclass=NullPool,  # Redshift handles pooling
                echo=False,
            )
            logger.info("Redshift engine created with NullPool")

        else:
            raise ValueError(f"Unsupported warehouse type: {self.warehouse_type}")

        self.engine = engine

        # Test connection
        try:
            with engine.connect() as conn:
                result = conn.execute("SELECT 1").scalar()
                logger.info(
                    f"✅ Warehouse connection test successful: {result}",
                    extra={"warehouse_type": self.warehouse_type},
                )
                logger.metric(
                    "warehouse.connection.success",
                    1,
                    {"warehouse_type": self.warehouse_type},
                )
        except Exception as e:
            logger.error(
                f"Failed to connect to warehouse: {e}",
                extra={"warehouse_type": self.warehouse_type, "error": str(e)},
                exc_info=True,
            )
            logger.metric(
                "warehouse.connection.failure",
                1,
                {"warehouse_type": self.warehouse_type},
            )
            raise

        return engine

    @contextmanager
    @log_execution()
    def get_connection(self) -> Generator:
        """
        Context manager for warehouse connections

        Yields:
            SQLAlchemy connection

        Example:
            with warehouse.get_connection() as conn:
                conn.execute("SELECT * FROM table")
        """
        if not self.engine:
            self.create_engine()

        connection = self.engine.connect()
        try:
            logger.debug("Warehouse connection acquired")
            yield connection
            connection.commit()
            logger.debug("Warehouse connection committed")
        except Exception as e:
            connection.rollback()
            logger.error(
                f"Transaction rollback: {e}",
                extra={"error": str(e)},
                exc_info=True,
            )
            raise
        finally:
            connection.close()
            logger.debug("Warehouse connection closed")

    def close(self):
        """Close engine and dispose of connection pool"""
        if self.engine:
            self.engine.dispose()
            logger.info("Warehouse engine disposed")
            logger.clear_context()


@log_execution()
def get_warehouse_connection() -> WarehouseConnection:
    """
    Factory function to get warehouse connection based on environment

    Returns:
        WarehouseConnection instance configured for current environment
    """
    return WarehouseConnection()
