# Get Market Data DAG

DAG para obtener datos de mercado desde Yahoo Finance API.

## 📋 Descripción

Este DAG obtiene datos históricos de precios de acciones desde la API pública de Yahoo Finance para un ticker y fecha específicos.

## 🎯 Funcionalidad

El DAG realiza las siguientes tareas:

1. **Validar Ticker**: Valida que el ticker proporcionado sea válido
2. **Obtener Datos**: Realiza petición HTTP a Yahoo Finance API
3. **Procesar Datos**: Procesa y muestra los datos obtenidos

## 🔧 Configuración

### Parámetros del DAG

Al ejecutar el DAG manualmente, puedes proporcionar:

- **ticker** (string): Símbolo del ticker (ej: AAPL, GOOGL, MSFT, TSLA)
  - Default: `AAPL`
  
- **date** (string): Fecha en formato YYYY-MM-DD
  - Default: Fecha actual

### Ejemplo de Configuración JSON

Cuando ejecutes el DAG desde la UI de Airflow, puedes proporcionar la siguiente configuración:

```json
{
    "ticker": "AAPL",
    "date": "2023-11-09"
}
```

Otros ejemplos:

```json
{
    "ticker": "GOOGL",
    "date": "2024-01-15"
}
```

```json
{
    "ticker": "TSLA",
    "date": "2024-03-20"
}
```

## 📊 Datos Obtenidos

El DAG obtiene la siguiente información:

### Información del Ticker
- Nombre completo de la empresa
- Símbolo del ticker
- Exchange (bolsa de valores)
- Tipo de instrumento
- Moneda

### Datos de Precio
- **Open**: Precio de apertura
- **High**: Precio máximo del día
- **Low**: Precio mínimo del día
- **Close**: Precio de cierre
- **Volume**: Volumen de transacciones

### Datos Adicionales
- Máximo de 52 semanas
- Mínimo de 52 semanas
- Precio actual de mercado

## 🚀 Cómo Ejecutar

### Desde la Interfaz Web de Airflow

1. Accede a http://localhost:8080
2. Busca el DAG `get_market_data`
3. Activa el DAG (toggle)
4. Haz clic en el botón "Trigger DAG" (▶️)
5. En el modal, proporciona la configuración JSON:
   ```json
   {
       "ticker": "AAPL",
       "date": "2023-11-09"
   }
   ```
6. Haz clic en "Trigger"

### Desde la CLI

```bash
# Ejecutar con parámetros por defecto
docker compose exec airflow-scheduler airflow dags trigger get_market_data

# Ejecutar con parámetros personalizados
docker compose exec airflow-scheduler airflow dags trigger get_market_data \
  --conf '{"ticker": "GOOGL", "date": "2024-01-15"}'
```

### Probar el DAG

```bash
# Probar el DAG completo
docker compose exec airflow-scheduler airflow dags test get_market_data 2025-11-11

# Probar una tarea específica
docker compose exec airflow-scheduler airflow tasks test get_market_data fetch_market_data 2025-11-11
```

## 📝 Estructura del DAG

```
validate_ticker → fetch_market_data → process_market_data
```

### Tareas

1. **validate_ticker**: Valida el ticker proporcionado
2. **fetch_market_data**: Obtiene los datos de Yahoo Finance API
3. **process_market_data**: Procesa y muestra los datos

## 🔄 Reintentos y Rate Limiting

El DAG incluye manejo robusto de errores:

### Reintentos a Nivel de Airflow
- **Reintentos**: 2 intentos
- **Retraso entre reintentos**: 2 minutos
- **Timeout de ejecución**: 10 minutos

### Reintentos a Nivel de API (interno)
- **Reintentos**: 3 intentos por request
- **Estrategia**: Exponential backoff (5s, 10s, 20s)
- **Manejo de 429**: Respeta el header `Retry-After` de la API

### Headers HTTP
El DAG incluye headers de navegador para evitar bloqueos:
- User-Agent simulando Chrome
- Accept headers apropiados

Esto asegura que fallos temporales de red o rate limiting no causen pérdida de datos.

## 📈 XCom

Los datos de mercado se almacenan en XCom con la key `market_data` y pueden ser accedidos por tareas posteriores.

## 🔗 API de Yahoo Finance

**Endpoint**: `https://query2.finance.yahoo.com/v8/finance/chart/{TICKER}`

**Parámetros**:
- `period1`: Timestamp Unix de fecha inicio
- `period2`: Timestamp Unix de fecha fin
- `interval`: Intervalo de datos (1d para diario)

**Ejemplo**:
```
https://query2.finance.yahoo.com/v8/finance/chart/AAPL?period1=1699549200&period2=1699549200&interval=1d
```

## 📊 Ejemplo de Salida

```
============================================================
DATOS DE MERCADO PROCESADOS
============================================================
Ticker: AAPL
Fecha: 2023-11-09
Empresa: Apple Inc.
Exchange: NMS
Moneda: USD
------------------------------------------------------------
PRECIOS:
  Open:   $182.96
  High:   $184.12
  Low:    $181.81
  Close:  $182.41
  Volume: 53,763,500
------------------------------------------------------------
52-Week High: $184.95
52-Week Low:  $124.17
============================================================
```

## 🛠️ Dependencias

Este DAG requiere las siguientes librerías de Python (ya incluidas en `requirements.txt`):

```
requests==2.31.0
pandas==2.1.4
```

## 🔮 Extensiones Futuras

Este DAG puede ser extendido para:

1. **Almacenamiento**: Guardar datos en PostgreSQL, S3, o data warehouse
2. **Múltiples Tickers**: Procesar múltiples tickers en paralelo
3. **Análisis**: Calcular indicadores técnicos (SMA, RSI, MACD)
4. **Alertas**: Enviar notificaciones cuando el precio cruza umbrales
5. **Histórico**: Obtener rangos de fechas en lugar de un solo día
6. **Visualización**: Generar gráficos y reportes

## ⚠️ Notas

- La API de Yahoo Finance es pública pero no oficial
- Los datos pueden tener un ligero retraso
- Algunos tickers pueden no estar disponibles
- Respeta los límites de rate limiting de la API

## 🐛 Troubleshooting

### El DAG no obtiene datos

1. Verifica que el ticker sea válido (debe existir en Yahoo Finance)
2. Verifica la fecha (debe ser un día de mercado abierto)
3. Revisa los logs de la tarea `fetch_market_data`

### Error de conexión

1. Verifica que el worker tenga acceso a internet
2. Revisa los logs para ver el error específico
3. El DAG reintentará automáticamente (3 intentos internos + 2 reintentos de Airflow)

### Error 429 (Too Many Requests)

Si recibes un error de rate limiting:

1. **El DAG maneja esto automáticamente** con exponential backoff
2. Espera entre reintentos: 5s → 10s → 20s
3. Respeta el header `Retry-After` de la API
4. Si persiste, espera unos minutos antes de ejecutar nuevamente

**Recomendaciones**:
- Evita ejecutar múltiples instancias del DAG simultáneamente
- Si necesitas obtener datos de múltiples tickers, espacía las ejecuciones
- Yahoo Finance tiene límites de rate por IP

### Ticker no encontrado

Algunos tickers pueden no estar disponibles o tener nombres diferentes en Yahoo Finance. Verifica el símbolo correcto en https://finance.yahoo.com/

