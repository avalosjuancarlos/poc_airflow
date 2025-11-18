"""
Unit tests for warehouse configuration
"""

import os
from unittest.mock import MagicMock, patch

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

        # Verify connection string has correct format and components
        assert conn_string.startswith("postgresql://")
        assert "testuser" in conn_string
        assert "localhost" in conn_string
        assert "5432" in conn_string
        assert "testdb" in conn_string
        # Note: Password must be in connection string for SQLAlchemy to work

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

        # Verify connection string has correct format and components
        assert conn_string.startswith("redshift+psycopg2://")
        assert "testuser" in conn_string
        assert "cluster.region.redshift.amazonaws.com" in conn_string
        assert "5439" in conn_string
        assert "testdb" in conn_string
        # Note: Password must be in connection string for SQLAlchemy to work

    @patch("market_data.config.warehouse_config.get_warehouse_config")
    def test_unsupported_warehouse_type(self, mock_get_config):
        """Test connection string with unsupported warehouse type"""
        mock_get_config.return_value = {
            "type": "mysql",
            "host": "localhost",
            "port": 3306,
            "database": "testdb",
            "user": "testuser",
            "password": "testpass",
        }

        with pytest.raises(ValueError, match="Unsupported warehouse type"):
            get_connection_string()


class TestGetWarehouseConfigStaging:
    """Test get_warehouse_config for staging environment"""

    @patch.dict(
        os.environ,
        {
            "ENVIRONMENT": "staging",
            "STAGING_WAREHOUSE_HOST": "staging-cluster.redshift.amazonaws.com",
            "STAGING_WAREHOUSE_PORT": "5439",
            "STAGING_WAREHOUSE_DATABASE": "staging_db",
            "STAGING_WAREHOUSE_SCHEMA": "public",
            "STAGING_WAREHOUSE_USER": "staging_user",
            "STAGING_WAREHOUSE_PASSWORD": "staging_pass",
            "STAGING_WAREHOUSE_REGION": "us-west-2",
        },
        clear=True,
    )
    def test_staging_config(self):
        """Test staging environment configuration"""
        from importlib import reload

        from market_data.config import warehouse_config

        reload(warehouse_config)
        config = warehouse_config.get_warehouse_config()

        assert config["type"] == "redshift"
        assert config["host"] == "staging-cluster.redshift.amazonaws.com"
        assert config["port"] == "5439"
        assert config["database"] == "staging_db"
        assert config["schema"] == "public"
        assert config["user"] == "staging_user"
        assert config["password"] == "staging_pass"
        assert config["region"] == "us-west-2"


class TestGetWarehouseConfigProduction:
    """Test get_warehouse_config for production environment"""

    @patch.dict(
        os.environ,
        {
            "ENVIRONMENT": "production",
            "PROD_WAREHOUSE_HOST": "prod-cluster.redshift.amazonaws.com",
            "PROD_WAREHOUSE_PORT": "5439",
            "PROD_WAREHOUSE_DATABASE": "prod_db",
            "PROD_WAREHOUSE_SCHEMA": "public",
            "PROD_WAREHOUSE_USER": "prod_user",
            "PROD_WAREHOUSE_PASSWORD": "prod_pass",
            "PROD_WAREHOUSE_REGION": "us-east-1",
        },
        clear=True,
    )
    def test_production_config(self):
        """Test production environment configuration"""
        from importlib import reload

        from market_data.config import warehouse_config

        reload(warehouse_config)
        config = warehouse_config.get_warehouse_config()

        assert config["type"] == "redshift"
        assert config["host"] == "prod-cluster.redshift.amazonaws.com"
        assert config["port"] == "5439"
        assert config["database"] == "prod_db"
        assert config["schema"] == "public"
        assert config["user"] == "prod_user"
        assert config["password"] == "prod_pass"
        assert config["region"] == "us-east-1"


