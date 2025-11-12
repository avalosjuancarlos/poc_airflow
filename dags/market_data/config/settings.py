"""
Configuration settings for Market Data DAG

This module handles configuration with a triple fallback system:
1. Airflow Variables (highest priority)
2. Environment Variables
3. Default values (lowest priority)
"""

import logging
import os

from airflow.models import Variable

logger = logging.getLogger(__name__)


def get_config_value(airflow_key, env_key, default_value, value_type=str):
    """
    Obtiene valor de configuración con prioridad de fallback:
    1. Airflow Variable (puede cambiarse desde UI sin reiniciar)
    2. Variable de Entorno (configurada en .env)
    3. Valor por defecto (hardcoded)
    
    Args:
        airflow_key: Nombre de la variable en Airflow (ej: 'market_data.default_ticker')
        env_key: Nombre de la variable de entorno (ej: 'MARKET_DATA_DEFAULT_TICKER')
        default_value: Valor por defecto si no existe en ningún lado
        value_type: Tipo de dato a retornar (str, int, bool, float)
        
    Returns:
        Valor configurado del tipo especificado
        
    Example:
        >>> ticker = get_config_value('market_data.default_ticker', 'MARKET_DATA_DEFAULT_TICKER', 'AAPL')
        >>> # Busca en: Airflow Variable → ENV → Default
    """
    try:
        # Prioridad 1: Airflow Variable
        value = Variable.get(airflow_key, default_var=None)
        if value is not None:
            logger.debug(f"Config '{airflow_key}' obtenida de Airflow Variable: {value}")
            # Manejo especial para booleanos
            if value_type == bool:
                return value.lower() in ('true', '1', 'yes', 'on')
            return value_type(value)
    except Exception as e:
        logger.debug(f"No se pudo obtener Airflow Variable '{airflow_key}': {e}")
    
    # Prioridad 2: Variable de Entorno
    env_value = os.environ.get(env_key)
    if env_value is not None:
        logger.debug(f"Config '{airflow_key}' obtenida de ENV '{env_key}': {env_value}")
        # Manejo especial para booleanos
        if value_type == bool:
            return env_value.lower() in ('true', '1', 'yes', 'on')
        return value_type(env_value)
    
    # Prioridad 3: Valor por defecto
    logger.debug(f"Config '{airflow_key}' usando valor por defecto: {default_value}")
    return value_type(default_value)


# ============================================================================
# Configuration Values
# ============================================================================

# API Configuration - Mantener como ENV (infraestructura)
YAHOO_FINANCE_API_BASE_URL = os.environ.get(
    'YAHOO_FINANCE_API_BASE_URL',
    'https://query2.finance.yahoo.com/v8/finance/chart'
)

# API Timeout - Mantener como ENV (configuración global)
API_TIMEOUT = int(os.environ.get('MARKET_DATA_API_TIMEOUT', '30'))

# Default Ticker - Migrado a Airflow Variable con fallback
DEFAULT_TICKER = get_config_value(
    airflow_key='market_data.default_ticker',
    env_key='MARKET_DATA_DEFAULT_TICKER',
    default_value='AAPL',
    value_type=str
)

# Retry Configuration - Migrado a Airflow Variables con fallback
MAX_RETRIES = get_config_value(
    airflow_key='market_data.max_retries',
    env_key='MARKET_DATA_MAX_RETRIES',
    default_value='3',
    value_type=int
)

RETRY_DELAY = get_config_value(
    airflow_key='market_data.retry_delay',
    env_key='MARKET_DATA_RETRY_DELAY',
    default_value='5',
    value_type=int
)

# Sensor Configuration - Migrado a Airflow Variables con fallback
SENSOR_POKE_INTERVAL = get_config_value(
    airflow_key='market_data.sensor_poke_interval',
    env_key='MARKET_DATA_SENSOR_POKE_INTERVAL',
    default_value='30',
    value_type=int
)

SENSOR_TIMEOUT = get_config_value(
    airflow_key='market_data.sensor_timeout',
    env_key='MARKET_DATA_SENSOR_TIMEOUT',
    default_value='600',
    value_type=int
)

# Exponential Backoff - Mantener como ENV (feature flag)
SENSOR_EXPONENTIAL_BACKOFF = os.environ.get(
    'MARKET_DATA_SENSOR_EXPONENTIAL_BACKOFF', 
    'true'
).lower() == 'true'

# Headers para evitar bloqueos de la API
HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/91.0.4472.124 Safari/537.36'
    ),
    'Accept': 'application/json',
    'Accept-Language': 'en-US,en;q=0.9',
}


def log_configuration():
    """Log current configuration values"""
    try:
        logger.info("=" * 60)
        logger.info("CONFIGURACIÓN DEL DAG DE MARKET DATA")
        logger.info("=" * 60)
        logger.info(f"API Base URL: {YAHOO_FINANCE_API_BASE_URL}")
        logger.info(f"Default Ticker: {DEFAULT_TICKER}")
        logger.info(f"API Timeout: {API_TIMEOUT}s")
        logger.info(f"Max Retries: {MAX_RETRIES}")
        logger.info(f"Retry Delay: {RETRY_DELAY}s")
        logger.info(f"Sensor Poke Interval: {SENSOR_POKE_INTERVAL}s")
        logger.info(f"Sensor Timeout: {SENSOR_TIMEOUT}s")
        logger.info(f"Sensor Exponential Backoff: {SENSOR_EXPONENTIAL_BACKOFF}")
        logger.info("=" * 60)
    except Exception as e:
        logger.debug(f"Could not log configuration (likely in test mode): {e}")
