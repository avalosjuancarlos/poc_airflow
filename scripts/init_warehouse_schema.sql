-- ============================================================================
-- Data Warehouse Schema Initialization for Development Environment
-- ============================================================================
--
-- This script creates the market_data_warehouse schema in PostgreSQL
-- for development environment.
--
-- Runs automatically when PostgreSQL container starts for the first time
-- via docker-entrypoint-initdb.d/
--
-- ============================================================================

-- Create warehouse schema (separate from Airflow metadata)
CREATE SCHEMA IF NOT EXISTS market_data_warehouse;

-- Grant permissions to airflow user
GRANT ALL PRIVILEGES ON SCHEMA market_data_warehouse TO airflow;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA market_data_warehouse TO airflow;
ALTER DEFAULT PRIVILEGES IN SCHEMA market_data_warehouse GRANT ALL ON TABLES TO airflow;

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE '✅ Schema market_data_warehouse created successfully';
    RAISE NOTICE 'Warehouse tables will be created automatically by DAG on first run';
END $$;

