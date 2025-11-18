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
def _parse_ticker_sequence(raw_value):
    """Parse comma-separated or JSON list into a list of tickers."""
    if raw_value is None:
        return []

    if isinstance(raw_value, (list, tuple, set)):
        candidates = list(raw_value)
    else:
        text = str(raw_value).strip().strip("'").strip('"')
        if not text:
            return []

        if text.startswith("[") and text.endswith("]"):
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, list):
                candidates = parsed
            else:
                candidates = [text]
        elif "," in text:
            candidates = text.split(",")
        else:
            candidates = [text]

    normalized = []
    for candidate in candidates:
        if candidate is None:
            continue
        ticker = str(candidate).strip().strip("'").strip('"').upper()
        if ticker and ticker not in normalized:
            normalized.append(ticker)
    return normalized


def _tickers_param_default():
    """Default ticker list displayed in the Airflow UI."""
    env_tickers = _parse_ticker_sequence(os.environ.get("MARKET_DATA_DEFAULT_TICKERS"))
    if env_tickers:
        return env_tickers
    return list(DEFAULT_TICKERS)


_TICKERS_PARAM_DEFAULT = _tickers_param_default()
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
        "tickers": _TICKERS_PARAM_DEFAULT,
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
    - Si no existe archivo Parquet → Backfill de **120 días** (~6 meses)
    - Si existe archivo Parquet → Solo día actual
    - Configurable via `MARKET_DATA_BACKFILL_DAYS` (default: 120)
    
    ## 📊 Indicadores Técnicos Calculados (12)
    
    - **Trend**: SMA (7, 14, 20), EMA (12), MACD (line, signal, histogram)
    - **Momentum**: RSI (14 días)
    - **Volatility**: Bollinger Bands (upper, middle, lower), Volatility 20d
    - **Returns**: Daily return %
    
    ## 💾 Almacenamiento Multi-Capa
    
    ### Layer 1: Parquet (Local Cache)
    - **Formato**: Apache Parquet (compresión Snappy)
    - **Ubicación**: `/opt/airflow/data/{TICKER}_market_data.parquet`
    - **Uso**: Cache local, recovery, análisis local
    - **Ventaja**: 80% menos espacio que CSV
    
    ### Layer 2: Data Warehouse
    - **Development**: PostgreSQL (mismo servidor, schema separado)
    - **Staging/Production**: Amazon Redshift (cluster dedicado)
    - **Estrategia**: UPSERT (inserta nuevos, actualiza existentes)
    - **Schema**: `fact_market_data` con 25+ columnas
    - **Tablas adicionales**: `dim_ticker` con metadatos (long_name, short_name)
    
    ## 🔄 Flujo de Ejecución (6 Tareas)
    
    1. **Validate Ticker**: Valida formato del ticker symbol (soporta múltiples tickers)
    2. **Determine Dates**: Decide backfill (120 días) o incremental (1 día)
    3. **Check API Availability**: Sensor verifica disponibilidad de API con exponential backoff
    4. **Fetch Multiple Dates**: Obtiene datos de Yahoo Finance (1-120 fechas según backfill)
    5. **Transform & Save**: Calcula indicadores y guarda en Parquet
    6. **Load to Warehouse**: Carga desde Parquet a PostgreSQL/Redshift con UPSERT
    
    ## 🌍 Ambientes
    
    - **Development**: PostgreSQL en Docker (postgres:5432)
    - **Staging**: Redshift cluster staging
    - **Production**: Redshift cluster production
    
    Configurado via variable `ENVIRONMENT` (development/staging/production)
    
    ## 🎛️ Parámetros
    
    ```json
    {
        "tickers": ["AAPL", "MSFT", "NVDA"],
        "date": "2025-01-15"
    }
    ```
    
    - **tickers**: Lista de tickers a procesar (soporta múltiples simultáneamente)
    - **date**: Fecha de ejecución (default: fecha actual)
    
    ## ⚙️ Configuración
    
    **Sistema de prioridad**: Las configuraciones se resuelven en este orden:
    1. **Airflow Variables** (prioridad más alta, se pueden cambiar desde la UI sin reiniciar)
    2. **Variables de Entorno** (configuradas en `.env` o sistema)
    3. **Valores por defecto** (hardcoded en el código)
    
    ### Variables de Airflow (Configurables desde UI)
    
    Estas variables pueden configurarse desde la UI de Airflow (Admin → Variables) o como variables de entorno:
    
    - `market_data.default_tickers`: Lista de tickers por defecto (JSON array o CSV)
      - Variable de Entorno equivalente: `MARKET_DATA_DEFAULT_TICKERS`
      - Default: `["AAPL"]`
    
    - `market_data.backfill_days`: Días de backfill en primera ejecución
      - Variable de Entorno equivalente: `MARKET_DATA_BACKFILL_DAYS`
      - Default: `120`
    
    ### Variables de Entorno
    
    Estas variables solo se configuran mediante variables de entorno (`.env` o sistema):
    
    - `ENVIRONMENT`: development | staging | production
      - Controla qué ambiente de warehouse usar
    
    - `MARKET_DATA_STORAGE_DIR`: Directorio Parquet
      - Default: `/opt/airflow/data`
    
    - `WAREHOUSE_LOAD_STRATEGY`: upsert | append | truncate_insert
      - Estrategia de carga al warehouse
    
    - `DEV_WAREHOUSE_HOST`: Host PostgreSQL (development)
      - Host del warehouse en desarrollo
    
    - `PROD_WAREHOUSE_HOST`: Host Redshift (production)
      - Host del warehouse en producción
    
    - `MARKET_DATA_API_TIMEOUT`: Timeout para llamadas API (segundos)
      - Default: `30`
    
    - `MARKET_DATA_MAX_RETRIES`: Número máximo de reintentos
      - Default: `3`
    
    - `MARKET_DATA_SENSOR_POKE_INTERVAL`: Intervalo del sensor (segundos)
      - Default: `30`
    
    - `MARKET_DATA_SENSOR_TIMEOUT`: Timeout del sensor (segundos)
      - Default: `600`
    
    ## 🚀 Características Avanzadas
    
    - **Multi-ticker support**: Procesa múltiples tickers en una sola ejecución
    - **Automatic backfill**: 120 días históricos en primera ejecución
    - **Error handling**: Retries automáticos con exponential backoff
    - **API resilience**: Sensor verifica disponibilidad antes de ejecutar
    - **Data validation**: Validación de formato de tickers y datos
    
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
