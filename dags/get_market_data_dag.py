"""
Market Data DAG - Yahoo Finance API

This DAG fetches historical price data for one or more tickers
using the Yahoo Finance public API.

Modular structure:
- market_data.config: Configuration and settings
- market_data.utils: Utilities (API client, validators)
- market_data.operators: Task functions
- market_data.sensors: Custom sensors
"""

import json
import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.sensors.python import PythonSensor

# Import from modular structure
from market_data.config import (
    DEFAULT_TICKERS,
    SENSOR_EXPONENTIAL_BACKOFF,
    SENSOR_POKE_INTERVAL,
    SENSOR_TIMEOUT,
    log_configuration,
)
# Resolve default tickers for DAG params (reflects env configuration literally)
_raw_env_tickers = os.environ.get("MARKET_DATA_DEFAULT_TICKERS")
if _raw_env_tickers:
    _raw_env_tickers = _raw_env_tickers.strip()
    if _raw_env_tickers.startswith("[") and _raw_env_tickers.endswith("]"):
        try:
            _tickers_param_default = json.dumps(json.loads(_raw_env_tickers))
        except json.JSONDecodeError:
            _tickers_param_default = json.dumps(DEFAULT_TICKERS)
    else:
        tokens = [token.strip() for token in _raw_env_tickers.split(",") if token.strip()]
        _tickers_param_default = json.dumps(tokens or DEFAULT_TICKERS)
else:
    _tickers_param_default = json.dumps(DEFAULT_TICKERS)
from market_data.operators import (
    fetch_market_data,
    process_market_data,
    validate_ticker,
)
from market_data.operators.transform_operators import (
    check_and_determine_dates,
    fetch_multiple_dates,
    transform_and_save,
)
from market_data.operators.warehouse_operators import load_to_warehouse
from market_data.sensors import check_api_availability

# Log configuration on DAG load (skip in test mode)
if not os.environ.get("AIRFLOW__CORE__UNIT_TEST_MODE"):
    log_configuration()

# ============================================================================
# DAG Definition
# ============================================================================

# Default arguments
default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2025, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
    "execution_timeout": timedelta(minutes=10),
}

