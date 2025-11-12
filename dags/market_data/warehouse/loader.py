"""
Warehouse Data Loader

Loads data from Parquet files to Data Warehouse (PostgreSQL/Redshift).
"""

from typing import Dict

import pandas as pd
from market_data.config.warehouse_config import (
    BATCH_SIZE,
    LOAD_STRATEGY,
    TABLE_MARKET_DATA,
    get_warehouse_config,
)
from market_data.storage import get_parquet_path, load_from_parquet
from market_data.utils import get_logger, log_execution
from market_data.warehouse.connection import get_warehouse_connection
from sqlalchemy import text

logger = get_logger(__name__)


class WarehouseLoader:
    """
    Loads market data from Parquet to Data Warehouse
    """

    def __init__(self):
        """Initialize warehouse loader"""
        self.config = get_warehouse_config()
        self.warehouse_type = self.config["type"]
        self.schema = self.config.get("schema", "public")
        self.connection = get_warehouse_connection()

        logger.set_context(warehouse_type=self.warehouse_type, schema=self.schema)

    @log_execution()
    def create_tables(self):
        """
        Create warehouse tables if they don't exist

        Creates:
        - fact_market_data: Main fact table with market data and indicators
        """
        logger.info("Creating warehouse tables if not exist")

        # Schema creation (PostgreSQL only, Redshift uses default schema)
        if self.warehouse_type == "postgresql":
            create_schema_sql = f"CREATE SCHEMA IF NOT EXISTS {self.schema}"
        else:
            create_schema_sql = None

        # Main fact table DDL
        if self.warehouse_type == "postgresql":
            create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {self.schema}.{TABLE_MARKET_DATA} (
                id SERIAL PRIMARY KEY,
                ticker VARCHAR(10) NOT NULL,
                date DATE NOT NULL,

                -- OHLCV Data
                open DECIMAL(18, 6),
                high DECIMAL(18, 6),
                low DECIMAL(18, 6),
                close DECIMAL(18, 6),
                volume BIGINT,

                -- Technical Indicators - Trend
                sma_7 DECIMAL(18, 6),
                sma_14 DECIMAL(18, 6),
                sma_20 DECIMAL(18, 6),
                ema_12 DECIMAL(18, 6),
                macd DECIMAL(18, 6),
                macd_signal DECIMAL(18, 6),
                macd_histogram DECIMAL(18, 6),

                -- Technical Indicators - Momentum
                rsi DECIMAL(18, 6),

                -- Technical Indicators - Volatility
                bb_upper DECIMAL(18, 6),
                bb_middle DECIMAL(18, 6),
                bb_lower DECIMAL(18, 6),
                volatility_20d DECIMAL(18, 6),

                -- Returns
                daily_return DECIMAL(18, 6),
                daily_return_pct DECIMAL(18, 6),

                -- Metadata
                currency VARCHAR(10),
                exchange VARCHAR(50),
                instrument_type VARCHAR(50),
                regular_market_price DECIMAL(18, 6),
                fifty_two_week_high DECIMAL(18, 6),
                fifty_two_week_low DECIMAL(18, 6),
                long_name VARCHAR(255),
                short_name VARCHAR(255),

                -- Audit fields
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                -- Unique constraint
                UNIQUE(ticker, date)
            )
            """

            # Create index
            create_index_sql = f"""
            CREATE INDEX IF NOT EXISTS idx_{TABLE_MARKET_DATA}_ticker_date
            ON {self.schema}.{TABLE_MARKET_DATA}(ticker, date DESC)
            """

        else:  # Redshift
            # Redshift-specific DDL with distribution and sort keys
            create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {self.schema}.{TABLE_MARKET_DATA} (
                id BIGINT IDENTITY(1,1) PRIMARY KEY,
                ticker VARCHAR(10) NOT NULL,
                date DATE NOT NULL,

                -- OHLCV Data
                open DECIMAL(18, 6),
                high DECIMAL(18, 6),
                low DECIMAL(18, 6),
                close DECIMAL(18, 6),
                volume BIGINT,

                -- Technical Indicators - Trend
                sma_7 DECIMAL(18, 6),
                sma_14 DECIMAL(18, 6),
                sma_20 DECIMAL(18, 6),
                ema_12 DECIMAL(18, 6),
                macd DECIMAL(18, 6),
                macd_signal DECIMAL(18, 6),
                macd_histogram DECIMAL(18, 6),

                -- Technical Indicators - Momentum
                rsi DECIMAL(18, 6),

                -- Technical Indicators - Volatility
                bb_upper DECIMAL(18, 6),
                bb_middle DECIMAL(18, 6),
                bb_lower DECIMAL(18, 6),
                volatility_20d DECIMAL(18, 6),

                -- Returns
                daily_return DECIMAL(18, 6),
                daily_return_pct DECIMAL(18, 6),

                -- Metadata
                currency VARCHAR(10),
                exchange VARCHAR(50),
                instrument_type VARCHAR(50),
                regular_market_price DECIMAL(18, 6),
                fifty_two_week_high DECIMAL(18, 6),
                fifty_two_week_low DECIMAL(18, 6),
                long_name VARCHAR(255),
                short_name VARCHAR(255),

                -- Audit fields
                created_at TIMESTAMP DEFAULT SYSDATE,
                updated_at TIMESTAMP DEFAULT SYSDATE,

                -- Unique constraint
                UNIQUE(ticker, date)
            )
            DISTKEY(ticker)
            SORTKEY(ticker, date)
            """

            create_index_sql = None  # Redshift doesn't use traditional indexes

        # Execute DDL
        with self.connection.get_connection() as conn:
            if create_schema_sql:
                logger.info(f"Creating schema: {self.schema}")
                conn.execute(text(create_schema_sql))

            logger.info(f"Creating table: {self.schema}.{TABLE_MARKET_DATA}")
            conn.execute(text(create_table_sql))

            if create_index_sql:
                logger.info(f"Creating index on {TABLE_MARKET_DATA}")
                conn.execute(text(create_index_sql))

        logger.audit(
            "warehouse_tables_created",
            {
                "warehouse_type": self.warehouse_type,
                "schema": self.schema,
                "table": TABLE_MARKET_DATA,
            },
        )

        logger.info("✅ Warehouse tables created successfully")

    @log_execution()
    def load_from_parquet(self, ticker: str) -> int:
        """
        Load data from Parquet file to warehouse

        Process:
        1. Read Parquet file
        2. Load into Pandas DataFrame
        3. Generate SQL INSERT/UPSERT statements
        4. Execute in batches

        Args:
            ticker: Stock ticker symbol

        Returns:
            Number of records loaded
        """
        logger.set_context(ticker=ticker, load_strategy=LOAD_STRATEGY)

        # Step 1: Read Parquet
        logger.info(f"Reading Parquet file for {ticker}")
        parquet_path = get_parquet_path(ticker)

        try:
            df = load_from_parquet(ticker)
        except FileNotFoundError:
            logger.warning(
                f"No Parquet file found for {ticker}",
                extra={"ticker": ticker, "path": parquet_path},
            )
            return 0

        logger.info(
            f"Loaded {len(df)} records from Parquet",
            extra={"ticker": ticker, "records": len(df), "columns": len(df.columns)},
        )

        # Step 2: Data preparation
        df_clean = self._prepare_dataframe(df)

        logger.info(
            f"Data prepared: {len(df_clean)} valid records (filtered from {len(df)})",
            extra={
                "ticker": ticker,
                "total_records": len(df),
                "valid_records": len(df_clean),
                "filtered": len(df) - len(df_clean),
            },
        )

        if len(df_clean) == 0:
            logger.warning(f"No valid records to load for {ticker}")
            return 0

        # Step 3: Load to warehouse
        records_loaded = self._load_dataframe(df_clean, ticker)

        logger.metric(
            "warehouse.records_loaded",
            records_loaded,
            {"ticker": ticker, "warehouse_type": self.warehouse_type},
        )

        logger.audit(
            "parquet_loaded_to_warehouse",
            {
                "ticker": ticker,
                "records": records_loaded,
                "warehouse_type": self.warehouse_type,
            },
        )

        logger.clear_context()
        return records_loaded

    def _prepare_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare DataFrame for warehouse loading

        - Filter out records with null close prices
        - Ensure date column is datetime
        - Handle NaN values
        - Select relevant columns
        - Exclude nested dict columns (quote, metadata)

        Args:
            df: Raw DataFrame from Parquet

        Returns:
            Cleaned DataFrame ready for warehouse
        """
        df_clean = df.copy()

        # Filter: Only records with valid close prices
        df_clean = df_clean[df_clean["close"].notna()].copy()

        logger.debug(
            f"Filtered records with valid close prices: {len(df_clean)}",
            extra={"valid_close": len(df_clean), "total": len(df)},
        )

        # Ensure date is datetime
        if "date" in df_clean.columns:
            df_clean["date"] = pd.to_datetime(df_clean["date"])

        # Exclude columns not in warehouse table schema
        # - quote, metadata: Nested dicts already expanded to individual columns
        # - timestamp, regular_market_time: Raw API timestamps (not needed in warehouse)
        columns_to_exclude = ["quote", "metadata", "timestamp", "regular_market_time"]
        columns_to_drop = [col for col in columns_to_exclude if col in df_clean.columns]
        if columns_to_drop:
            df_clean = df_clean.drop(columns=columns_to_drop)
            logger.debug(
                f"Dropped non-warehouse columns: {columns_to_drop}",
                extra={"dropped_columns": columns_to_drop},
            )

        # Replace NaN with None for SQL compatibility
        df_clean = df_clean.where(pd.notna(df_clean), None)

        return df_clean

    def _load_dataframe(self, df: pd.DataFrame, ticker: str) -> int:
        """
        Load DataFrame to warehouse using configured strategy

        Args:
            df: Prepared DataFrame
            ticker: Stock ticker

        Returns:
            Number of records loaded
        """
        if LOAD_STRATEGY == "append":
            return self._load_append(df, ticker)
        elif LOAD_STRATEGY == "upsert":
            return self._load_upsert(df, ticker)
        elif LOAD_STRATEGY == "truncate_insert":
            return self._load_truncate_insert(df, ticker)
        else:
            raise ValueError(f"Unknown load strategy: {LOAD_STRATEGY}")

    def _load_append(self, df: pd.DataFrame, ticker: str) -> int:
        """
        Load data using APPEND strategy (insert all records)

        Args:
            df: DataFrame to load
            ticker: Stock ticker

        Returns:
            Number of records inserted
        """
        logger.info(
            f"Loading {len(df)} records using APPEND strategy",
            extra={"ticker": ticker, "records": len(df)},
        )

        with self.connection.get_connection() as conn:
            # Use pandas to_sql with append mode
            df.to_sql(
                TABLE_MARKET_DATA,
                conn,
                schema=self.schema,
                if_exists="append",
                index=False,
                method="multi",
                chunksize=BATCH_SIZE,
            )

        logger.info(f"✅ Appended {len(df)} records to warehouse")
        return len(df)

    def _load_upsert(self, df: pd.DataFrame, ticker: str) -> int:
        """
        Load data using UPSERT strategy (insert or update on conflict)

        PostgreSQL: Uses ON CONFLICT DO UPDATE
        Redshift: Uses staging table + MERGE pattern

        Args:
            df: DataFrame to load
            ticker: Stock ticker

        Returns:
            Number of records upserted
        """
        logger.info(
            f"Loading {len(df)} records using UPSERT strategy",
            extra={"ticker": ticker, "records": len(df)},
        )

        if self.warehouse_type == "postgresql":
            return self._upsert_postgresql(df, ticker)
        else:  # Redshift
            return self._upsert_redshift(df, ticker)

    def _upsert_postgresql(self, df: pd.DataFrame, ticker: str) -> int:
        """UPSERT for PostgreSQL using ON CONFLICT"""
        # Generate column list
        columns = df.columns.tolist()
        columns_str = ", ".join(columns)
        placeholders = ", ".join([f":{col}" for col in columns])

        # Update clause for all columns except ticker and date
        update_columns = [col for col in columns if col not in ["ticker", "date"]]
        update_clause = ", ".join([f"{col} = EXCLUDED.{col}" for col in update_columns])

        # Add updated_at
        update_clause += ", updated_at = CURRENT_TIMESTAMP"

        # Build UPSERT query
        upsert_sql = f"""
        INSERT INTO {self.schema}.{TABLE_MARKET_DATA} ({columns_str})
        VALUES ({placeholders})
        ON CONFLICT (ticker, date)
        DO UPDATE SET {update_clause}
        """

        records_loaded = 0

        with self.connection.get_connection() as conn:
            # Execute in batches
            for i in range(0, len(df), BATCH_SIZE):
                batch = df.iloc[i : i + BATCH_SIZE]  # noqa: E203

                logger.debug(
                    f"Upserting batch {i // BATCH_SIZE + 1}/{(len(df) - 1) // BATCH_SIZE + 1}",
                    extra={"batch_size": len(batch), "start": i},
                )

                # Convert batch to list of dicts
                records = batch.to_dict("records")

                # Execute upsert for each record
                for record in records:
                    conn.execute(text(upsert_sql), record)
                    records_loaded += 1

        logger.info(
            f"✅ Upserted {records_loaded} records to PostgreSQL",
            extra={"ticker": ticker, "records": records_loaded},
        )

        return records_loaded

    def _upsert_redshift(self, df: pd.DataFrame, ticker: str) -> int:
        """
        UPSERT for Redshift using staging table + MERGE pattern

        Redshift doesn't support ON CONFLICT, so we:
        1. Create temp staging table
        2. Load data to staging
        3. DELETE existing records
        4. INSERT from staging
        5. Drop staging
        """
        staging_table = f"{TABLE_MARKET_DATA}_staging_{ticker.lower()}"

        logger.info(
            f"Using Redshift MERGE pattern with staging table: {staging_table}",
            extra={"ticker": ticker, "staging_table": staging_table},
        )

        with self.connection.get_connection() as conn:
            # Step 1: Create staging table (temp)
            create_staging_sql = f"""
            CREATE TEMP TABLE {staging_table} (LIKE {self.schema}.{TABLE_MARKET_DATA})
            """
            conn.execute(text(create_staging_sql))
            logger.debug(f"Created staging table: {staging_table}")

            # Step 2: Load data to staging using pandas
            df.to_sql(
                staging_table,
                conn,
                if_exists="append",
                index=False,
                method="multi",
                chunksize=BATCH_SIZE,
            )
            logger.debug(f"Loaded {len(df)} records to staging table")

            # Step 3 & 4: DELETE + INSERT (MERGE pattern)
            merge_sql = f"""
            BEGIN TRANSACTION;

            -- Delete existing records
            DELETE FROM {self.schema}.{TABLE_MARKET_DATA}
            WHERE ticker = '{ticker}'
            AND date IN (SELECT date FROM {staging_table});

            -- Insert from staging
            INSERT INTO {self.schema}.{TABLE_MARKET_DATA}
            SELECT * FROM {staging_table};

            END TRANSACTION;
            """

            conn.execute(text(merge_sql))
            logger.debug("Executed MERGE pattern (DELETE + INSERT)")

            # Step 5: Drop staging (automatic on session end for TEMP table)

        logger.info(
            f"✅ Upserted {len(df)} records to Redshift",
            extra={"ticker": ticker, "records": len(df)},
        )

        return len(df)

    def _load_truncate_insert(self, df: pd.DataFrame, ticker: str) -> int:
        """
        Load data using TRUNCATE + INSERT strategy

        WARNING: Deletes ALL existing data for ticker before insert

        Args:
            df: DataFrame to load
            ticker: Stock ticker

        Returns:
            Number of records inserted
        """
        logger.warning(
            f"Using TRUNCATE+INSERT strategy - will delete all existing data for {ticker}",
            extra={"ticker": ticker, "records_to_delete": "ALL"},
        )

        with self.connection.get_connection() as conn:
            # Delete existing records for ticker
            delete_sql = f"""
            DELETE FROM {self.schema}.{TABLE_MARKET_DATA}
            WHERE ticker = :ticker
            """
            result = conn.execute(text(delete_sql), {"ticker": ticker})
            deleted_count = result.rowcount

            logger.info(
                f"Deleted {deleted_count} existing records for {ticker}",
                extra={"ticker": ticker, "deleted": deleted_count},
            )

            # Insert new records
            df.to_sql(
                TABLE_MARKET_DATA,
                conn,
                schema=self.schema,
                if_exists="append",
                index=False,
                method="multi",
                chunksize=BATCH_SIZE,
            )

        logger.info(
            f"✅ Loaded {len(df)} records using TRUNCATE+INSERT",
            extra={"ticker": ticker, "records": len(df)},
        )

        return len(df)

    def close(self):
        """Close warehouse connection"""
        if self.connection:
            self.connection.close()


@log_execution()
def load_parquet_to_warehouse(ticker: str, **context) -> Dict[str, any]:
    """
    Operator function to load Parquet data to warehouse

    Workflow:
    1. Read Parquet file
    2. Load to Pandas DataFrame
    3. Create warehouse tables if needed
    4. Load data using configured strategy (upsert/append/truncate)

    Args:
        ticker: Stock ticker symbol
        context: Airflow context

    Returns:
        Summary dictionary with load statistics
    """
    logger.set_context(
        task_id=context["task_instance"].task_id,
        ticker=ticker,
        execution_date=str(context["execution_date"]),
    )

    logger.info(
        f"Starting warehouse load for {ticker}",
        extra={"ticker": ticker, "load_strategy": LOAD_STRATEGY},
    )

    # Initialize loader
    loader = WarehouseLoader()

    try:
        # Create tables if not exist
        logger.info("Ensuring warehouse tables exist")
        loader.create_tables()

        # Load data
        logger.info(f"Loading Parquet data for {ticker} to warehouse")
        records_loaded = loader.load_from_parquet(ticker)

        # Get warehouse stats
        with loader.connection.get_connection() as conn:
            count_sql = f"""
            SELECT COUNT(*)
            FROM {loader.schema}.{TABLE_MARKET_DATA}
            WHERE ticker = :ticker
            """
            total_records = conn.execute(text(count_sql), {"ticker": ticker}).scalar()

            min_date_sql = f"""
            SELECT MIN(date)
            FROM {loader.schema}.{TABLE_MARKET_DATA}
            WHERE ticker = :ticker
            """
            min_date = conn.execute(text(min_date_sql), {"ticker": ticker}).scalar()

            max_date_sql = f"""
            SELECT MAX(date)
            FROM {loader.schema}.{TABLE_MARKET_DATA}
            WHERE ticker = :ticker
            """
            max_date = conn.execute(text(max_date_sql), {"ticker": ticker}).scalar()

        summary = {
            "ticker": ticker,
            "records_loaded": records_loaded,
            "total_in_warehouse": total_records,
            "date_range": {
                "min": str(min_date) if min_date else None,
                "max": str(max_date) if max_date else None,
            },
            "load_strategy": LOAD_STRATEGY,
            "warehouse_type": loader.warehouse_type,
        }

        logger.info(
            f"✅ Warehouse load complete for {ticker}",
            extra={
                "ticker": ticker,
                "records_loaded": records_loaded,
                "total_in_warehouse": total_records,
                "date_range": f"{min_date} to {max_date}",
            },
        )

        logger.metric(
            "warehouse.load.complete",
            records_loaded,
            {"ticker": ticker, "warehouse_type": loader.warehouse_type},
        )

        # Push summary to XCom
        context["task_instance"].xcom_push(key="warehouse_summary", value=summary)

        logger.clear_context()
        return summary

    except Exception as e:
        logger.error(
            f"Failed to load data to warehouse: {e}",
            extra={"ticker": ticker, "error": str(e)},
            exc_info=True,
        )
        raise
    finally:
        loader.close()
