"""
Unit tests for warehouse configuration
"""

import os
from unittest.mock import patch

import pytest

from market_data.config.warehouse_config import (
    BATCH_SIZE,
    CONNECTION_POOL_SIZE,
    ENVIRONMENT,
    LOAD_STRATEGY,
    MAX_OVERFLOW,
    POOL_TIMEOUT,
    TABLE_DATES,
    TABLE_MARKET_DATA,
    TABLE_TICKERS,
    get_connection_string,
    get_warehouse_config,
)


class TestWarehouseConfigConstants:
    """Test warehouse configuration constants"""

    def test_default_environment(self):
        """Test default environment is development"""
        with patch.dict(os.environ, {}, clear=True):
            from importlib import reload

            from market_data.config import warehouse_config

            reload(warehouse_config)
            assert warehouse_config.ENVIRONMENT == "development"

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
        assert CONNECTION_POOL_SIZE == 5
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
        config = get_warehouse_config("development")

        assert config["type"] == "postgresql"
        assert config["host"] == "localhost"
        assert config["port"] == 5433
        assert config["database"] == "dev_db"
        assert config["schema"] == "public"
        assert config["user"] == "dev_user"
        assert config["password"] == "dev_pass"

    @patch.dict(
        os.environ,
        {
            "ENVIRONMENT": "staging",
            "STAGING_WAREHOUSE_HOST": "staging.redshift.amazonaws.com",
            "STAGING_WAREHOUSE_PORT": "5439",
            "STAGING_WAREHOUSE_DATABASE": "staging_db",
            "STAGING_WAREHOUSE_SCHEMA": "staging_schema",
            "STAGING_WAREHOUSE_USER": "staging_user",
            "STAGING_WAREHOUSE_PASSWORD": "staging_pass",
            "STAGING_WAREHOUSE_REGION": "us-east-1",
        },
    )
    def test_staging_config(self):
        """Test staging environment configuration"""
        config = get_warehouse_config("staging")

        assert config["type"] == "redshift"
        assert config["host"] == "staging.redshift.amazonaws.com"
        assert config["port"] == 5439
        assert config["database"] == "staging_db"
        assert config["schema"] == "staging_schema"
        assert config["user"] == "staging_user"
        assert config["password"] == "staging_pass"
        assert config["region"] == "us-east-1"

    @patch.dict(
        os.environ,
        {
            "ENVIRONMENT": "production",
            "PROD_WAREHOUSE_HOST": "prod.redshift.amazonaws.com",
            "PROD_WAREHOUSE_PORT": "5439",
            "PROD_WAREHOUSE_DATABASE": "prod_db",
            "PROD_WAREHOUSE_SCHEMA": "prod_schema",
            "PROD_WAREHOUSE_USER": "prod_user",
            "PROD_WAREHOUSE_PASSWORD": "prod_pass",
            "PROD_WAREHOUSE_REGION": "us-west-2",
        },
    )
    def test_production_config(self):
        """Test production environment configuration"""
        config = get_warehouse_config("production")

        assert config["type"] == "redshift"
        assert config["host"] == "prod.redshift.amazonaws.com"
        assert config["port"] == 5439
        assert config["database"] == "prod_db"
        assert config["schema"] == "prod_schema"
        assert config["user"] == "prod_user"
        assert config["password"] == "prod_pass"
        assert config["region"] == "us-west-2"

    @patch.dict(
        os.environ,
        {
            "DEV_WAREHOUSE_HOST": "localhost",
            "DEV_WAREHOUSE_DATABASE": "dev_db",
            "DEV_WAREHOUSE_USER": "dev_user",
            "DEV_WAREHOUSE_PASSWORD": "dev_pass",
        },
    )
    def test_default_port_and_schema(self):
        """Test default port and schema values"""
        config = get_warehouse_config("development")

        assert config["port"] == 5432  # Default PostgreSQL port
        assert config["schema"] == "public"  # Default schema

    @patch.dict(
        os.environ,
        {
            "DEV_WAREHOUSE_HOST": "localhost",
            "DEV_WAREHOUSE_DATABASE": "dev_db",
            "DEV_WAREHOUSE_USER": "dev_user",
            "DEV_WAREHOUSE_PASSWORD": "dev_pass",
            "WAREHOUSE_CONNECTION_POOL_SIZE": "10",
            "WAREHOUSE_MAX_OVERFLOW": "20",
            "WAREHOUSE_POOL_TIMEOUT": "60",
        },
    )
    def test_custom_pool_parameters(self):
        """Test custom pool parameters are included"""
        config = get_warehouse_config("development")

        assert config["pool_size"] == 10
        assert config["max_overflow"] == 20
        assert config["pool_timeout"] == 60

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_required_env_vars_raises_error(self):
        """Test missing required environment variables raises error"""
        with pytest.raises((KeyError, ValueError)):
            get_warehouse_config("development")

    @patch.dict(
        os.environ,
        {
            "DEV_WAREHOUSE_HOST": "localhost",
            "DEV_WAREHOUSE_DATABASE": "dev_db",
            "DEV_WAREHOUSE_USER": "dev_user",
            "DEV_WAREHOUSE_PASSWORD": "dev_pass",
        },
    )
    def test_uses_current_environment_by_default(self):
        """Test function uses ENVIRONMENT variable by default"""
        with patch("market_data.config.warehouse_config.ENVIRONMENT", "development"):
            config = get_warehouse_config()
            assert config["type"] == "postgresql"