# Define DAG
with DAG(
    dag_id="get_market_data",
    default_args=default_args,
    description="ETL Pipeline: Yahoo Finance → Indicadores Técnicos → Parquet → Data Warehouse",
    schedule_interval="0 23 * * 1-5",  # 6:00 PM ET (23:00 UTC) Monday-Friday
    catchup=False,
    tags=[
        "finance",
        "market-data",
        "yahoo-finance",
        "api",
        "etl",
        "parquet",
        "warehouse",
    ],
    params={
        # Airflow UI treats params as strings; keep JSON string so the default shows as an array.
        "tickers": _tickers_param_default,
        "date": datetime.now().strftime("%Y-%m-%d"),
    },
    doc_md="""
    # Get Market Data DAG - ETL Pipeline
    
    Pipeline ETL completo que extrae, transforma y carga datos de mercado a un Data Warehouse.
    
    ## 🎯 Funcionalidad
    
    ### Ejecución Diaria (Schedule: 6:00 PM ET / 23:00 UTC)
    - **Horario**: 6:00 PM Eastern Time (post-cierre del mercado)
    - **Días**: Lunes a Viernes (días laborables)
    - **Timezone**: UTC 23:00 (ajustado a cierre del mercado US)
    - Obtiene datos del día actual desde Yahoo Finance API
    - Calcula 12 indicadores técnicos
    - Almacena en Parquet (persistencia local)
    - Carga a Data Warehouse (PostgreSQL dev / Redshift prod)
    
    ### Backfill Automático (Primera Ejecución)
    - Si no existe archivo Parquet → Backfill de 20 días
    - Si existe archivo Parquet → Solo día actual
    
    ## 📊 Indicadores Técnicos Calculados (12)
    
    - **Trend**: SMA (7, 14, 20), EMA, MACD (line, signal, histogram)
    - **Momentum**: RSI (14 días)
    - **Volatility**: Bollinger Bands, Volatility 20d
    - **Returns**: Daily return %
    
    ## 💾 Almacenamiento Multi-Capa
    
    ### Layer 1: Parquet (Local Cache)
    - **Formato**: Apache Parquet (compresión Snappy)
    - **Ubicación**: `/opt/airflow/data/{TICKER}_market_data.parquet`
    - **Uso**: Cache local, recovery, análisis local
    
    ### Layer 2: Data Warehouse
    - **Development**: PostgreSQL (mismo servidor, schema separado)
    - **Staging/Production**: Amazon Redshift (cluster dedicado)
    - **Estrategia**: UPSERT (inserta nuevos, actualiza existentes)
    - **Schema**: fact_market_data con 25+ columnas
    
    ## 🔄 Flujo de Ejecución (6 Tareas)
    
    1. **Validate Ticker**: Valida formato del ticker symbol
    2. **Determine Dates**: Decide backfill (20 días) o incremental (1 día)
    3. **Check API Availability**: Sensor verifica disponibilidad de API
    4. **Fetch Multiple Dates**: Obtiene datos de Yahoo Finance (1-20 fechas)
    5. **Transform & Save**: Calcula indicadores y guarda en Parquet
    6. **Load to Warehouse**: Carga desde Parquet a PostgreSQL/Redshift
    
    ## 🌍 Ambientes
    
    - **Development**: PostgreSQL en Docker (postgres:5432)
    - **Staging**: Redshift cluster staging
    - **Production**: Redshift cluster production
    
    Configurado via variable `ENVIRONMENT` (development/staging/production)
    
    ## 🎛️ Parámetros
    
    ```json
    {
        "tickers": ["AAPL", "MSFT", "NVDA"]
    }
    ```
    
    ## ⚙️ Variables de Entorno Principales
    
    - `ENVIRONMENT`: development | staging | production
    - `MARKET_DATA_DEFAULT_TICKERS`: Lista de tickers por defecto (JSON/CSV)
    - `MARKET_DATA_STORAGE_DIR`: Directorio Parquet (default: /opt/airflow/data)
    - `WAREHOUSE_LOAD_STRATEGY`: upsert | append | truncate_insert
    - `DEV_WAREHOUSE_HOST`: Host PostgreSQL (development)
    - `PROD_WAREHOUSE_HOST`: Host Redshift (production)
    
    ## 📖 Documentación
    
    Ver `docs/user-guide/market-data-dag.md` para guía completa.
    """,
) as dag:

    # Task 1: Validate ticker
    validate_ticker_task = PythonOperator(
        task_id="validate_ticker",
        python_callable=validate_ticker,
        provide_context=True,
    )

    # Task 2: Check if parquet exists and determine dates to fetch
    determine_dates_task = PythonOperator(
        task_id="determine_dates",
        python_callable=check_and_determine_dates,
        provide_context=True,
    )

    # Task 3: Sensor - Check API availability
    api_sensor = PythonSensor(
        task_id="check_api_availability",
        python_callable=check_api_availability,
        poke_interval=SENSOR_POKE_INTERVAL,
        timeout=SENSOR_TIMEOUT,
        mode="poke",
        exponential_backoff=SENSOR_EXPONENTIAL_BACKOFF,
    )

    # Task 4: Fetch market data for all determined dates
    fetch_data_task = PythonOperator(
        task_id="fetch_multiple_dates",
        python_callable=fetch_multiple_dates,
        provide_context=True,
        execution_timeout=timedelta(minutes=15),  # Longer timeout for backfill
    )

    # Task 5: Transform data (calculate indicators) and save to Parquet
    transform_and_save_task = PythonOperator(
        task_id="transform_and_save",
        python_callable=transform_and_save,
        provide_context=True,
    )

    # Task 6: Load data to Data Warehouse (PostgreSQL dev / Redshift prod)
    load_warehouse_task = PythonOperator(
        task_id="load_to_warehouse",
        python_callable=load_to_warehouse,
        provide_context=True,
    )

    # Define task dependencies
    # validate → determine dates → check API → fetch data → transform & save → load warehouse
    (
        validate_ticker_task
        >> determine_dates_task
        >> api_sensor
        >> fetch_data_task
        >> transform_and_save_task
        >> load_warehouse_task
    )
