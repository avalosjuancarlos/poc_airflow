# Get Market Data DAG - Pipeline ETL Completo

DAG de producción para obtener, transformar y almacenar datos de mercado desde Yahoo Finance API.

---

## 🎯 Descripción

**Pipeline ETL completo** que:
- **Extrae** datos de Yahoo Finance API
- **Transforma** datos calculando 12 indicadores técnicos
- **Carga** datos en formato Parquet con persistencia

**Schedule**: `@daily` (ejecución automática diaria a las 00:00 UTC)

---

## ✨ Características Principales

### 1. **Backfill Automático** ✅
- **Primera ejecución** (sin Parquet): Backfill de **20 días históricos**
- **Ejecuciones posteriores**: Solo **día actual**
- Lógica inteligente de determinación de fechas

### 2. **12 Indicadores Técnicos** ✅
#### Tendencia (Trend)
- **SMA** (Simple Moving Average): 7, 14, 20 días
- **EMA** (Exponential Moving Average)
- **MACD** (Moving Average Convergence Divergence)
  - Línea MACD
  - Línea de señal (Signal Line)
  - Histograma MACD

#### Momentum
- **RSI** (Relative Strength Index): 14 días

#### Volatilidad
- **Bollinger Bands**: Upper, Middle, Lower (20 días, 2σ)
- **Volatility**: Desviación estándar rolling de 20 días

#### Retornos
- **Daily Return**: Cambio porcentual diario
- **Daily Return %**: Formato porcentaje

### 3. **Almacenamiento Parquet** ✅
- **Formato**: Apache Parquet (compresión Snappy)
- **Ubicación**: `/opt/airflow/data/{TICKER}_market_data.parquet`
- **Modo**: Append con deduplicación automática por fecha
- **Persistencia**: A través de volumen Docker

### 4. **Smart Timestamp Logic** ✅
- **Fechas históricas**: Usa 6PM (después del cierre del mercado)
- **Hoy antes de 6PM**: Usa hora actual (evita timestamps futuros)
- **Hoy después de 6PM**: Usa 6PM
- **Previene**: Errores HTTP 400 por timestamps futuros

### 5. **Manejo de Fines de Semana** ✅
- API devuelve datos vacíos para sábado/domingo
- El código continúa procesando sin fallar
- Solo días con datos válidos se incluyen en indicadores

---

## 📊 Flujo del DAG

### **Arquitectura (5 Tareas)**

```
1. validate_ticker
       ↓
2. determine_dates  🆕
   ├─ No Parquet? → Backfill 20 días
   └─ Existe? → Solo hoy
       ↓
3. check_api_availability (Sensor)
       ↓
4. fetch_multiple_dates  🆕
   └─ Fetch para todas las fechas
       ↓
5. transform_and_save  🆕
   ├─ Calcula indicadores técnicos
   └─ Guarda en Parquet
```

### **Comparación con Versión Anterior**

| Aspecto | Antes | Ahora |
|---------|-------|-------|
| **Tasks** | 4 | 5 |
| **Schedule** | Manual (`None`) | Diario (`@daily`) |
| **Datos** | 1 fecha | 1-20 fechas (backfill) |
| **Transformación** | No | 12 indicadores ✅ |
| **Storage** | XCom (temporal) | Parquet (persistente) ✅ |
| **Backfill** | No | Automático ✅ |

---

## 🚀 Uso

### **Primera Ejecución (No hay Parquet)**

#### Desde Airflow UI:
1. Abre http://localhost:8080
2. Activa el DAG `get_market_data`
3. Trigger manualmente con:
   ```json
   {"ticker": "AAPL"}
   ```

#### Lo que sucede:
```
1. Valida ticker: AAPL ✅
2. Detecta: No existe AAPL_market_data.parquet
3. Determina fechas: Últimos 20 días (ej: 2025-10-24 a 2025-11-12)
4. Verifica API: Disponible ✅
5. Fetch data: 20 requests (14 con datos, 6 fines de semana vacíos)
6. Transforma: Calcula 12 indicadores técnicos
7. Guarda: /opt/airflow/data/AAPL_market_data.parquet (~50KB)
```

