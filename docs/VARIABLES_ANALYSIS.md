# 🔍 Análisis: Variables de Entorno vs Airflow Variables

## 📋 Criterios de Decisión

### Variables de Entorno (`.env`)
✅ Usar para:
- Configuración de infraestructura (URLs, puertos, hosts)
- Credenciales y secrets
- Configuración que NO cambia frecuentemente
- Configuración a nivel de sistema/contenedor
- Valores que requieren reinicio del servicio

### Airflow Variables (UI/CLI)
✅ Usar para:
- Configuración específica de DAGs
- Valores que cambian frecuentemente
- Configuración que varía por ambiente sin reiniciar
- Valores que usuarios no-técnicos pueden necesitar cambiar
- Parámetros de negocio

---

## 📊 Análisis de Variables Actuales

### ✅ MANTENER como Variables de Entorno

| Variable | Razón | Tipo |
|----------|-------|------|
| `YAHOO_FINANCE_API_BASE_URL` | URL de infraestructura, raramente cambia | Infrastructure |
| `AIRFLOW__CORE__LOAD_EXAMPLES` | Configuración de Airflow core | System |
| `AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION` | Configuración de Airflow core | System |
| `POSTGRES_*` | Credenciales de base de datos | Credentials |
| `REDIS_*` | Configuración de Redis | Infrastructure |
| `_AIRFLOW_WWW_USER_*` | Credenciales de usuario | Credentials |

### 🔄 MIGRAR a Airflow Variables

| Variable Actual (ENV) | Nueva Variable (Airflow) | Razón | Prioridad |
|----------------------|--------------------------|-------|-----------|
| `MARKET_DATA_DEFAULT_TICKER` | `market_data.default_ticker` | Valor de negocio que puede cambiar frecuentemente | 🔴 Alta |
| `MARKET_DATA_MAX_RETRIES` | `market_data.max_retries` | Parámetro configurable sin reinicio | 🟡 Media |
| `MARKET_DATA_RETRY_DELAY` | `market_data.retry_delay` | Parámetro configurable sin reinicio | 🟡 Media |
| `MARKET_DATA_SENSOR_POKE_INTERVAL` | `market_data.sensor_poke_interval` | Parámetro de tuning del sensor | 🟢 Baja |
| `MARKET_DATA_SENSOR_TIMEOUT` | `market_data.sensor_timeout` | Parámetro de tuning del sensor | 🟢 Baja |

### ⚠️ DECIDIR según Caso de Uso

| Variable | Como ENV | Como Airflow Var | Recomendación |
|----------|----------|------------------|---------------|
| `MARKET_DATA_API_TIMEOUT` | Configuración global | Ajustable por DAG | ENV (global) |
| `MARKET_DATA_SENSOR_EXPONENTIAL_BACKOFF` | Comportamiento fijo | Feature flag | ENV (comportamiento) |

---

## 🎯 Propuesta de Implementación

### Fase 1: Variables Críticas de Negocio (Alta Prioridad)

```python
# En get_market_data_dag.py

# Usar Airflow Variable con fallback a ENV
DEFAULT_TICKER = Variable.get(
    "market_data.default_ticker",
    default_var=os.environ.get('MARKET_DATA_DEFAULT_TICKER', 'AAPL')
)
```

**Beneficio**: Los usuarios pueden cambiar el ticker desde la UI sin reiniciar servicios.

### Fase 2: Parámetros de Configuración (Media Prioridad)

```python
# Reintentos configurables
MAX_RETRIES = int(Variable.get(
    "market_data.max_retries",
    default_var=os.environ.get('MARKET_DATA_MAX_RETRIES', '3')
))

RETRY_DELAY = int(Variable.get(
    "market_data.retry_delay",
    default_var=os.environ.get('MARKET_DATA_RETRY_DELAY', '5')
))
```

**Beneficio**: Ajuste fino sin reiniciar contenedores.

### Fase 3: Parámetros de Tuning (Baja Prioridad)

```python
# Configuración del sensor
SENSOR_POKE_INTERVAL = int(Variable.get(
    "market_data.sensor_poke_interval",
    default_var=os.environ.get('MARKET_DATA_SENSOR_POKE_INTERVAL', '30')
))
```

**Beneficio**: Optimización de rendimiento sin downtime.

---

## 🔧 Implementación Recomendada

### Estrategia: Doble Fallback

```python
def get_config_value(airflow_key, env_key, default_value, value_type=str):
    """
    Obtiene valor de configuración con prioridad:
    1. Airflow Variable
    2. Variable de Entorno
    3. Valor por defecto
    """
    try:
        value = Variable.get(airflow_key, default_var=None)
        if value is not None:
            return value_type(value)
    except:
        pass
    
    env_value = os.environ.get(env_key)
    if env_value is not None:
        return value_type(env_value)
    
    return value_type(default_value)

# Uso
DEFAULT_TICKER = get_config_value(
    airflow_key="market_data.default_ticker",
    env_key="MARKET_DATA_DEFAULT_TICKER",
    default_value="AAPL",
    value_type=str
)

MAX_RETRIES = get_config_value(
    airflow_key="market_data.max_retries",
    env_key="MARKET_DATA_MAX_RETRIES",
    default_value=3,
    value_type=int
)
```

