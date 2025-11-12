# 🎯 Guía de Variables de Airflow - Market Data DAG

Esta guía explica cómo configurar y usar las Variables de Airflow para el Market Data DAG.

## 📋 Tabla de Contenidos

- [Introducción](#introducción)
- [Sistema de Prioridad](#sistema-de-prioridad)
- [Variables Disponibles](#variables-disponibles)
- [Configuración Rápida](#configuración-rápida)
- [Configuración Manual](#configuración-manual)
- [Ejemplos de Uso](#ejemplos-de-uso)
- [Troubleshooting](#troubleshooting)

---

## 🎯 Introducción

El Market Data DAG implementa un **sistema de doble fallback** para la configuración:

```
Airflow Variable → Variable de Entorno → Valor por Defecto
```

**Ventajas**:
- ✅ Cambios sin reiniciar servicios
- ✅ Configuración desde la UI de Airflow
- ✅ Compatibilidad con variables de entorno
- ✅ Valores por defecto sensatos

---

## 🔄 Sistema de Prioridad

### Orden de Búsqueda

1. **Airflow Variable** (Prioridad Alta)
   - Configurable desde UI: `Admin → Variables`
   - Configurable desde CLI
   - Sin necesidad de reiniciar

2. **Variable de Entorno** (Prioridad Media)
   - Configurada en `.env`
   - Requiere reinicio de contenedores

3. **Valor por Defecto** (Prioridad Baja)
   - Hardcoded en el código
   - Siempre disponible como fallback

### Ejemplo de Funcionamiento

```python
# Variable: market_data.default_ticker

# Escenario 1: Airflow Variable existe
# Resultado: "GOOGL"
Airflow Variable: "GOOGL"
ENV Variable: "AAPL"
Default: "AAPL"
→ Usa: "GOOGL"

# Escenario 2: Solo ENV existe
# Resultado: "TSLA"
Airflow Variable: (no existe)
ENV Variable: "TSLA"
Default: "AAPL"
→ Usa: "TSLA"

# Escenario 3: Nada configurado
# Resultado: "AAPL"
Airflow Variable: (no existe)
ENV Variable: (no existe)
Default: "AAPL"
→ Usa: "AAPL"
```

---

## 📊 Variables Disponibles

### Variables con Airflow Fallback

| Airflow Variable | ENV Fallback | Default | Tipo | Descripción |
|-----------------|--------------|---------|------|-------------|
| `market_data.default_ticker` | `MARKET_DATA_DEFAULT_TICKER` | `AAPL` | string | Ticker por defecto |
| `market_data.max_retries` | `MARKET_DATA_MAX_RETRIES` | `3` | int | Máximo de reintentos |
| `market_data.retry_delay` | `MARKET_DATA_RETRY_DELAY` | `5` | int | Delay entre reintentos (seg) |
| `market_data.sensor_poke_interval` | `MARKET_DATA_SENSOR_POKE_INTERVAL` | `30` | int | Intervalo del sensor (seg) |
| `market_data.sensor_timeout` | `MARKET_DATA_SENSOR_TIMEOUT` | `600` | int | Timeout del sensor (seg) |

### Variables Solo de Entorno

Estas NO tienen fallback de Airflow Variables:

| ENV Variable | Default | Descripción |
|-------------|---------|-------------|
| `YAHOO_FINANCE_API_BASE_URL` | `https://query2...` | URL base de la API |
| `MARKET_DATA_API_TIMEOUT` | `30` | Timeout HTTP global |
| `MARKET_DATA_SENSOR_EXPONENTIAL_BACKOFF` | `true` | Feature flag |

---

## 🚀 Configuración Rápida

### Opción 1: Script Automático

```bash
# Ejecutar script de configuración
./scripts/setup_airflow_variables.sh
```

Este script:
1. ✅ Verifica que los servicios estén corriendo
2. ✅ Crea todas las variables con valores por defecto
3. ✅ Muestra las variables creadas
4. ✅ Proporciona instrucciones de uso

### Opción 2: Comando Manual

```bash
# Crear todas las variables de una vez
docker compose exec airflow-scheduler bash -c '
airflow variables set market_data.default_ticker "AAPL" &&
airflow variables set market_data.max_retries "3" &&
airflow variables set market_data.retry_delay "5" &&
airflow variables set market_data.sensor_poke_interval "30" &&
airflow variables set market_data.sensor_timeout "600"
'
```

---

## 🔧 Configuración Manual

### Desde la Interfaz Web

1. **Acceder a Variables**
   - Abre http://localhost:8080
   - Ve a `Admin` → `Variables`

2. **Crear Nueva Variable**
   - Haz clic en el botón `+` (Add a new record)
   - Completa los campos:
     - **Key**: `market_data.default_ticker`
     - **Val**: `GOOGL`
     - **Description**: (opcional) Default ticker symbol

3. **Guardar**
   - Haz clic en `Save`
   - La variable estará disponible inmediatamente

### Desde la CLI

#### Crear Variable

```bash
# Sintaxis
docker compose exec airflow-scheduler \
  airflow variables set KEY "VALUE"

# Ejemplos
docker compose exec airflow-scheduler \
  airflow variables set market_data.default_ticker "GOOGL"

docker compose exec airflow-scheduler \
  airflow variables set market_data.max_retries "5"
```

#### Ver Variable

```bash
# Ver una variable específica
docker compose exec airflow-scheduler \
  airflow variables get market_data.default_ticker

# Listar todas las variables
docker compose exec airflow-scheduler \
  airflow variables list

# Buscar variables de market_data
docker compose exec airflow-scheduler \
  airflow variables list | grep market_data
```

#### Actualizar Variable

```bash
# Actualizar (mismo comando que crear)
docker compose exec airflow-scheduler \
  airflow variables set market_data.default_ticker "MSFT"
```

#### Eliminar Variable

```bash
# Eliminar una variable
docker compose exec airflow-scheduler \
  airflow variables delete market_data.default_ticker
```

---

## 💡 Ejemplos de Uso

### Ejemplo 1: Cambiar Ticker por Defecto

**Objetivo**: Cambiar de AAPL a GOOGL sin reiniciar servicios

```bash
# Crear/actualizar variable
docker compose exec airflow-scheduler \
  airflow variables set market_data.default_ticker "GOOGL"

# Verificar
docker compose exec airflow-scheduler \
  airflow variables get market_data.default_ticker
# Output: GOOGL

# El siguiente DAG run usará GOOGL automáticamente
```

**Resultado**: Sin reiniciar contenedores, el próximo run del DAG usará GOOGL.

### Ejemplo 2: Aumentar Reintentos Temporalmente

**Objetivo**: Aumentar reintentos debido a problemas de red

```bash
# Configuración normal
docker compose exec airflow-scheduler \
  airflow variables set market_data.max_retries "3"

# Aumentar temporalmente durante problemas de red
docker compose exec airflow-scheduler \
  airflow variables set market_data.max_retries "10"

# Volver a normal cuando se resuelva
docker compose exec airflow-scheduler \
  airflow variables set market_data.max_retries "3"
```

### Ejemplo 3: Ajuste Fino del Sensor

**Objetivo**: Optimizar el sensor para API lenta

```bash
# Sensor más paciente
docker compose exec airflow-scheduler \
  airflow variables set market_data.sensor_timeout "1200"  # 20 min

docker compose exec airflow-scheduler \
  airflow variables set market_data.sensor_poke_interval "60"  # Cada 60s
```

### Ejemplo 4: Configuración por Ambiente

#### Desarrollo
```bash
# Configuración para desarrollo (más rápido)
docker compose exec airflow-scheduler bash -c '
airflow variables set market_data.default_ticker "AAPL" &&
airflow variables set market_data.max_retries "2" &&
airflow variables set market_data.sensor_timeout "300"
'
```

#### Producción
```bash
# Configuración para producción (más robusto)
docker compose exec airflow-scheduler bash -c '
airflow variables set market_data.default_ticker "AAPL" &&
airflow variables set market_data.max_retries "5" &&
airflow variables set market_data.sensor_timeout "900"
'
```

---

## 🔍 Ver Configuración Activa

### Desde los Logs

```bash
# Ver configuración al cargar el DAG
docker compose logs airflow-scheduler | grep "CONFIGURACIÓN DEL DAG"

# Output esperado:
# ==========================================================
# CONFIGURACIÓN DEL DAG DE MARKET DATA
# ==========================================================
# API Base URL: https://query2.finance.yahoo.com/v8/finance/chart
# Default Ticker: GOOGL
# API Timeout: 30s
# Max Retries: 5
# Retry Delay: 5s
# Sensor Poke Interval: 30s
# Sensor Timeout: 600s
# Sensor Exponential Backoff: True
# ==========================================================
```

### Desde la UI de Airflow

1. Ve a `Admin` → `Variables`
2. Busca variables que empiecen con `market_data.`
3. Verás los valores actuales

---

## 🐛 Troubleshooting

### Variable no se aplica

**Problema**: Cambié la variable pero el DAG sigue usando el valor antiguo.

**Solución**:
```bash
# 1. Verificar que la variable existe
docker compose exec airflow-scheduler \
  airflow variables get market_data.default_ticker

# 2. Verificar logs del scheduler
docker compose logs airflow-scheduler | grep "market_data.default_ticker"

# 3. Refrescar el DAG (pausar y despausar en la UI)

# 4. Si persiste, reiniciar scheduler
docker compose restart airflow-scheduler
```

### No puedo crear variables

**Problema**: Error al crear variables desde CLI.

**Solución**:
```bash
# 1. Verificar que los servicios están corriendo
docker compose ps

# 2. Verificar que puedes conectarte al scheduler
docker compose exec airflow-scheduler airflow version

# 3. Verificar permisos
docker compose exec airflow-scheduler ls -la /opt/airflow/

# 4. Ver logs de error
docker compose logs airflow-scheduler | tail -50
```

### Variable retorna None

**Problema**: `Variable.get()` retorna None.

**Causas posibles**:
1. Nombre de variable incorrecto (case-sensitive)
2. Variable no existe
3. Permisos incorrectos

**Solución**:
```bash
# Verificar nombre exacto
docker compose exec airflow-scheduler \
  airflow variables list | grep market

# Crear si no existe
docker compose exec airflow-scheduler \
  airflow variables set market_data.default_ticker "AAPL"
```

### Valores no se convierten correctamente

**Problema**: Variable "3" se lee como string en lugar de int.

**Solución**: El helper `get_config_value()` maneja la conversión automáticamente.

```python
# Correcto - especificar value_type
MAX_RETRIES = get_config_value(
    airflow_key='market_data.max_retries',
    env_key='MARKET_DATA_MAX_RETRIES',
    default_value='3',
    value_type=int  # ← Importante!
)
```

---

## 📝 Best Practices

### 1. Nombrar Variables

✅ **Bueno**: `market_data.default_ticker`  
❌ **Malo**: `default_ticker`, `TICKER`, `ticker`

- Usa prefijo para agrupar (`market_data.`)
- Usa snake_case
- Nombres descriptivos

### 2. Documentar Cambios

```bash
# Cuando cambies una variable, documenta por qué
docker compose exec airflow-scheduler \
  airflow variables set market_data.max_retries "10"

# Agregar nota en commit o ticket
# "Increased retries to 10 due to API instability (TICKET-123)"
```

### 3. Testing

```bash
# Probar con diferentes valores antes de aplicar en prod
docker compose exec airflow-scheduler \
  airflow variables set market_data.max_retries "1"

# Ejecutar DAG y verificar comportamiento

# Ajustar según resultados
docker compose exec airflow-scheduler \
  airflow variables set market_data.max_retries "3"
```

### 4. Backup de Variables

```bash
# Exportar todas las variables
docker compose exec airflow-scheduler \
  airflow variables export variables_backup.json

# Importar variables
docker compose exec airflow-scheduler \
  airflow variables import variables_backup.json
```

---

## 🔗 Referencias

- [Documentación de Configuración](./CONFIGURATION.md)
- [Análisis de Variables](./VARIABLES_ANALYSIS.md)
- [Airflow Variables Documentation](https://airflow.apache.org/docs/apache-airflow/stable/howto/variable.html)

---

**Última actualización**: Noviembre 2025