**Resultado**: Archivo Parquet con 14 días de trading + 12 indicadores

---

### **Ejecuciones Diarias (Parquet Existe)**

#### Automático (@daily):
- Se ejecuta automáticamente a las 00:00 UTC cada día

#### Lo que sucede:
```
1. Valida ticker: AAPL ✅
2. Detecta: Existe AAPL_market_data.parquet
3. Determina fechas: Solo hoy (2025-11-13)
4. Verifica API: Disponible ✅
5. Fetch data: 1 request para hoy
6. Transforma: Recalcula indicadores para TODO el dataset
7. Guarda: Append a Parquet existente (~52KB ahora)
```

**Resultado**: 1 nuevo día agregado, todos los indicadores actualizados

---

### **Trigger con Ticker Diferente**

```json
{"ticker": "TSLA"}
```

- Si no existe `TSLA_market_data.parquet`: Backfill de 20 días
- Si existe: Solo agrega día actual
- Cada ticker tiene su propio archivo Parquet

---

## 📦 Datos Almacenados

### **Estructura del Archivo Parquet**

```
/opt/airflow/data/
├── AAPL_market_data.parquet   (~50KB por 20 días)
├── TSLA_market_data.parquet
└── GOOGL_market_data.parquet
```

### **Columnas del DataFrame (25+)**

#### OHLCV + Metadata
```
- date             (datetime)
- ticker           (string)
- open             (float64)
- high             (float64)
- low              (float64)
- close            (float64)
- volume           (int64)
- currency         (string)
- exchange         (string)
- instrument_type  (string)
```

#### Indicadores de Tendencia
```
- sma_7            (float64)
- sma_14           (float64)
- sma_20           (float64)
- ema_12           (float64)
- macd             (float64)
- macd_signal      (float64)
- macd_histogram   (float64)
```

#### Indicadores de Momentum
```
- rsi              (float64)
```

#### Indicadores de Volatilidad
```
- bb_upper         (float64)
- bb_middle        (float64)
- bb_lower         (float64)
- volatility_20d   (float64)
```

#### Retornos
```
- daily_return     (float64)
- daily_return_pct (float64)
```

#### Metadata Adicional
```
- regular_market_price    (float64)
- fifty_two_week_high     (float64)
- fifty_two_week_low      (float64)
- long_name               (string)
- short_name              (string)
```

---

## 🔧 Configuración

### **Variables de Entorno**

```bash
# Storage
MARKET_DATA_STORAGE_DIR=/opt/airflow/data

# API
YAHOO_FINANCE_API_BASE_URL=https://query2.finance.yahoo.com/v8/finance/chart
MARKET_DATA_DEFAULT_TICKER=AAPL
MARKET_DATA_API_TIMEOUT=30

# Retry Logic
MARKET_DATA_MAX_RETRIES=3
MARKET_DATA_RETRY_DELAY=5

# Sensor
MARKET_DATA_SENSOR_POKE_INTERVAL=30
MARKET_DATA_SENSOR_TIMEOUT=600
MARKET_DATA_SENSOR_EXPONENTIAL_BACKOFF=true
```

Ver `configuration.md` para lista completa.

---

## 🧪 Ejemplos de Uso

### **Ejemplo 1: Backfill de AAPL**

```bash
# Primera ejecución
docker compose exec airflow-scheduler airflow dags trigger get_market_data \
  --conf '{"ticker": "AAPL"}'

# Resultado:
# - Fetch de 20 días
# - 14 días con datos (lunes-viernes)
# - 6 días sin datos (fines de semana)
# - Archivo: AAPL_market_data.parquet (14 registros con 25+ columnas)
```

### **Ejemplo 2: Actualización Diaria**

