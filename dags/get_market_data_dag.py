"""
DAG para obtener datos de mercado desde Yahoo Finance API

Este DAG obtiene datos históricos de precios de un ticker específico
usando la API pública de Yahoo Finance.

Estructura modular:
- market_data.config: Configuración y settings
- market_data.utils: Utilidades (API client, validators)
- market_data.operators: Funciones de las tareas
- market_data.sensors: Sensores personalizados
"""

import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.sensors.python import PythonSensor

# Import from modular structure
from market_data.config import (
    DEFAULT_TICKER,
    SENSOR_EXPONENTIAL_BACKOFF,
    SENSOR_POKE_INTERVAL,
    SENSOR_TIMEOUT,
    log_configuration,
)
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
    description="Obtiene y transforma datos de mercado con indicadores técnicos - Yahoo Finance API",
    schedule_interval="@daily",  # Run daily
    catchup=False,
    tags=["finance", "market-data", "yahoo-finance", "api", "etl", "parquet"],
    params={"ticker": DEFAULT_TICKER, "date": datetime.now().strftime("%Y-%m-%d")},
    doc_md="""
    # Get Market Data DAG - ETL Pipeline
    
    DAG diario que obtiene datos de mercado, calcula indicadores técnicos y almacena en Parquet.
    
    ## 🎯 Funcionalidad
    
    ### Ejecución Diaria (Schedule: @daily)
    - Obtiene datos del día actual
    - Calcula indicadores técnicos
    - Almacena en formato Parquet
    
    ### Backfill Automático (Primera Ejecución)
    - Si no existe archivo Parquet → Backfill de 20 días
    - Si existe archivo Parquet → Solo día actual
    
    ## 📊 Indicadores Técnicos Calculados
    
    - **Moving Averages**: SMA 7, 14, 20 días
    - **RSI**: Relative Strength Index (14 días)
    - **MACD**: Moving Average Convergence Divergence
    - **Bollinger Bands**: Upper, Middle, Lower
    - **Returns**: Daily return percentage
    - **Volatility**: 20-day rolling volatility
    
    ## 💾 Almacenamiento
    
    - **Formato**: Apache Parquet (compresión Snappy)
    - **Ubicación**: `/opt/airflow/data/{TICKER}_market_data.parquet`
    - **Modo**: Append (deduplica por fecha)
    
    ## 🔄 Flujo de Ejecución
    
    1. **Validate Ticker**: Valida el ticker symbol
    2. **Check API**: Verifica disponibilidad de Yahoo Finance API
    3. **Determine Dates**: Decide backfill (20 días) o single date
    4. **Fetch Data**: Obtiene datos de Yahoo Finance API
    5. **Transform & Save**: Calcula indicadores y guarda en Parquet
    
    ## 🎛️ Parámetros
    
    ```json
    {
        "ticker": "AAPL"
    }
    ```
    
    ## ⚙️ Variables de Entorno
    
    - `MARKET_DATA_DEFAULT_TICKER`: Ticker por defecto (default: AAPL)
    - `MARKET_DATA_STORAGE_DIR`: Directorio de almacenamiento (default: /opt/airflow/data)
    
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
        op_kwargs={
            "ticker": '{{ dag_run.conf.get("ticker", params.ticker) }}',
        },
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

    # Define task dependencies
    # validate → determine dates → check API → fetch data → transform & save
    (
        validate_ticker_task
        >> determine_dates_task
        >> api_sensor
        >> fetch_data_task
        >> transform_and_save_task
    )
