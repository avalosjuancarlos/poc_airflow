-- ============================================================================
-- Data Warehouse Initialization for Development Environment
-- ============================================================================
--
-- This script initializes the dedicated PostgreSQL warehouse database
-- for development environment.
--
-- Database: market_data_warehouse (created automatically by POSTGRES_DB env var)
-- User: warehouse_user (created automatically by POSTGRES_USER env var)
--
-- Runs automatically when PostgreSQL container starts for the first time
-- via docker-entrypoint-initdb.d/
--
-- Tables will be created automatically by the DAG on first execution.
-- ============================================================================

-- Enable extensions if needed
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE '============================================================';
    RAISE NOTICE '✅ Market Data Warehouse Database Initialized';
    RAISE NOTICE '============================================================';
    RAISE NOTICE 'Database: market_data_warehouse';
    RAISE NOTICE 'User: warehouse_user';
    RAISE NOTICE 'Schema: public (default)';
    RAISE NOTICE '';
    RAISE NOTICE 'Tables will be created automatically by DAG on first run:';
    RAISE NOTICE '  - fact_market_data';
    RAISE NOTICE '';
    RAISE NOTICE 'Ready for ETL pipeline! 🚀';
    RAISE NOTICE '============================================================';
END $$;