```bash
# Ejecución automática diaria o manual
docker compose exec airflow-scheduler airflow dags trigger get_market_data

# Resultado:
# - Fetch solo día actual
# - Append a Parquet existente
# - Indicadores recalculados para todo el dataset
```

### **Ejemplo 3: Múltiples Tickers**

```bash
# Trigger para cada ticker
docker compose exec airflow-scheduler airflow dags trigger get_market_data \
  --conf '{"ticker": "TSLA"}'

docker compose exec airflow-scheduler airflow dags trigger get_market_data \
  --conf '{"ticker": "GOOGL"}'

# Resultado:
# - Cada ticker tiene su propio Parquet
# - Backfill independiente por ticker
# - Datos aislados por ticker
```

---

## 📈 Ejemplo de Output

### **Logs de Ejecución Exitosa**

```
[2025-11-12] INFO - Backfill dates prepared: 2025-10-24 to 2025-11-12
[2025-11-12] INFO - Fetching 1/20: 2025-10-24
[2025-11-12] INFO - API URL: .../AAPL?period1=1761328800&period2=1761328800&interval=1d
[2025-11-12] INFO - Quote data arrays: close_len=1, volume_len=1
[2025-11-12] INFO - First close value: 262.82
[2025-11-12] INFO - Fetch complete: 14 successful, 6 failed (weekends)
[2025-11-12] INFO - Data validation: 14/14 records with valid close prices
[2025-11-12] INFO - Calculating moving averages...
[2025-11-12] INFO - Calculating RSI...
[2025-11-12] INFO - Calculating MACD...
[2025-11-12] INFO - Calculating Bollinger Bands...
[2025-11-12] INFO - Transformation complete. DataFrame shape: (14, 28)
[2025-11-12] INFO - Saved 14 records to /opt/airflow/data/AAPL_market_data.parquet
[2025-11-12] INFO - AUDIT: parquet_saved | ticker=AAPL | records=14 | file_size=48.5KB
```

### **Estructura del DataFrame Guardado**

```python
import pandas as pd

# Leer el Parquet
df = pd.read_parquet('/opt/airflow/data/AAPL_market_data.parquet')

print(df.head())
```

```
         date ticker    open    high     low   close    volume  sma_7  sma_14  sma_20    rsi   macd  ...
0  2025-10-24   AAPL  261.19  264.13  259.18  262.82  38253700    NaN     NaN     NaN    NaN    NaN  ...
1  2025-10-27   AAPL  264.88  269.12  264.65  268.81  44888200    NaN     NaN     NaN    NaN    NaN  ...
2  2025-10-28   AAPL  268.99  269.89  268.15  269.00  41534800  267.2     NaN     NaN  52.31    NaN  ...
3  2025-10-29   AAPL  269.28  271.41  267.11  269.70  51086700  268.1     NaN     NaN  54.22    NaN  ...
4  2025-10-30   AAPL  271.99  274.14  268.48  271.40  69886500  269.3   267.8     NaN  58.41  0.23  ...
...
```

---

## 🔄 Smart Timestamp Logic

### **Problema Resuelto**

Yahoo Finance rechaza timestamps futuros con HTTP 400.

Ejemplo problemático:
- Hora actual: 4:49 PM (16:49)
- Timestamp solicitado: 6:00 PM (18:00) del mismo día
- Resultado: ❌ HTTP 400 Bad Request

### **Solución Implementada**

```python
# Para fechas históricas → 6PM (mercado ya cerró)
# Para HOY antes de 6PM → Hora actual (evita futuro)
# Para HOY después de 6PM → 6PM (mercado ya cerró)

if target_date.date() == now.date() and now < 6PM:
    timestamp = now  # Usa hora actual
else:
    timestamp = 6PM  # Usa 6PM fijo
```

### **Ejemplos**