### Ventajas de este Enfoque

1. ✅ **Compatibilidad hacia atrás**: Variables de entorno siguen funcionando
2. ✅ **Flexibilidad**: Airflow Variables tienen prioridad
3. ✅ **Sin downtime**: Cambios aplicables sin reinicio
4. ✅ **Fallback robusto**: Si falla Airflow Var, usa ENV
5. ✅ **Migración gradual**: Puedes migrar variable por variable

---

## 📝 Convención de Nombres

### Variables de Airflow

Usar notación con puntos para organización:

```
market_data.default_ticker          # Configuración general
market_data.api.timeout             # Configuración de API
market_data.api.max_retries         # Configuración de reintentos
market_data.sensor.poke_interval    # Configuración de sensor
market_data.sensor.timeout          # Timeout del sensor
```

### Estructura JSON (Opcional)

Agrupar configuraciones relacionadas en un JSON:

```json
{
  "default_ticker": "AAPL",
  "api": {
    "timeout": 30,
    "max_retries": 3,
    "retry_delay": 5
  },
  "sensor": {
    "poke_interval": 30,
    "timeout": 600,
    "exponential_backoff": true
  }
}
```

Acceder con:
```python
import json
config = json.loads(Variable.get("market_data.config"))
DEFAULT_TICKER = config["default_ticker"]
```

---

## 🎨 Ejemplo de UI en Airflow

### Crear Variables desde la Interfaz Web

1. Ve a **Admin → Variables**
2. Click en **+** (Add a new record)
3. Configura:

| Key | Val | Description |
|-----|-----|-------------|
| `market_data.default_ticker` | `AAPL` | Default ticker symbol for market data |
| `market_data.max_retries` | `3` | Maximum number of API retry attempts |
| `market_data.retry_delay` | `5` | Delay in seconds between retries |

### Desde CLI

```bash
# Crear variables
docker compose exec airflow-scheduler airflow variables set \
  market_data.default_ticker "GOOGL"

docker compose exec airflow-scheduler airflow variables set \
  market_data.max_retries "5"

# Ver variable
docker compose exec airflow-scheduler airflow variables get \
  market_data.default_ticker

# Listar todas
docker compose exec airflow-scheduler airflow variables list
```

---

## 🔐 Consideraciones de Seguridad

### Variables Sensibles

Para valores sensibles (API keys, passwords):

```python
# Marcar como sensible en la UI o usar Connections
API_KEY = Variable.get(
    "market_data.api_key",
    default_var=None
)

# Mejor: Usar Airflow Connections
from airflow.hooks.base import BaseHook
connection = BaseHook.get_connection("yahoo_finance_api")
API_KEY = connection.password
```

### NO migrar a Airflow Variables

❌ Credenciales de base de datos  
❌ Passwords de servicios  
❌ API keys sensibles  
❌ Tokens de autenticación  

Estos deben permanecer como:
- Variables de entorno
- Airflow Connections
- Secret backends (Vault, AWS Secrets Manager)

---

## 📊 Comparación de Performance

### Variables de Entorno
- ⚡ Lectura: Instantánea (memoria)
- 🔄 Cambio: Requiere reinicio
- 💾 Storage: Sistema operativo
- 🔒 Seguridad: Protegidas a nivel OS

### Airflow Variables
- ⚡ Lectura: Query a base de datos
- 🔄 Cambio: Inmediato (sin reinicio)
- 💾 Storage: Base de datos de Airflow
- 🔒 Seguridad: Pueden marcarse como sensibles

### Recomendación de Performance

Para DAGs que se ejecutan frecuentemente:
```python
# Cachear variables al inicio del DAG
# En lugar de leerlas en cada tarea

with DAG(...) as dag:
    # Leer una vez al inicio
    config = {
        'ticker': Variable.get("market_data.default_ticker", "AAPL"),
        'max_retries': int(Variable.get("market_data.max_retries", "3")),
    }
    
    # Pasar como parámetros a las tareas
    task = PythonOperator(
        task_id='task',
        op_kwargs=config
    )
```

---

## 🎯 Recomendación Final

### Migrar a Airflow Variables:
1. 🔴 `market_data.default_ticker` - Alta prioridad
2. 🟡 `market_data.max_retries` - Media prioridad  
3. 🟡 `market_data.retry_delay` - Media prioridad

### Mantener como ENV:
- `YAHOO_FINANCE_API_BASE_URL` - Infraestructura
- `MARKET_DATA_API_TIMEOUT` - Configuración global
- `MARKET_DATA_SENSOR_EXPONENTIAL_BACKOFF` - Feature flag
- Todas las credenciales y configuración de Airflow core

### Implementar:
- Función helper `get_config_value()` para doble fallback
- Migración gradual sin breaking changes
- Documentación de ambas formas de configuración

---

**¿Deseas que implemente estos cambios?**

