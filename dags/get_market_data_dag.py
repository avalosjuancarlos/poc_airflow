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

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.sensors.python import PythonSensor
from datetime import datetime, timedelta

# Import from modular structure
from market_data.config import (
    log_configuration,
    DEFAULT_TICKER,
    SENSOR_POKE_INTERVAL,
    SENSOR_TIMEOUT,
    SENSOR_EXPONENTIAL_BACKOFF
)
from market_data.operators import (
    validate_ticker,
    fetch_market_data,
    process_market_data
)
from market_data.sensors import check_api_availability

# Log configuration on DAG load (skip in test mode)
import os
if not os.environ.get('AIRFLOW__CORE__UNIT_TEST_MODE'):
    log_configuration()

# ============================================================================
# DAG Definition
# ============================================================================

# Default arguments
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=2),
    'execution_timeout': timedelta(minutes=10),
}

# Define DAG
with DAG(
    dag_id='get_market_data',
    default_args=default_args,
    description='Obtiene datos de mercado desde Yahoo Finance API para un ticker específico',
    schedule_interval=None,  # Manual execution
    catchup=False,
    tags=['finance', 'market-data', 'yahoo-finance', 'api'],
    params={
        'ticker': DEFAULT_TICKER,
        'date': datetime.now().strftime('%Y-%m-%d')
    },
    doc_md="""
    # Get Market Data DAG
    
    Este DAG obtiene datos históricos de mercado desde Yahoo Finance API.
    
    ## Arquitectura Modular
    
    - **config**: Configuración centralizada
    - **utils**: API client y validadores
    - **operators**: Funciones de tareas
    - **sensors**: Sensores personalizados
    
    ## Parámetros de Configuración
    
    Al ejecutar el DAG, puedes proporcionar:
    - **ticker**: Símbolo del ticker (ej: AAPL, GOOGL, MSFT, TSLA)
    - **date**: Fecha en formato YYYY-MM-DD
    
    ## Ejemplo de Configuración JSON
    
    ```json
    {
        "ticker": "AAPL",
        "date": "2023-11-09"
    }
    ```
    
    ## Configuración Avanzada
    
    Puedes configurar el comportamiento del DAG usando Airflow Variables:
    
    - `market_data.default_ticker`: Ticker por defecto
    - `market_data.max_retries`: Número de reintentos
    - `market_data.retry_delay`: Delay entre reintentos
    - `market_data.sensor_poke_interval`: Intervalo del sensor
    - `market_data.sensor_timeout`: Timeout del sensor
    
    Ver `docs/AIRFLOW_VARIABLES_GUIDE.md` para más información.
    
    ## Fuente de Datos
    
    Yahoo Finance API: https://query2.finance.yahoo.com/v8/finance/chart/
    
    ## Notas
    
    - Los datos son de mercado público
    - El DAG realiza reintentos automáticos en caso de fallo
    - Los datos se almacenan en XCom para uso posterior
    - Incluye sensor de disponibilidad de API
    """
) as dag:
    
    # Task 1: Validate ticker
    validate_ticker_task = PythonOperator(
        task_id='validate_ticker',
        python_callable=validate_ticker,
        provide_context=True,
    )
    
    # Task 2: Sensor - Check API availability
    api_sensor = PythonSensor(
        task_id='check_api_availability',
        python_callable=check_api_availability,
        op_kwargs={
            'ticker': '{{ dag_run.conf.get("ticker", params.ticker) }}',
        },
        poke_interval=SENSOR_POKE_INTERVAL,
        timeout=SENSOR_TIMEOUT,
        mode='poke',
        exponential_backoff=SENSOR_EXPONENTIAL_BACKOFF,
    )
    
    # Task 3: Fetch market data
    fetch_data_task = PythonOperator(
        task_id='fetch_market_data',
        python_callable=fetch_market_data,
        op_kwargs={
            'ticker': '{{ dag_run.conf.get("ticker", params.ticker) }}',
            'date': '{{ dag_run.conf.get("date", params.date) }}',
        },
        provide_context=True,
    )
    
    # Task 4: Process market data
    process_data_task = PythonOperator(
        task_id='process_market_data',
        python_callable=process_market_data,
        provide_context=True,
    )
    
    # Define task dependencies
    validate_ticker_task >> api_sensor >> fetch_data_task >> process_data_task
