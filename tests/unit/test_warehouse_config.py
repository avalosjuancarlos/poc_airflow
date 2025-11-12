"""
Unit tests for warehouse configuration
"""

import os
from unittest.mock import patch

import pytest
from market_data.config.warehouse_config import (
    BATCH_SIZE,
    ENVIRONMENT,
    LOAD_STRATEGY,
    MAX_OVERFLOW,
    POOL_SIZE,
    POOL_TIMEOUT,
    TABLE_DATES,
    TABLE_MARKET_DATA,
    TABLE_TICKERS,
    get_connection_string,
    get_warehouse_config,
)


class TestWarehouseConfigConstants:
    """Test warehouse configuration constants"""

    def test_load_strategy_default(self):
        """Test default load strategy is upsert"""
        assert LOAD_STRATEGY == "upsert"

    def test_table_names_defined(self):
        """Test table names are defined"""
        assert TABLE_MARKET_DATA == "fact_market_data"
        assert TABLE_TICKERS == "dim_tickers"
        assert TABLE_DATES == "dim_dates"

    def test_connection_pool_defaults(self):
        """Test connection pool default values"""
        assert POOL_SIZE == 5
        assert MAX_OVERFLOW == 10
        assert POOL_TIMEOUT == 30

    def test_batch_size_default(self):
        """Test default batch size"""
        assert BATCH_SIZE == 1000


class TestGetWarehouseConfig:
    """Test get_warehouse_config function"""

    @patch.dict(
        os.environ,
        {
            "ENVIRONMENT": "development",
            "DEV_WAREHOUSE_HOST": "localhost",
            "DEV_WAREHOUSE_PORT": "5433",
            "DEV_WAREHOUSE_DATABASE": "dev_db",
            "DEV_WAREHOUSE_SCHEMA": "public",
            "DEV_WAREHOUSE_USER": "dev_user",
            "DEV_WAREHOUSE_PASSWORD": "dev_pass",
        },
    )
    def test_development_config(self):
        """Test development environment configuration"""
        from importlib import reload

        from market_data.config import warehouse_config

        reload(warehouse_config)
        config = warehouse_config.get_warehouse_config()

        assert config["type"] == "postgresql"
        assert config["host"] == "localhost"
        assert config["port"] == "5433"
        assert config["database"] == "dev_db"
        assert config["schema"] == "public"
        assert config["user"] == "dev_user"
        assert config["password"] == "dev_pass"


class TestGetConnectionString:
    """Test get_connection_string function"""

    @patch("market_data.config.warehouse_config.get_warehouse_config")
    def test_postgresql_connection_string(self, mock_get_config):
        """Test PostgreSQL connection string generation"""
        mock_get_config.return_value = {
            "type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "database": "testdb",
            "user": "testuser",
            "password": "testpass",
        }

        conn_string = get_connection_string()

        # Connection string is masked for security, check key components
        assert "localhost" in conn_string
        assert "5432" in conn_string
        assert "testdb" in conn_string
        # Password is masked with *** for security
        assert "***" in conn_string or "testpass" not in conn_string

    @patch("market_data.config.warehouse_config.get_warehouse_config")
    def test_redshift_connection_string(self, mock_get_config):
        """Test Redshift connection string generation"""
        mock_get_config.return_value = {
            "type": "redshift",
            "host": "cluster.region.redshift.amazonaws.com",
            "port": 5439,
            "database": "testdb",
            "user": "testuser",
            "password": "testpass",
            "region": "us-east-1",
        }

        conn_string = get_connection_string()

        # Connection string is masked for security, check key components
        assert "cluster.region.redshift.amazonaws.com" in conn_string
        assert "5439" in conn_string
        assert "testdb" in conn_string
        # Password is masked with *** for security
        assert "***" in conn_string or "testpass" not in conn_string
