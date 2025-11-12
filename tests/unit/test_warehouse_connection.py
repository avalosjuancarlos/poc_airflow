"""
Unit tests for warehouse connection management
"""

from unittest.mock import MagicMock, Mock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool, QueuePool

from market_data.warehouse.connection import WarehouseConnection


class TestWarehouseConnection:
    """Test WarehouseConnection class"""

    @patch("market_data.warehouse.connection.create_engine")
    def test_init_postgresql_creates_queue_pool(self, mock_create_engine):
        """Test PostgreSQL uses QueuePool"""
        config = {
            "type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "database": "testdb",
            "user": "testuser",
            "password": "testpass",
        }

        conn = WarehouseConnection(config)

        mock_create_engine.assert_called_once()
        call_args = mock_create_engine.call_args
        assert "postgresql+psycopg2://testuser:testpass@localhost:5432/testdb" in str(
            call_args[0][0]
        )
        assert call_args[1]["poolclass"] == QueuePool
        assert call_args[1]["pool_size"] == 5
        assert call_args[1]["max_overflow"] == 10

    @patch("market_data.warehouse.connection.create_engine")
    def test_init_redshift_creates_null_pool(self, mock_create_engine):
        """Test Redshift uses NullPool"""
        config = {
            "type": "redshift",
            "host": "cluster.region.redshift.amazonaws.com",
            "port": 5439,
            "database": "testdb",
            "user": "testuser",
            "password": "testpass",
            "region": "us-east-1",
        }

        conn = WarehouseConnection(config)

        mock_create_engine.assert_called_once()
        call_args = mock_create_engine.call_args
        assert call_args[1]["poolclass"] == NullPool

    @patch("market_data.warehouse.connection.create_engine")
    def test_init_with_custom_pool_params(self, mock_create_engine):
        """Test custom pool parameters"""
        config = {
            "type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "database": "testdb",
            "user": "testuser",
            "password": "testpass",
            "pool_size": 10,
            "max_overflow": 20,
            "pool_timeout": 60,
        }

        conn = WarehouseConnection(config)

        call_args = mock_create_engine.call_args
        assert call_args[1]["pool_size"] == 10
        assert call_args[1]["max_overflow"] == 20
        assert call_args[1]["pool_timeout"] == 60

    @patch("market_data.warehouse.connection.create_engine")
    def test_get_connection_context_manager(self, mock_create_engine):
        """Test get_connection returns working context manager"""
        mock_engine = MagicMock()
        mock_connection = MagicMock()
        mock_create_engine.return_value = mock_engine
        mock_engine.begin.return_value.__enter__.return_value = mock_connection

        config = {
            "type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "database": "testdb",
            "user": "testuser",
            "password": "testpass",
        }

        conn = WarehouseConnection(config)

        with conn.get_connection() as connection:
            assert connection == mock_connection

        mock_engine.begin.assert_called_once()

    @patch("market_data.warehouse.connection.create_engine")
    def test_get_connection_commits_on_success(self, mock_create_engine):
        """Test connection commits on successful completion"""
        mock_engine = MagicMock()
        mock_connection = MagicMock()
        mock_create_engine.return_value = mock_engine
        mock_engine.begin.return_value.__enter__.return_value = mock_connection

        config = {
            "type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "database": "testdb",
            "user": "testuser",
            "password": "testpass",
        }

        conn = WarehouseConnection(config)

        with conn.get_connection() as connection:
            connection.execute("SELECT 1")

        # Verify begin was called (which handles commit/rollback)
        mock_engine.begin.assert_called_once()

    @patch("market_data.warehouse.connection.create_engine")
    def test_get_connection_rollbacks_on_error(self, mock_create_engine):
        """Test connection rolls back on error"""
        mock_engine = MagicMock()
        mock_connection = MagicMock()
        mock_create_engine.return_value = mock_engine
        mock_engine.begin.return_value.__enter__.return_value = mock_connection
        mock_engine.begin.return_value.__exit__.return_value = False

        config = {
            "type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "database": "testdb",
            "user": "testuser",
            "password": "testpass",
        }

        conn = WarehouseConnection(config)

        with pytest.raises(Exception):
            with conn.get_connection() as connection:
                raise Exception("Test error")

        # Verify begin was called (which handles rollback)
        mock_engine.begin.assert_called_once()

    @patch("market_data.warehouse.connection.create_engine")
    def test_test_connection_success(self, mock_create_engine):
        """Test test_connection with successful connection"""
        mock_engine = MagicMock()
        mock_connection = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 1

        mock_create_engine.return_value = mock_engine
        mock_engine.connect.return_value.__enter__.return_value = mock_connection
        mock_connection.execute.return_value = mock_result

        config = {
            "type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "database": "testdb",
            "user": "testuser",
            "password": "testpass",
        }

        conn = WarehouseConnection(config)
        result = conn.test_connection()

        assert result is True
        mock_engine.connect.assert_called_once()

    @patch("market_data.warehouse.connection.create_engine")
    def test_test_connection_failure(self, mock_create_engine):
        """Test test_connection with failed connection"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        mock_engine.connect.side_effect = Exception("Connection failed")

        config = {
            "type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "database": "testdb",
            "user": "testuser",
            "password": "testpass",
        }

        conn = WarehouseConnection(config)
        result = conn.test_connection()

        assert result is False

    @patch("market_data.warehouse.connection.create_engine")
    def test_dispose_closes_engine(self, mock_create_engine):
        """Test dispose properly closes the engine"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        config = {
            "type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "database": "testdb",
            "user": "testuser",
            "password": "testpass",
        }

        conn = WarehouseConnection(config)
        conn.dispose()

        mock_engine.dispose.assert_called_once()

    @patch("market_data.warehouse.connection.create_engine")
    def test_repr_includes_config_details(self, mock_create_engine):
        """Test __repr__ includes configuration details"""
        config = {
            "type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "database": "testdb",
            "user": "testuser",
            "password": "testpass",
        }

        conn = WarehouseConnection(config)
        repr_str = repr(conn)

        assert "postgresql" in repr_str
        assert "localhost" in repr_str
        assert "testdb" in repr_str
        assert "testpass" not in repr_str  # Password should not be in repr

    @patch("market_data.warehouse.connection.create_engine")
    def test_connection_string_for_postgresql(self, mock_create_engine):
        """Test connection string generation for PostgreSQL"""
        config = {
            "type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "database": "testdb",
            "user": "testuser",
            "password": "testpass",
        }

        conn = WarehouseConnection(config)

        call_args = mock_create_engine.call_args
        conn_string = str(call_args[0][0])
        assert "postgresql+psycopg2://" in conn_string
        assert "testuser" in conn_string
        assert "testpass" in conn_string
        assert "localhost" in conn_string
        assert "5432" in conn_string
        assert "testdb" in conn_string

    @patch("market_data.warehouse.connection.create_engine")
    def test_connection_string_for_redshift(self, mock_create_engine):
        """Test connection string generation for Redshift"""
        config = {
            "type": "redshift",
            "host": "cluster.region.redshift.amazonaws.com",
            "port": 5439,
            "database": "testdb",
            "user": "testuser",
            "password": "testpass",
            "region": "us-east-1",
        }

        conn = WarehouseConnection(config)

        call_args = mock_create_engine.call_args
        conn_string = str(call_args[0][0])
        assert "redshift+redshift_connector://" in conn_string