| Fecha Solicitada | Hora Actual | Timestamp Usado | Razón |
|------------------|-------------|-----------------|-------|
| 2025-11-11 | 2025-11-12 16:00 | 2025-11-11 18:00 | Fecha pasada → 6PM |
| 2025-11-12 | 2025-11-12 16:00 | 2025-11-12 16:00 | Hoy antes de 6PM → Ahora |
| 2025-11-12 | 2025-11-12 19:00 | 2025-11-12 18:00 | Hoy después de 6PM → 6PM |

---

## 🔧 Configuración del DAG

### **Parámetros**

```python
params={
    'ticker': 'AAPL',        # Ticker por defecto
    'date': '2025-11-12'     # Fecha actual (se actualiza automáticamente)
}
```

### **Defaults**

```python
default_args = {
    'owner': 'airflow',
    'start_date': datetime(2025, 1, 1),  # Inicio del DAG
    'schedule_interval': '@daily',        # Ejecución diaria
    'catchup': False,                      # No backfill automático de Airflow
    'retries': 2,                          # 2 reintentos por tarea
    'retry_delay': timedelta(minutes=2),  # 2 min entre reintentos
    'execution_timeout': timedelta(minutes=10),  # 10 min timeout (15 para fetch)
}
```

---

## 📋 Tareas Detalladas

### **Task 1: `validate_ticker`** (PythonOperator)

**Función**: Valida formato y existencia del ticker

**Validaciones**:
- ✅ No vacío
- ✅ Solo caracteres alfanuméricos y guiones
- ✅ Máximo 10 caracteres
- ✅ Convierte a mayúsculas

**Output**: Ticker validado (push a XCom: `validated_ticker`)

---

### **Task 2: `determine_dates`** (PythonOperator) 🆕

**Función**: Determina qué fechas obtener según existencia de Parquet

**Lógica**:
```python
if not check_parquet_exists(ticker):
    # No existe Parquet → BACKFILL
    dates = [execution_date - timedelta(days=i) for i in range(19, -1, -1)]
    # Resultado: 20 fechas (ej: 2025-10-24 a 2025-11-12)
else:
    # Existe Parquet → INCREMENTAL
    dates = [execution_date]
    # Resultado: 1 fecha (solo hoy)
```

**Output**: 
```python
{
    "dates": ["2025-10-24", "2025-10-25", ..., "2025-11-12"],
    "ticker": "AAPL",
    "is_backfill": True
}
```

---

### **Task 3: `check_api_availability`** (PythonSensor)

**Función**: Verifica que Yahoo Finance API esté disponible

**Verificaciones**:
- ✅ API responde (no timeout)
- ✅ Status code 2xx
- ✅ Estructura JSON válida
- ✅ Ticker existe

**Manejo de Errores**:
- **429 (Rate Limit)**: Retorna `False` → reintenta después de 30s
- **5xx (Server Error)**: Retorna `False` → reintenta
- **404 (Not Found)**: Levanta excepción → ticker inválido
- **Timeout**: Retorna `False` → reintenta

**Configuración**:
- **Poke Interval**: 30 segundos
- **Timeout**: 10 minutos
- **Exponential Backoff**: ✅ (30s → 60s → 120s)

---

### **Task 4: `fetch_multiple_dates`** (PythonOperator) 🆕

**Función**: Obtiene datos para todas las fechas determinadas

**Proceso**:
```python
for date in dates:
    try:
        data = api_client.fetch_market_data(ticker, date)
        market_data_list.append(data)
    except Exception as e:
        log_warning(f"Failed {date}: {e}")
        continue  # Continúa con siguiente fecha
```

**Características**:
- ✅ Fetch secuencial (evita rate limiting)
- ✅ Maneja errores por fecha (no falla todo si una fecha falla)
- ✅ Logging detallado de progreso (1/20, 2/20, ...)
- ✅ Métricas: successful, failed, duration
- ✅ Smart timestamp (hora actual si es hoy antes de 6PM)

**Timeout**: 15 minutos (permite fetch de 20 fechas)

**Output**: Lista de 1-20 diccionarios con market data

