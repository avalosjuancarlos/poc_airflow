"""
DAG para obtener datos de mercado desde Yahoo Finance API

Este DAG obtiene datos históricos de precios de un ticker específico
usando la API pública de Yahoo Finance.
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.sensors.python import PythonSensor
from airflow.models import Variable
from datetime import datetime, timedelta
import requests
import json
import logging
import time

# Configuración del logger
logger = logging.getLogger(__name__)

# Headers para evitar bloqueos de la API
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'application/json',
    'Accept-Language': 'en-US,en;q=0.9',
}


def get_market_data(ticker: str, date: str, **context):
    """
    Obtiene datos de mercado de Yahoo Finance API
    
    Args:
        ticker: Símbolo del ticker (ej: AAPL, GOOGL, TSLA)
        date: Fecha en formato YYYY-MM-DD
        
    Returns:
        dict: Datos de mercado del ticker
    """
    try:
        # Convertir fecha a timestamp Unix
        target_date = datetime.strptime(date, '%Y-%m-%d')
        timestamp = int(target_date.timestamp())
        
        # Construir URL de la API
        url = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}"
        params = {
            'period1': timestamp,
            'period2': timestamp,
            'interval': '1d'
        }
        
        logger.info(f"Obteniendo datos de mercado para {ticker} en fecha {date}")
        logger.info(f"URL: {url}")
        logger.info(f"Parámetros: {params}")
        
        # Hacer request a la API con headers y retry logic
        max_retries = 3
        retry_delay = 5  # segundos
        
        for attempt in range(max_retries):
            try:
                # Agregar pequeño delay para evitar rate limiting
                if attempt > 0:
                    wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.info(f"Esperando {wait_time} segundos antes de reintentar...")
                    time.sleep(wait_time)
                
                logger.info(f"Intento {attempt + 1} de {max_retries}")
                response = requests.get(url, params=params, headers=HEADERS, timeout=30)
                
                # Si es 429, esperar y reintentar
                if response.status_code == 429:
                    if attempt < max_retries - 1:
                        retry_after = int(response.headers.get('Retry-After', retry_delay))
                        logger.warning(f"Rate limit alcanzado (429). Esperando {retry_after} segundos...")
                        time.sleep(retry_after)
                        continue
                    else:
                        logger.error("Rate limit alcanzado después de todos los reintentos")
                        response.raise_for_status()
                
                response.raise_for_status()
                break  # Si es exitoso, salir del loop
                
            except requests.exceptions.HTTPError as e:
                if attempt == max_retries - 1:
                    raise
                logger.warning(f"Error HTTP en intento {attempt + 1}: {e}")
            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    raise
                logger.warning(f"Error de red en intento {attempt + 1}: {e}")
        
        # Parsear respuesta JSON
        data = response.json()
        
        # Validar que la respuesta sea exitosa
        if data.get('chart', {}).get('error'):
            error_msg = data['chart']['error']
            logger.error(f"Error en la API de Yahoo Finance: {error_msg}")
            raise ValueError(f"Error en la API: {error_msg}")
        
        # Extraer datos relevantes
        result = data['chart']['result'][0]
        meta = result['meta']
        
        # Extraer datos de precio si existen
        quote_data = {}
        if result.get('indicators', {}).get('quote') and result['indicators']['quote']:
            quote = result['indicators']['quote'][0]
            quote_data = {
                'open': quote.get('open', [None])[0],
                'high': quote.get('high', [None])[0],
                'low': quote.get('low', [None])[0],
                'close': quote.get('close', [None])[0],
                'volume': quote.get('volume', [None])[0],
            }
        
        # Construir respuesta estructurada
        market_data = {
            'ticker': ticker,
            'date': date,
            'timestamp': timestamp,
            'currency': meta.get('currency'),
            'exchange': meta.get('exchangeName'),
            'instrument_type': meta.get('instrumentType'),
            'regular_market_price': meta.get('regularMarketPrice'),
            'regular_market_time': meta.get('regularMarketTime'),
            'quote': quote_data,
            'metadata': {
                'fifty_two_week_high': meta.get('fiftyTwoWeekHigh'),
                'fifty_two_week_low': meta.get('fiftyTwoWeekLow'),
                'long_name': meta.get('longName'),
                'short_name': meta.get('shortName'),
            }
        }
        
        logger.info(f"Datos obtenidos exitosamente para {ticker}")
        logger.info(f"Precio de cierre: {quote_data.get('close')}")
        logger.info(f"Volumen: {quote_data.get('volume')}")
        
        # Guardar datos en XCom para uso posterior
        context['task_instance'].xcom_push(key='market_data', value=market_data)
        
        return market_data
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error en la petición HTTP: {str(e)}")
        raise
    except (KeyError, IndexError) as e:
        logger.error(f"Error al parsear la respuesta de la API: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}")
        raise


def process_market_data(**context):
    """
    Procesa los datos de mercado obtenidos
    
    Esta función puede ser extendida para:
    - Guardar datos en base de datos
    - Generar reportes
    - Calcular indicadores técnicos
    - Enviar notificaciones
    """
    # Obtener datos del paso anterior
    market_data = context['task_instance'].xcom_pull(
        task_ids='fetch_market_data',
        key='market_data'
    )
    
    if not market_data:
        logger.warning("No se obtuvieron datos de mercado")
        return
    
    logger.info("=" * 60)
    logger.info("DATOS DE MERCADO PROCESADOS")
    logger.info("=" * 60)
    logger.info(f"Ticker: {market_data['ticker']}")
    logger.info(f"Fecha: {market_data['date']}")
    logger.info(f"Empresa: {market_data['metadata']['long_name']}")
    logger.info(f"Exchange: {market_data['exchange']}")
    logger.info(f"Moneda: {market_data['currency']}")
    logger.info("-" * 60)
    logger.info("PRECIOS:")
    logger.info(f"  Open:   ${market_data['quote'].get('open')}")
    logger.info(f"  High:   ${market_data['quote'].get('high')}")
    logger.info(f"  Low:    ${market_data['quote'].get('low')}")
    logger.info(f"  Close:  ${market_data['quote'].get('close')}")
    logger.info(f"  Volume: {market_data['quote'].get('volume'):,}")
    logger.info("-" * 60)
    logger.info(f"52-Week High: ${market_data['metadata']['fifty_two_week_high']}")
    logger.info(f"52-Week Low:  ${market_data['metadata']['fifty_two_week_low']}")
    logger.info("=" * 60)
    
    # Aquí puedes agregar lógica adicional:
    # - Guardar en base de datos
    # - Guardar en archivo CSV
    # - Enviar a un data warehouse
    # - Generar alertas si el precio cruza ciertos umbrales
    
    return market_data


def check_api_availability(ticker: str, **context):
    """
    Sensor que verifica si la API de Yahoo Finance está disponible y responde correctamente
    
    Args:
        ticker: Símbolo del ticker para validar
        
    Returns:
        bool: True si la API está disponible, False para reintentar
    """
    try:
        # Usar una fecha reciente para probar la API
        test_date = datetime.now() - timedelta(days=7)
        timestamp = int(test_date.timestamp())
        
        url = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}"
        params = {
            'period1': timestamp,
            'period2': timestamp,
            'interval': '1d'
        }
        
        logger.info(f"Verificando disponibilidad de la API para ticker {ticker}...")
        logger.info(f"URL de prueba: {url}")
        
        # Hacer request de prueba con timeout corto
        response = requests.get(url, params=params, headers=HEADERS, timeout=10)
        
        # Si la API responde con 429, retornar False para reintentar
        if response.status_code == 429:
            logger.warning("API retornó 429 (Rate Limit). Esperando antes de reintentar...")
            return False
        
        # Si hay error de servidor (5xx), retornar False para reintentar
        if 500 <= response.status_code < 600:
            logger.warning(f"API retornó error de servidor: {response.status_code}")
            return False
        
        # Para otros errores HTTP, lanzar excepción
        response.raise_for_status()
        
        # Validar que la respuesta sea JSON válido
        data = response.json()
        
        # Verificar que tenga la estructura esperada
        if not data.get('chart'):
            logger.error("Respuesta de la API no tiene el formato esperado")
            return False
        
        # Verificar si hay error en la respuesta
        if data.get('chart', {}).get('error'):
            error = data['chart']['error']
            logger.error(f"API retornó error: {error}")
            # Si es un error de ticker inválido, fallar inmediatamente
            if 'not found' in str(error).lower() or 'invalid' in str(error).lower():
                raise ValueError(f"Ticker '{ticker}' no es válido o no existe: {error}")
            return False
        
        # Verificar que tenga resultados
        if not data.get('chart', {}).get('result'):
            logger.warning("API no retornó resultados")
            return False
        
        logger.info(f"✅ API de Yahoo Finance está disponible y responde correctamente para {ticker}")
        return True
        
    except requests.exceptions.Timeout:
        logger.warning("Timeout al conectar con la API. Reintentando...")
        return False
    except requests.exceptions.ConnectionError:
        logger.warning("Error de conexión con la API. Reintentando...")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Error al verificar disponibilidad de la API: {str(e)}")
        return False
    except ValueError as e:
        # Errores de validación del ticker deben fallar inmediatamente
        logger.error(str(e))
        raise
    except Exception as e:
        logger.error(f"Error inesperado al verificar API: {str(e)}")
        return False


def validate_ticker(**context):
    """
    Valida que el ticker esté configurado correctamente
    """
    dag_run = context['dag_run']
    ticker = dag_run.conf.get('ticker', 'AAPL')
    
    logger.info(f"Validando ticker: {ticker}")
    
    # Validaciones básicas
    if not ticker or not isinstance(ticker, str):
        raise ValueError("El ticker debe ser un string válido")
    
    if not ticker.isupper():
        logger.warning(f"El ticker '{ticker}' no está en mayúsculas, convirtiendo...")
        ticker = ticker.upper()
    
    logger.info(f"Ticker validado: {ticker}")
    
    # Guardar ticker en XCom para el sensor
    context['task_instance'].xcom_push(key='validated_ticker', value=ticker)
    
    return ticker


# Argumentos por defecto del DAG
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

# Definición del DAG
with DAG(
    dag_id='get_market_data',
    default_args=default_args,
    description='Obtiene datos de mercado desde Yahoo Finance API para un ticker específico',
    schedule_interval=None,  # Ejecución manual o por trigger
    catchup=False,
    tags=['finance', 'market-data', 'yahoo-finance', 'api'],
    params={
        'ticker': 'AAPL',
        'date': datetime.now().strftime('%Y-%m-%d')
    },
    doc_md="""
    # Get Market Data DAG
    
    Este DAG obtiene datos históricos de mercado desde Yahoo Finance API.
    
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
    
    ## Fuente de Datos
    
    Yahoo Finance API: https://query2.finance.yahoo.com/v8/finance/chart/
    
    ## Notas
    
    - Los datos son de mercado público
    - El DAG realiza reintentos automáticos en caso de fallo
    - Los datos se almacenan en XCom para uso posterior
    """
) as dag:
    
    # Tarea 1: Validar ticker
    validate_ticker_task = PythonOperator(
        task_id='validate_ticker',
        python_callable=validate_ticker,
        provide_context=True,
    )
    
    # Tarea 2: Sensor - Verificar disponibilidad de la API
    api_sensor = PythonSensor(
        task_id='check_api_availability',
        python_callable=check_api_availability,
        op_kwargs={
            'ticker': '{{ dag_run.conf.get("ticker", params.ticker) }}',
        },
        poke_interval=30,  # Verificar cada 30 segundos
        timeout=600,  # Timeout de 10 minutos
        mode='poke',  # Modo poke: verifica periódicamente
        exponential_backoff=True,  # Incrementar el intervalo exponencialmente
    )
    
    # Tarea 3: Obtener datos de mercado
    fetch_data_task = PythonOperator(
        task_id='fetch_market_data',
        python_callable=get_market_data,
        op_kwargs={
            'ticker': '{{ dag_run.conf.get("ticker", params.ticker) }}',
            'date': '{{ dag_run.conf.get("date", params.date) }}',
        },
        provide_context=True,
    )
    
    # Tarea 4: Procesar datos obtenidos
    process_data_task = PythonOperator(
        task_id='process_market_data',
        python_callable=process_market_data,
        provide_context=True,
    )
    
    # Definir dependencias
    validate_ticker_task >> api_sensor >> fetch_data_task >> process_data_task

