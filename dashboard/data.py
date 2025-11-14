from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text

from config import get_database_config


@st.cache_resource
def get_engine():
    config = get_database_config()
    if config["type"] == "postgresql":
        conn = (
            f"postgresql://{config['user']}:{config['password']}@"
            f"{config['host']}:{config['port']}/{config['database']}"
        )
    else:
        conn = (
            f"redshift+psycopg2://{config['user']}:{config['password']}@"
            f"{config['host']}:{config['port']}/{config['database']}"
        )
    return create_engine(conn)


@st.cache_data(ttl=300)
def load_available_tickers() -> List[str]:
    engine = get_engine()
    query = """
    SELECT DISTINCT ticker
    FROM fact_market_data
    ORDER BY ticker
    """
    try:
        with engine.connect() as conn:
            df = pd.read_sql(text(query), conn)
            return df["ticker"].tolist()
    except Exception as e:
        msg = str(e)
        if "UndefinedTable" in msg or "does not exist" in msg:
            st.info(
                "Warehouse table `fact_market_data` not found yet. "
                "Trigger the market data DAG to populate data."
            )
        else:
            st.warning(f"Unable to load tickers from warehouse: {e}")
        return []


@st.cache_data(ttl=300)
def load_market_data(ticker: str, days: int = 90) -> pd.DataFrame:
    engine = get_engine()
    query = """
    SELECT
        date,
        open,
        high,
        low,
        close,
        volume,
        sma_7,
        sma_14,
        sma_20,
        rsi,
        macd,
        macd_signal,
        macd_histogram,
        bb_upper,
        bb_middle,
        bb_lower,
        daily_return,
        volatility_20d,
        created_at,
        updated_at
    FROM fact_market_data
    WHERE ticker = :ticker
        AND date >= CURRENT_DATE - :days * INTERVAL '1 day'
    ORDER BY date DESC
    """
    try:
        with engine.connect() as conn:
            df = pd.read_sql(
                text(query), conn, params={"ticker": ticker, "days": str(days)}
            )
            df["date"] = pd.to_datetime(df["date"])
            return df.sort_values("date")
    except Exception as e:
        st.error(f"Error loading data for {ticker}: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300)
def load_summary_stats(ticker: str) -> Dict:
    engine = get_engine()
    query = """
    SELECT
        COUNT(*) as total_records,
        MIN(date) as first_date,
        MAX(date) as last_date,
        AVG(close) as avg_close,
        MIN(close) as min_close,
        MAX(close) as max_close,
        AVG(volume) as avg_volume,
        AVG(volatility_20d) FILTER (WHERE volatility_20d IS NOT NULL AND volatility_20d != 'NaN') as avg_volatility,
        COUNT(*) FILTER (WHERE volatility_20d IS NOT NULL AND volatility_20d != 'NaN') as volatility_count
    FROM fact_market_data
    WHERE ticker = :ticker
    """
    try:
        with engine.connect() as conn:
            df = pd.read_sql(text(query), conn, params={"ticker": ticker})
            return df.iloc[0].to_dict() if not df.empty else {}
    except Exception as e:
        st.error(f"Error loading summary for {ticker}: {e}")
        return {}


@st.cache_data(ttl=600)
def load_warehouse_tables() -> List[Dict]:
    engine = get_engine()
    query = """
    SELECT table_schema, table_name
    FROM information_schema.tables
    WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
    ORDER BY table_schema, table_name
    """
    try:
        with engine.connect() as conn:
            df = pd.read_sql(text(query), conn)
            return df.to_dict("records")
    except Exception as e:
        st.error(f"Error loading warehouse tables: {e}")
        return []


@st.cache_data(ttl=600)
def load_table_columns(schema: str, table: str) -> List[Dict]:
    engine = get_engine()
    query = """
    SELECT
        column_name,
        data_type,
        is_nullable,
        ordinal_position
    FROM information_schema.columns
    WHERE table_schema = :schema
        AND table_name = :table
    ORDER BY ordinal_position
    """
    try:
        with engine.connect() as conn:
            df = pd.read_sql(text(query), conn, params={"schema": schema, "table": table})
            return df.to_dict("records")
    except Exception as e:
        st.error(f"Error loading columns for {schema}.{table}: {e}")
        return []


@st.cache_data(ttl=600)
def load_distinct_values(schema: str, table: str, column: str, limit: int = 50):
    engine = get_engine()
    query = f'''
    SELECT DISTINCT "{column}" AS value
    FROM "{schema}"."{table}"
    WHERE "{column}" IS NOT NULL
    ORDER BY value
    LIMIT :limit
    '''
    try:
        with engine.connect() as conn:
            df = pd.read_sql(text(query), conn, params={"limit": limit})
            return df["value"].dropna().tolist()
    except Exception as e:
        st.warning(f"Unable to load distinct values for {column}: {e}")
        return []


def build_warehouse_query(
    schema: str,
    table: str,
    columns: List[Dict],
    ticker_column: Optional[str],
    date_column: Optional[str],
    ticker_filter: List[str],
    date_range,
    custom_filter: str,
    limit_rows: int,
):
    qualified_table = f'"{schema}"."{table}"'
    where_clauses = []
    params: Dict[str, str | int | datetime] = {}

    def quote_identifier(identifier):
        return f'"{identifier}"'

    if ticker_filter:
        column_name = ticker_column or "ticker"
        ticker_params = []
        for idx, ticker in enumerate(ticker_filter):
            param_name = f"ticker_{idx}"
            ticker_params.append(f":{param_name}")
            params[param_name] = ticker
        where_clauses.append(
            f"{quote_identifier(column_name)} IN ({', '.join(ticker_params)})"
        )

    if date_range and len(date_range) == 2 and all(date_range) and date_column:
        column_name = quote_identifier(date_column)
        params["start_date"] = date_range[0]
        params["end_date"] = date_range[1]
        where_clauses.append(f"{column_name} BETWEEN :start_date AND :end_date")

    if custom_filter and custom_filter.strip():
        where_clauses.append(custom_filter.strip())

    query = f"SELECT *\nFROM {qualified_table}"
    if where_clauses:
        query += "\nWHERE " + "\n  AND ".join(where_clauses)

    column_names = [col["column_name"] for col in columns] if columns else []
    order_column = date_column or (column_names[0] if column_names else None)
    if order_column:
        query += f'\nORDER BY "{order_column}" DESC'
    query += "\nLIMIT :limit_rows"

    params["limit_rows"] = limit_rows
    return query, params


def run_warehouse_query(query: str, params: Dict):
    normalized = query.strip().lower()
    if not normalized.startswith("select"):
        raise ValueError("Only SELECT statements are permitted in Warehouse Explorer.")

    engine = get_engine()
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn, params=params)

    for column in df.columns:
        lower_col = column.lower()
        if any(suffix in lower_col for suffix in ("date", "_at")):
            try:
                df[column] = pd.to_datetime(df[column], errors="ignore")
            except Exception:
                continue
    return df

