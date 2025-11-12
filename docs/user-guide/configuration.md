# 🔧 Guía de Configuración

Este documento describe todas las variables de configuración disponibles para el proyecto de Airflow.

## 📋 Tabla de Contenidos

- [Variables de Entorno](#variables-de-entorno)
- [Variables de Airflow](#variables-de-airflow)
- [Configuración del Market Data DAG](#configuración-del-market-data-dag)
- [Cómo Configurar](#cómo-configurar)

---

## 🌍 Variables de Entorno

Las variables de entorno se configuran en el archivo `.env` (basado en `env.template`).

### Airflow Core

| Variable | Valor por Defecto | Descripción |
|----------|-------------------|-------------|
| `AIRFLOW_IMAGE_NAME` | `apache/airflow:2.11.0-python3.10` | Imagen Docker de Airflow |
| `AIRFLOW_UID` | `50000` | User ID para Airflow (importante en Linux) |
| `AIRFLOW_PROJ_DIR` | `.` | Directorio del proyecto |
| `_AIRFLOW_WWW_USER_USERNAME` | `airflow` | Usuario admin de la UI |
| `_AIRFLOW_WWW_USER_PASSWORD` | `airflow` | Contraseña del admin |

### Airflow Settings

| Variable | Valor por Defecto | Descripción |
|----------|-------------------|-------------|
| `AIRFLOW__CORE__LOAD_EXAMPLES` | `false` | ✅ Deshabilitar DAGs de ejemplo |
| `AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION` | `true` | Nuevos DAGs inician pausados |

### Base de Datos

| Variable | Valor por Defecto | Descripción |
|----------|-------------------|-------------|
| `POSTGRES_USER` | `airflow` | Usuario de PostgreSQL |
| `POSTGRES_PASSWORD` | `airflow` | Contraseña de PostgreSQL |
| `POSTGRES_DB` | `airflow` | Nombre de la base de datos |

### Redis

| Variable | Valor por Defecto | Descripción |
|----------|-------------------|-------------|
| `REDIS_PASSWORD` | _(vacío)_ | Contraseña de Redis (opcional) |

---

## 📊 Configuración del Market Data DAG

### Ticker por Defecto

| Variable | Valor por Defecto | Descripción |
|----------|-------------------|-------------|
| `MARKET_DATA_DEFAULT_TICKER` | `AAPL` | Ticker por defecto si no se especifica |

**Ejemplos de valores**:
- `AAPL` - Apple Inc.
- `GOOGL` - Alphabet Inc.
- `MSFT` - Microsoft
- `TSLA` - Tesla
- `AMZN` - Amazon

### Configuración de API

| Variable | Valor por Defecto | Descripción |
|----------|-------------------|-------------|
| `YAHOO_FINANCE_API_BASE_URL` | `https://query2.finance.yahoo.com/v8/finance/chart` | URL base de la API de Yahoo Finance |
| `MARKET_DATA_API_TIMEOUT` | `30` | Timeout en segundos para requests HTTP |

### Configuración de Reintentos

| Variable | Valor por Defecto | Descripción |
|----------|-------------------|-------------|
| `MARKET_DATA_MAX_RETRIES` | `3` | Número máximo de reintentos |
| `MARKET_DATA_RETRY_DELAY` | `5` | Delay inicial en segundos entre reintentos |

**Estrategia de reintentos**:
- Intento 1: Sin delay
- Intento 2: 5 segundos
- Intento 3: 10 segundos (exponential backoff)

### Configuración del Sensor

| Variable | Valor por Defecto | Descripción |
|----------|-------------------|-------------|
| `MARKET_DATA_SENSOR_POKE_INTERVAL` | `30` | Intervalo en segundos entre verificaciones |
| `MARKET_DATA_SENSOR_TIMEOUT` | `600` | Timeout del sensor en segundos (10 min) |
| `MARKET_DATA_SENSOR_EXPONENTIAL_BACKOFF` | `true` | Habilitar exponential backoff |

**Exponential Backoff**:
- Poke 1: 30 segundos
- Poke 2: 60 segundos
- Poke 3: 120 segundos
- ...

---

## 🔧 Cómo Configurar

### 1. Configurar Variables de Entorno

**Opción A: Editar el archivo `.env`**

```bash
cd /Users/juancarlosavalos/ITBA/cloud_data_engineering/poc_airflow

# Si no existe, crear desde template
cp env.template .env

# Editar con tu editor favorito
nano .env
# o
code .env
```

**Ejemplo de configuración personalizada**:

```bash
# Cambiar ticker por defecto a Google
MARKET_DATA_DEFAULT_TICKER=GOOGL

# Aumentar timeout para conexiones lentas
MARKET_DATA_API_TIMEOUT=60

# Más reintentos
MARKET_DATA_MAX_RETRIES=5

# Sensor más frecuente
MARKET_DATA_SENSOR_POKE_INTERVAL=15
```

**Opción B: Variables de entorno del sistema**

```bash
export MARKET_DATA_DEFAULT_TICKER=GOOGL
export MARKET_DATA_API_TIMEOUT=60
```

### 2. Aplicar Cambios

Después de modificar `.env`:

```bash
# Reiniciar los servicios para aplicar cambios
docker compose down
docker compose up -d
```

### 3. Verificar Configuración

```bash
# Ver variables de entorno en un contenedor
docker compose exec airflow-scheduler env | grep MARKET_DATA

# Ver logs para confirmar configuración
docker compose logs -f airflow-scheduler | grep "Configuración"
```

---

## 📊 Variables de Airflow (UI)

Además de las variables de entorno, Airflow permite crear variables desde la UI o CLI.

### Crear Variables desde la UI

1. Ve a **Admin → Variables** en http://localhost:8080
2. Haz clic en "+" para agregar una nueva variable
3. Configura:
   - **Key**: `market_data_default_ticker`
   - **Val**: `GOOGL`

### Crear Variables desde CLI

```bash
# Crear variable
docker compose exec airflow-scheduler airflow variables set market_data_default_ticker "GOOGL"

# Ver variable
docker compose exec airflow-scheduler airflow variables get market_data_default_ticker

# Listar todas las variables
docker compose exec airflow-scheduler airflow variables list
```

### Usar Variables en el Código

```python
from airflow.models import Variable

# Obtener variable con valor por defecto
ticker = Variable.get("market_data_default_ticker", default_var="AAPL")
```

---

## 🔐 Mejores Prácticas

### Seguridad

1. **NO versionar el archivo `.env`** (ya está en `.gitignore`)
2. **Cambiar contraseñas por defecto** en producción
3. **Usar Variables de Airflow para secrets** (se pueden marcar como sensibles)
4. **Rotar credenciales regularmente**

### Desarrollo vs Producción

#### Desarrollo (`.env`)
```bash
MARKET_DATA_DEFAULT_TICKER=AAPL
MARKET_DATA_API_TIMEOUT=30
AIRFLOW__CORE__LOAD_EXAMPLES=false
_AIRFLOW_WWW_USER_PASSWORD=airflow
```

#### Producción (`.env`)
```bash
MARKET_DATA_DEFAULT_TICKER=AAPL
MARKET_DATA_API_TIMEOUT=60
MARKET_DATA_MAX_RETRIES=5
AIRFLOW__CORE__LOAD_EXAMPLES=false
_AIRFLOW_WWW_USER_PASSWORD=${SECURE_PASSWORD_FROM_VAULT}
```

### Gestión de Configuración

#### Opción 1: Archivo `.env` por Ambiente

```bash
.env.development
.env.staging
.env.production
```

Usar el apropiado según el ambiente:
```bash
cp .env.production .env
docker compose up -d
```

#### Opción 2: Docker Compose Override

```yaml
# docker-compose.override.yml (no versionado)
version: '3.8'

x-airflow-common:
  &airflow-common-override
  environment:
    MARKET_DATA_DEFAULT_TICKER: GOOGL
    MARKET_DATA_API_TIMEOUT: 60
```

#### Opción 3: Secrets Manager

Integrar con:
- **HashiCorp Vault**
- **AWS Secrets Manager**
- **Azure Key Vault**
- **Google Secret Manager**

---

## 📖 Recursos

- [Airflow Variables Documentation](https://airflow.apache.org/docs/apache-airflow/stable/howto/variable.html)
- [Docker Compose Environment Variables](https://docs.docker.com/compose/environment-variables/)
- [Airflow Configuration Reference](https://airflow.apache.org/docs/apache-airflow/stable/configurations-ref.html)

---

## 🆘 Troubleshooting

### Las variables no se aplican

1. Verifica que el archivo `.env` esté en la raíz del proyecto
2. Reinicia los contenedores: `docker compose restart`
3. Verifica los logs: `docker compose logs airflow-scheduler`

### Error al leer variables

```bash
# Verificar sintaxis del .env
cat .env | grep -v '^#' | grep -v '^$'

# Verificar que no haya espacios extra
sed 's/ *= */=/g' .env
```

### Variables no disponibles en el DAG

1. Las variables de entorno deben existir al iniciar el contenedor
2. Reiniciar después de cambios en `.env`
3. Verificar que el nombre de la variable sea correcto (case-sensitive)

---

**Última actualización**: Noviembre 2025