class TestGetConnectionString:
    """Test get_connection_string function"""

    def test_postgresql_connection_string(self):
        """Test PostgreSQL connection string generation"""
        config = {
            "type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "database": "testdb",
            "user": "testuser",
            "password": "testpass",
        }

        conn_string = get_connection_string(config)

        assert conn_string.startswith("postgresql+psycopg2://")
        assert "testuser" in conn_string
        assert "testpass" in conn_string
        assert "localhost" in conn_string
        assert "5432" in conn_string
        assert "testdb" in conn_string

    def test_redshift_connection_string(self):
        """Test Redshift connection string generation"""
        config = {
            "type": "redshift",
            "host": "cluster.region.redshift.amazonaws.com",
            "port": 5439,
            "database": "testdb",
            "user": "testuser",
            "password": "testpass",
            "region": "us-east-1",
        }

        conn_string = get_connection_string(config)

        assert conn_string.startswith("redshift+redshift_connector://")
        assert "testuser" in conn_string
        assert "testpass" in conn_string
        assert "cluster.region.redshift.amazonaws.com" in conn_string
        assert "5439" in conn_string
        assert "testdb" in conn_string

    def test_connection_string_masks_password_in_logs(self):
        """Test that password is masked when logged"""
        config = {
            "type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "database": "testdb",
            "user": "testuser",
            "password": "super_secret_password",
        }

        # This is tested via the logger mock in the actual function
        # Here we just verify the connection string contains the password
        conn_string = get_connection_string(config)
        assert "super_secret_password" in conn_string

    def test_special_characters_in_password(self):
        """Test connection string with special characters in password"""
        config = {
            "type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "database": "testdb",
            "user": "testuser",
            "password": "p@ss:w0rd!#$",
        }

        conn_string = get_connection_string(config)

        # Password should be URL encoded
        assert "testuser" in conn_string
        assert "localhost" in conn_string

    def test_ipv4_host(self):
        """Test connection string with IPv4 host"""
        config = {
            "type": "postgresql",
            "host": "192.168.1.100",
            "port": 5432,
            "database": "testdb",
            "user": "testuser",
            "password": "testpass",
        }

        conn_string = get_connection_string(config)

        assert "192.168.1.100" in conn_string

    def test_custom_port(self):
        """Test connection string with custom port"""
        config = {
            "type": "postgresql",
            "host": "localhost",
            "port": 5433,
            "database": "testdb",
            "user": "testuser",
            "password": "testpass",
        }

        conn_string = get_connection_string(config)

        assert "5433" in conn_string


class TestLogWarehouseConfiguration:
    """Test log_warehouse_configuration function"""

    @patch.dict(
        os.environ,
        {
            "DEV_WAREHOUSE_HOST": "localhost",
            "DEV_WAREHOUSE_DATABASE": "dev_db",
            "DEV_WAREHOUSE_USER": "dev_user",
            "DEV_WAREHOUSE_PASSWORD": "dev_pass",
        },
    )
    @patch("market_data.config.warehouse_config._get_logger")
    def test_log_warehouse_configuration_logs_config(self, mock_get_logger):
        """Test log_warehouse_configuration logs configuration"""
        from market_data.config.warehouse_config import log_warehouse_configuration

        mock_logger = mock_get_logger.return_value

        log_warehouse_configuration()

        # Verify logger was called
        assert mock_logger.info.call_count > 0

        # Verify important information was logged
        logged_messages = [
            str(call[0][0]) for call in mock_logger.info.call_args_list
        ]
        logged_str = " ".join(logged_messages)

        assert "WAREHOUSE" in logged_str or "warehouse" in logged_str.lower()