class TestGetWarehouseConfigErrors:
    """Test error cases for get_warehouse_config"""

    @patch.dict(os.environ, {"ENVIRONMENT": "unknown"}, clear=True)
    def test_unknown_environment(self):
        """Test unknown environment raises ValueError"""
        from importlib import reload

        from market_data.config import warehouse_config

        reload(warehouse_config)

        with pytest.raises(ValueError, match="Unknown environment"):
            warehouse_config.get_warehouse_config()

    @patch.dict(
        os.environ,
        {
            "ENVIRONMENT": "development",
            "DEV_WAREHOUSE_HOST": "",  # Missing required field
            "DEV_WAREHOUSE_DATABASE": "dev_db",
            "DEV_WAREHOUSE_USER": "dev_user",
            "DEV_WAREHOUSE_PASSWORD": "dev_pass",
        },
        clear=True,
    )
    def test_missing_required_fields(self):
        """Test missing required fields raises ValueError"""
        from importlib import reload

        from market_data.config import warehouse_config

        reload(warehouse_config)

        with pytest.raises(ValueError, match="Missing required warehouse config"):
            warehouse_config.get_warehouse_config()

    @patch.dict(
        os.environ,
        {
            "ENVIRONMENT": "staging",
            "STAGING_WAREHOUSE_HOST": "",  # Missing required field
            "STAGING_WAREHOUSE_DATABASE": "staging_db",
            "STAGING_WAREHOUSE_USER": "staging_user",
            "STAGING_WAREHOUSE_PASSWORD": "staging_pass",
        },
        clear=True,
    )
    def test_missing_required_fields_staging(self):
        """Test missing required fields in staging raises ValueError"""
        from importlib import reload

        from market_data.config import warehouse_config

        reload(warehouse_config)

        with pytest.raises(ValueError, match="Missing required warehouse config"):
            warehouse_config.get_warehouse_config()


class TestGetWarehouseConfigDefaults:
    """Test default values for warehouse config"""

    @patch.dict(
        os.environ,
        {
            "ENVIRONMENT": "development",
            "DEV_WAREHOUSE_HOST": "localhost",
            "DEV_WAREHOUSE_DATABASE": "dev_db",
            "DEV_WAREHOUSE_USER": "dev_user",
            "DEV_WAREHOUSE_PASSWORD": "dev_pass",
        },
        clear=True,
    )
    def test_development_defaults(self):
        """Test development environment uses defaults for optional fields"""
        from importlib import reload

        from market_data.config import warehouse_config

        reload(warehouse_config)
        config = warehouse_config.get_warehouse_config()

        assert config["type"] == "postgresql"  # Default
        assert config["port"] == "5432"  # Default
        assert config["schema"] == "public"  # Default

    @patch.dict(
        os.environ,
        {
            "ENVIRONMENT": "staging",
            "STAGING_WAREHOUSE_HOST": "staging-cluster.redshift.amazonaws.com",
            "STAGING_WAREHOUSE_DATABASE": "staging_db",
            "STAGING_WAREHOUSE_USER": "staging_user",
            "STAGING_WAREHOUSE_PASSWORD": "staging_pass",
        },
        clear=True,
    )
    def test_staging_defaults(self):
        """Test staging environment uses defaults for optional fields"""
        from importlib import reload

        from market_data.config import warehouse_config

        reload(warehouse_config)
        config = warehouse_config.get_warehouse_config()

        assert config["type"] == "redshift"  # Default
        assert config["port"] == "5439"  # Default
        assert config["schema"] == "public"  # Default
        assert config["region"] == "us-east-1"  # Default


class TestLogWarehouseConfiguration:
    """Test log_warehouse_configuration function"""

    @patch("market_data.config.warehouse_config.get_warehouse_config")
    @patch("market_data.config.warehouse_config._get_logger")
    def test_log_warehouse_configuration(self, mock_get_logger, mock_get_config):
        """Test logging warehouse configuration"""
        from market_data.config.warehouse_config import log_warehouse_configuration

        mock_get_config.return_value = {
            "type": "postgresql",
            "host": "localhost",
            "port": "5432",
            "database": "test_db",
            "schema": "public",
            "user": "test_user",
        }
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        log_warehouse_configuration()

        # Verify logger.info was called multiple times
        assert mock_logger.info.call_count >= 10