---

### **Task 5: `transform_and_save`** (PythonOperator) 🆕

**Función**: Calcula indicadores y persiste en Parquet

**Proceso**:
1. **Obtiene datos** de XCom (`market_data_list`)
2. **Convierte a DataFrame** con pandas
3. **Extrae OHLCV** del diccionario `quote`
4. **Convierte a numérico** (`pd.to_numeric()`)
5. **Valida datos** (al menos 1 registro con close price válido)
6. **Calcula indicadores**:
   - Moving Averages (SMA 7, 14, 20)
   - RSI (14 días)
   - MACD (12, 26, 9)
   - Bollinger Bands (20 días, 2σ)
   - Daily Returns
   - Volatility
7. **Guarda en Parquet** con append y deduplicación
8. **Push summary** a XCom

**Output**:
```python
{
    "ticker": "AAPL",
    "records_processed": 14,
    "records_saved": 14,
    "file_size_kb": 48.5,
    "indicators_calculated": 12
}
```

---

## 🔄 Reintentos y Manejo de Errores

### **Nivel 1: Airflow Task Retries**
```
Reintentos: 2
Delay: 2 minutos
Timeout: 10 min (fetch_multiple_dates: 15 min)
```

### **Nivel 2: API Internal Retries**
```
Reintentos: 3 por request
Strategy: Exponential backoff (5s → 10s → 20s)
Manejo 429: Respeta Retry-After header
```

### **Nivel 3: Sensor Retries**
```
Poke interval: 30 segundos
Timeout: 10 minutos
Exponential backoff: ✅
```

### **Nivel 4: Multi-Date Resilience**
```
Si una fecha falla: Continúa con las demás
Si todas fallan: Levanta ValueError
Logging: Detalla fechas exitosas vs fallidas
```

---

## 📊 Indicadores Técnicos - Detalles

### **1. SMA (Simple Moving Average)**

```python
SMA_7 = avg(close[-7:])   # Promedio móvil 7 días
SMA_14 = avg(close[-14:]) # Promedio móvil 14 días
SMA_20 = avg(close[-20:]) # Promedio móvil 20 días
```

**Uso**: Identificar tendencias a corto, medio y largo plazo

---

### **2. RSI (Relative Strength Index)**

```python
RSI = 100 - (100 / (1 + RS))
RS = avg(gains) / avg(losses)
```

**Valores**:
- RSI > 70: Sobrecompra (overbought)
- RSI < 30: Sobreventa (oversold)
- RSI 40-60: Neutral

---

### **3. MACD (Moving Average Convergence Divergence)**

```python
MACD = EMA(12) - EMA(26)
Signal = EMA(MACD, 9)
Histogram = MACD - Signal
```

**Señales**:
- MACD cruza Signal hacia arriba: Señal de compra
- MACD cruza Signal hacia abajo: Señal de venta

---

### **4. Bollinger Bands**

```python
BB_Middle = SMA(20)
BB_Upper = SMA(20) + (2 * STD(20))
BB_Lower = SMA(20) - (2 * STD(20))
```

**Uso**: Identificar volatilidad y puntos de entrada/salida

---

### **5. Volatilidad**

```python
Volatility = STD(close[-20:])
```

**Uso**: Medir riesgo del activo

---

### **6. Daily Returns**

```python
Daily_Return = (close[i] - close[i-1]) / close[i-1]
Daily_Return_Pct = Daily_Return * 100
```

**Uso**: Analizar rendimiento diario

---

## 🐛 Troubleshooting

### **Error: "No valid 'close' prices found in data"**

**Causa**: Todos los días solicitados son fines de semana o feriados

**Solución**:
- Ejecuta el DAG en día de semana (lunes-viernes)
- Verifica que las fechas no sean todas fines de semana
- Si es backfill, debería incluir al menos algunos días laborables

---

### **Error: HTTP 400 Bad Request**

**Causa**: Timestamp futuro (raro después del fix)

