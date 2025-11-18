"""
Unit tests for warehouse connection management
"""

from unittest.mock import MagicMock, patch

import pytest
from market_data.warehouse.connection import (WarehouseConnection,
                                              get_warehouse_connection)


class TestGetWarehouseConnection:
    """Test get_warehouse_connection factory function"""

    @patch("market_data.warehouse.connection.get_warehouse_config")
    def test_returns_warehouse_connection_instance(self, mock_get_config):
        """Test factory function returns WarehouseConnection instance"""
        mock_get_config.return_value = {
            "type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "database": "testdb",
            "user": "testuser",
            "password": "testpass",
            "schema": "public",
        }

        conn = get_warehouse_connection()

        assert isinstance(conn, WarehouseConnection)
        assert conn.warehouse_type == "postgresql"


class TestWarehouseConnection:
    """Test WarehouseConnection class"""

    @patch("market_data.warehouse.connection.get_warehouse_config")
    def test_init_stores_config(self, mock_get_config):
        """Test initialization stores configuration"""
        mock_config = {
            "type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "database": "testdb",
            "user": "testuser",
            "password": "testpass",
            "schema": "public",
        }
        mock_get_config.return_value = mock_config

        conn = WarehouseConnection()

        assert conn.config == mock_config
        assert conn.warehouse_type == "postgresql"

    @patch("market_data.warehouse.connection.get_warehouse_config")
    @patch("market_data.warehouse.connection.get_connection_string")
    @patch("market_data.warehouse.connection.create_engine")
    def test_create_engine_for_postgresql(
        self, mock_create_engine, mock_get_conn_string, mock_get_config
    ):
        """Test create_engine for PostgreSQL"""
        mock_get_config.return_value = {
            "type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "database": "testdb",
            "user": "testuser",
            "password": "testpass",
            "schema": "public",
        }
        mock_get_conn_string.return_value = (
            "postgresql://testuser:testpass@localhost:5432/testdb"
        )

        mock_engine = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value.execute.return_value.scalar.return_value = (
            1
        )
        mock_create_engine.return_value = mock_engine

        conn = WarehouseConnection()
        engine = conn.create_engine()

        assert engine == mock_engine
        assert mock_create_engine.called

    @patch("market_data.warehouse.connection.get_warehouse_config")
    def test_get_connection_context_manager(self, mock_get_config):
        """Test get_connection returns working context manager"""
        mock_get_config.return_value = {
            "type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "database": "testdb",
            "user": "testuser",
            "password": "testpass",
            "schema": "public",
        }

        conn = WarehouseConnection()
        mock_engine = MagicMock()
        mock_connection = MagicMock()
        conn.engine = mock_engine
        mock_engine.begin.return_value.__enter__.return_value = mock_connection

        with conn.get_connection() as connection:
            assert connection == mock_connection

        mock_engine.begin.assert_called_once()

    @patch("market_data.warehouse.connection.get_warehouse_config")
    def test_close_disposes_engine(self, mock_get_config):
        """Test close properly disposes the engine"""
        mock_get_config.return_value = {
            "type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "database": "testdb",
            "user": "testuser",
            "password": "testpass",
            "schema": "public",
        }

        conn = WarehouseConnection()
        mock_engine = MagicMock()
        conn.engine = mock_engine

        conn.close()

        mock_engine.dispose.assert_called_once()
