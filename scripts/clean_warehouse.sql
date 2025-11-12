-- Clean up warehouse database after failed table creation
-- Run this script to reset the warehouse schema

\c market_data_warehouse

-- Drop the corrupted sequence and table
DROP SEQUENCE IF EXISTS fact_market_data_id_seq CASCADE;
DROP TABLE IF EXISTS public.fact_market_data CASCADE;

-- Verify cleanup
SELECT 'Warehouse cleaned successfully!' AS status;