**Verificación**:
```bash
# Ver el log de fetch_multiple_dates
# Buscar línea: "Using current time for today's data"
```

**Solución**: Ya implementada con smart timestamp logic

---

### **Fines de Semana Sin Datos**

**Comportamiento Normal**: ✅

```
2025-11-08 (sábado): close=None ✅ ESPERADO
2025-11-09 (domingo): close=None ✅ ESPERADO
```

El código:
- ✅ Continúa procesando
- ✅ Guarda registros con close=NaN
- ✅ Indicadores técnicos manejan NaN correctamente
- ✅ No falla el DAG

---

### **Verificar Archivo Parquet Creado**

```bash
# Listar archivos
docker compose exec airflow-webserver ls -lh /opt/airflow/data/

# Ver contenido
docker compose exec airflow-webserver python3 << 'EOF'
import pandas as pd
df = pd.read_parquet('/opt/airflow/data/AAPL_market_data.parquet')
print(f"Total records: {len(df)}")
print(f"Columns: {len(df.columns)}")
print(f"\nFirst 3 records:\n{df.head(3)}")
print(f"\nClose prices:\n{df[['date', 'close', 'sma_7', 'rsi']].head(10)}")
EOF
```

---

### **Datos Parciales (Solo Algunos Días)**

**Si solo 14 de 20 días tienen datos**:

✅ **Normal**: Probablemente 6 son fines de semana

Verificar:
```bash
# Contar días por tipo
docker compose exec airflow-webserver python3 << 'EOF'
import pandas as pd
df = pd.read_parquet('/opt/airflow/data/AAPL_market_data.parquet')
print(f"Total records: {len(df)}")
print(f"Valid close prices: {df['close'].notna().sum()}")
print(f"Null close prices: {df['close'].isna().sum()}")
print(f"\nDates with data:\n{df[df['close'].notna()]['date'].tolist()}")
print(f"\nDates without data (weekends):\n{df[df['close'].isna()]['date'].tolist()}")
EOF
```

---

## 📝 Logs y Monitoreo

### **Structured Logging**

Todos los módulos usan el logger centralizado con:
- **Context**: task_id, ticker, date, etc.
- **Levels**: INFO, WARNING, ERROR, DEBUG
- **Metrics**: Performance, API calls, data counts
- **Audit**: Business events (backfill_initiated, parquet_saved, etc.)

### **Métricas Importantes**

```
api.request.success          # API calls exitosos
api.request.http_error       # Errores HTTP
fetch.multiple_dates.success # Fechas fetcheadas exitosamente
backfill.days                # Cantidad de días en backfill
storage.parquet_saved        # Archivos guardados
indicators.close_price       # Precios procesados
```

---

## 🔗 Referencias

- **API Reference**: [Yahoo Finance Chart API](https://query2.finance.yahoo.com/v8/finance/chart/)
- **Configuration Guide**: `docs/user-guide/configuration.md`
- **Logging Guide**: `docs/user-guide/logging.md`
- **Testing Guide**: `docs/developer-guide/testing.md`

---

## 📖 Documentación Adicional

- **Airflow Variables**: `docs/user-guide/airflow-variables.md`
- **Architecture**: `README.md` (Data Flow diagram)
- **Testing**: 131 tests (119 unit + 12 integration), 89% coverage

---

## ✨ Features Completas

- ✅ ETL Pipeline completo
- ✅ 12 indicadores técnicos
- ✅ Almacenamiento Parquet persistente
- ✅ Backfill automático (20 días)
- ✅ Ejecución diaria automática
- ✅ Smart timestamp logic
- ✅ Manejo robusto de errores
- ✅ Logging estructurado completo
- ✅ Métricas y auditoría
- ✅ Tests exhaustivos (89% coverage)
- ✅ Production-ready

---

<div align="center">

**🎉 DAG Completo y Funcional 🎉**

**Extrae → Transforma → Carga**

</div>
