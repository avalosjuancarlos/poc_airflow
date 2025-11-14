# API Reference

Complete API documentation for all modules in the Market Data Pipeline.

---

## Table of Contents

- [Configuration Modules](#configuration-modules)
- [Utility Modules](#utility-modules)
- [Operator Modules](#operator-modules)
- [Sensor Modules](#sensor-modules)
- [Transformer Modules](#transformer-modules)
- [Storage Modules](#storage-modules)
- [Warehouse Modules](#warehouse-modules)

---

## Configuration Modules

### market_data.config.settings

Configuration management with triple-fallback system (Airflow Variable → Env Var → Default).

#### Constants

```python
DEFAULT_TICKERS[0]: str = "AAPL"
# Default stock ticker to fetch

API_BASE_URL: str = "https://query2.finance.yahoo.com/v8/finance/chart"
# Yahoo Finance API base URL

API_TIMEOUT: int = 30
# API request timeout in seconds

MAX_RETRIES: int = 3
# Maximum number of API retry attempts

RETRY_DELAY: int = 5
# Base delay between retries in seconds

SENSOR_POKE_INTERVAL: int = 30
# Sensor check interval in seconds

SENSOR_TIMEOUT: int = 600
# Sensor maximum wait time in seconds

SENSOR_EXPONENTIAL_BACKOFF: bool = True
# Enable exponential backoff for sensor retries

STORAGE_DIR: str = "/opt/airflow/data"
# Directory for Parquet file storage
```

#### Functions

##### `log_configuration()`

```python
def log_configuration() -> None
```

Logs current configuration settings for debugging.

**Usage**:
```python
from market_data.config import log_configuration

log_configuration()
```

**Output**:
```
=== MARKET DATA CONFIGURATION ===
Default Ticker: AAPL
API Base URL: https://query2.finance.yahoo.com/v8/finance/chart
Timeout: 30s
Max Retries: 3
...
```

---

### market_data.config.warehouse_config

Multi-environment data warehouse configuration.

#### Constants

```python
ENVIRONMENT: str = "development"
# Current environment: development | staging | production

LOAD_STRATEGY: str = "upsert"
# Warehouse load strategy: upsert | append | truncate_insert

TABLE_MARKET_DATA: str = "fact_market_data"
TABLE_TICKERS: str = "dim_tickers"
TABLE_DATES: str = "dim_dates"
# Warehouse table names

BATCH_SIZE: int = 1000
# Records per batch for warehouse loading

POOL_SIZE: int = 5
MAX_OVERFLOW: int = 10
POOL_TIMEOUT: int = 30
# Connection pool configuration
```

#### Functions

##### `get_warehouse_config()`

```python
def get_warehouse_config() -> Dict[str, Any]
```

Returns warehouse configuration based on current environment.

**Returns**:
```python
{
    "type": "postgresql" | "redshift",
    "host": str,
    "port": int,
    "database": str,
    "schema": str,
    "user": str,
    "password": str,
    "region": str  # Only for Redshift
}
```

**Example**:
```python
from market_data.config.warehouse_config import get_warehouse_config

config = get_warehouse_config()
print(f"Warehouse: {config['type']} at {config['host']}")
# Output: Warehouse: postgresql at warehouse-postgres
```

##### `get_connection_string()`

```python
def get_connection_string() -> str
```

Builds SQLAlchemy connection string for current environment.

**Returns**: SQLAlchemy connection string

**Examples**:
```python
# Development (PostgreSQL)
"postgresql://warehouse_user:pass@warehouse-postgres:5432/market_data_warehouse"

# Production (Redshift)
"redshift+psycopg2://user:pass@cluster.region.redshift.amazonaws.com:5439/market_data_prod"
```

##### `log_warehouse_configuration()`

```python
def log_warehouse_configuration() -> None
```

Logs current warehouse configuration (passwords masked).

---

## Utility Modules

### market_data.utils.api_client

Yahoo Finance API client with retry logic and rate limiting.

#### Class: `YahooFinanceClient`

```python
class YahooFinanceClient(base_url: str, timeout: int = 30)
```

**Parameters**:
- `base_url` (str): Yahoo Finance API base URL
- `timeout` (int, optional): Request timeout in seconds. Default: 30

**Example**:
```python
from market_data.utils.api_client import YahooFinanceClient

client = YahooFinanceClient(
    base_url="https://query2.finance.yahoo.com/v8/finance/chart",
    timeout=30
)
```

##### Method: `fetch_market_data()`

```python
def fetch_market_data(
    ticker: str,
    date: str,
    max_retries: int = 3,
    retry_delay: int = 5
) -> Optional[Dict[str, Any]]
```

Fetches market data for a specific ticker and date.

**Parameters**:
- `ticker` (str): Stock ticker symbol (e.g., "AAPL")
- `date` (str): Date in YYYY-MM-DD format
- `max_retries` (int, optional): Maximum retry attempts. Default: 3
- `retry_delay` (int, optional): Base retry delay in seconds. Default: 5

**Returns**: 
- `Dict[str, Any]`: Market data with OHLCV + metadata
- `None`: If fetch fails after all retries

**Raises**:
- `ValueError`: Invalid ticker or date format
- `requests.exceptions.RequestException`: Network errors

**Example**:
```python
client = YahooFinanceClient(base_url="...")
data = client.fetch_market_data("AAPL", "2025-11-12")

if data:
    print(f"Close: ${data['close']}")
    print(f"Volume: {data['volume']}")
```

**Response Structure**:
```python
{
    "ticker": "AAPL",
    "date": "2025-11-12",
    "timestamp": 1731441600,
    "open": 259.45,
    "high": 260.61,
    "low": 258.32,
    "close": 259.57,
    "volume": 54123456,
    "currency": "USD",
    "exchange_name": "NMS",
    "instrument_type": "EQUITY",
    "regular_market_price": 259.57,
    "fifty_two_week_high": 277.32,
    "fifty_two_week_low": 164.08,
    "quote": {...},  # Raw quote data
    "metadata": {...}  # Raw metadata
}
```

##### Method: `check_availability()`

```python
def check_availability(ticker: str = "AAPL") -> bool
```

Checks if Yahoo Finance API is responsive.

**Parameters**:
- `ticker` (str, optional): Ticker to test. Default: "AAPL"

**Returns**: `True` if API is available, `False` otherwise

**Example**:
```python
if client.check_availability():
    print("API is ready")
else:
    print("API is down or rate limited")
```

---

### market_data.utils.validators

Input validation utilities.

#### Functions

##### `validate_ticker_format()`

```python
def validate_ticker_format(ticker: str) -> str
```

Validates ticker symbol format.

**Parameters**:
- `ticker` (str): Stock ticker symbol

**Returns**: `str` - Validated ticker (uppercase)

**Raises**:
- `ValueError`: If ticker is empty, invalid format, or too long

**Rules**:
- 1-5 uppercase letters
- Allows numbers and dots (e.g., "BRK.A")
- Max length: 10 characters

**Examples**:
```python
from market_data.utils.validators import validate_ticker_format

# Valid
validate_ticker_format("AAPL")    # Returns: "AAPL"
validate_ticker_format("aapl")    # Returns: "AAPL"
validate_ticker_format("BRK.A")   # Returns: "BRK.A"

# Invalid
validate_ticker_format("")        # Raises: ValueError
validate_ticker_format("ABC123")  # Raises: ValueError
validate_ticker_format("A" * 20)  # Raises: ValueError
```

##### `validate_date_format()`

```python
def validate_date_format(date_str: str) -> str
```

Validates date string format (YYYY-MM-DD).

**Parameters**:
- `date_str` (str): Date string

**Returns**: `str` - Validated date

**Raises**:
- `ValueError`: If date format is invalid

**Example**:
```python
from market_data.utils.validators import validate_date_format

# Valid
validate_date_format("2025-11-12")  # Returns: "2025-11-12"

# Invalid
validate_date_format("11/12/2025")  # Raises: ValueError
validate_date_format("2025-13-01")  # Raises: ValueError
```

---

### market_data.utils.logger

Centralized logging system with structured logging and monitoring integration.

#### Class: `MarketDataLogger`

```python
class MarketDataLogger(name: str, config: Optional[Dict] = None)
```

**Parameters**:
- `name` (str): Logger name (usually `__name__`)
- `config` (dict, optional): Logging configuration

**Example**:
```python
from market_data.utils.logger import MarketDataLogger

logger = MarketDataLogger(__name__)
```

##### Method: `info()`, `debug()`, `warning()`, `error()`

Standard logging methods with context support.

```python
def info(message: str, extra: Optional[Dict] = None) -> None
def debug(message: str, extra: Optional[Dict] = None) -> None
def warning(message: str, extra: Optional[Dict] = None) -> None
def error(message: str, extra: Optional[Dict] = None, exc_info: bool = False) -> None
```

**Example**:
```python
logger.info("Fetching data", extra={"ticker": "AAPL", "date": "2025-11-12"})
logger.error("API failed", extra={"status_code": 500}, exc_info=True)
```

##### Method: `set_context()` / `clear_context()`

```python
def set_context(context: Dict[str, Any]) -> None
def clear_context() -> None
```

Set contextual information for all subsequent logs.

**Example**:
```python
logger.set_context({"dag_run_id": "123", "task_id": "fetch_data"})
logger.info("Processing")  # Includes context automatically
logger.clear_context()
```

##### Method: `metric()`

```python
def metric(name: str, value: float, tags: Optional[Dict] = None) -> None
```

Log metrics for monitoring.

**Example**:
```python
logger.metric("api.response_time", 1.234, {"endpoint": "/chart"})
logger.metric("records.processed", 150, {"ticker": "AAPL"})
```

##### Method: `audit()`

```python
def audit(action: str, details: Dict[str, Any]) -> None
```

Log audit events for compliance.

**Example**:
```python
logger.audit("data_fetched", {
    "user": "airflow",
    "ticker": "AAPL",
    "date": "2025-11-12",
    "records": 15
})
```

##### Context Manager: `execution_timer()`

```python
@contextmanager
def execution_timer(operation: str) -> Iterator[None]
```

Time code execution and log duration.

**Example**:
```python
with logger.execution_timer("fetch_data"):
    data = fetch_from_api()
# Logs: "fetch_data completed in 1.234s"
```

#### Decorators

##### `@log_execution()`

```python
@log_execution(logger: MarketDataLogger)
def my_function(**kwargs):
    pass
```

Automatically logs function execution start, end, duration.

**Example**:
```python
from market_data.utils.logger import log_execution, get_logger

logger = get_logger(__name__)

@log_execution(logger)
def fetch_data(ticker: str, **kwargs):
    # Your code
    return data
```

**Output**:
```
INFO - Executing fetch_data
INFO - fetch_data completed successfully in 1.234s
```

##### `@log_errors()`

```python
@log_errors(logger: MarketDataLogger)
def my_function(**kwargs):
    pass
```

Automatically logs and re-raises exceptions.

**Example**:
```python
@log_errors(logger)
def risky_operation():
    raise ValueError("Something went wrong")
```

**Output**:
```
ERROR - Error in risky_operation: Something went wrong
(exception is re-raised)
```

#### Helper Functions

##### `get_logger()`

```python
def get_logger(name: str) -> MarketDataLogger
```

Factory function to create logger instances.

**Example**:
```python
from market_data.utils import get_logger

logger = get_logger(__name__)
logger.info("Application started")
```

---

## Operator Modules

### market_data.operators.market_data_operators

Task operators for market data DAG.

#### Functions

##### `validate_ticker()`

```python
def validate_ticker(**context) -> str
```

Validates and returns ticker from DAG params.

**Context Keys Used**:
- `params['ticker']` or `dag_run.conf.get('ticker')`

**Returns**: `str` - Validated ticker (uppercase)

**XCom Push**: Validated ticker (key: `return_value`)

**Example**:
```python
from airflow.operators.python import PythonOperator

validate_task = PythonOperator(
    task_id='validate_ticker',
    python_callable=validate_ticker,
)
```

##### `fetch_market_data()`

```python
def fetch_market_data(**context) -> Dict[str, Any]
```

Fetches market data from Yahoo Finance API.

**Context Keys Used**:
- `ti` (TaskInstance) - For XCom pull
- `params['ticker']` or XCom from `validate_ticker`
- `params['date']` or execution_date

**Returns**: `Dict` - Market data

**XCom Push**: Market data dictionary

**Example**:
```python
fetch_task = PythonOperator(
    task_id='fetch_market_data',
    python_callable=fetch_market_data,
)
```

##### `process_market_data()`

```python
def process_market_data(**context) -> None
```

Processes and logs fetched market data.

**Context Keys Used**:
- `ti` - For XCom pull from `fetch_market_data`

**Example**:
```python
process_task = PythonOperator(
    task_id='process_market_data',
    python_callable=process_market_data,
)
```

---

### market_data.operators.transform_operators

Data transformation and backfill operators.

#### Functions

##### `check_and_determine_dates()`

```python
def check_and_determine_dates(**context) -> List[str]
```

Determines which dates to fetch (backfill or single date).

**Logic**:
- If Parquet exists: Return [today]
- If Parquet missing: Return last 20 trading days

**Context Keys Used**:
- `ti` - For XCom pull (ticker)
- `execution_date`

**Returns**: `List[str]` - Dates in YYYY-MM-DD format

**XCom Push**: List of dates

**Example**:
```python
determine_dates_task = PythonOperator(
    task_id='determine_dates',
    python_callable=check_and_determine_dates,
)
```

##### `fetch_multiple_dates()`

```python
def fetch_multiple_dates(**context) -> List[Dict[str, Any]]
```

Fetches market data for multiple dates.

**Context Keys Used**:
- `ti` - For XCom pull (ticker, dates)

**Returns**: `List[Dict]` - Market data for all dates

**XCom Push**: List of market data dictionaries

**Example**:
```python
fetch_task = PythonOperator(
    task_id='fetch_data',
    python_callable=fetch_multiple_dates,
    retries=3,
)
```

##### `transform_and_save()`

```python
def transform_and_save(**context) -> Dict[str, Any]
```

Calculates technical indicators and saves to Parquet.

**Context Keys Used**:
- `ti` - For XCom pull (ticker, market_data)

**Returns**: 
```python
{
    "records_saved": int,
    "file_path": str,
    "indicators_calculated": List[str]
}
```

**XCom Push**: Save result dictionary

**Example**:
```python
transform_task = PythonOperator(
    task_id='transform_and_save',
    python_callable=transform_and_save,
    retries=2,
)
```

---

### market_data.operators.warehouse_operators

Data warehouse loading operator.

#### Functions

##### `load_to_warehouse()`

```python
def load_to_warehouse(**context) -> Dict[str, Any]
```

Loads data from Parquet to warehouse.

**Context Keys Used**:
- `ti` - For XCom pull (ticker)

**Returns**:
```python
{
    "records_loaded": int,
    "total_in_warehouse": int,
    "warehouse_type": str,
    "load_strategy": str,
    "execution_time_seconds": float
}
```

**Example**:
```python
load_task = PythonOperator(
    task_id='load_to_warehouse',
    python_callable=load_to_warehouse,
    retries=2,
)
```

---

## Sensor Modules

### market_data.sensors.api_sensor

Custom sensor for API availability checking.

#### Functions

##### `check_api_availability()`

```python
def check_api_availability(**context) -> bool
```

Checks if Yahoo Finance API is responsive.

**Context Keys Used**:
- `params['ticker']` or XCom from `validate_ticker`

**Returns**: 
- `True`: API is available
- `False`: API is down or rate limited (sensor will retry)

**Example**:
```python
from airflow.sensors.python import PythonSensor

api_sensor = PythonSensor(
    task_id='check_api_availability',
    python_callable=check_api_availability,
    poke_interval=30,
    timeout=600,
    mode='reschedule',
)
```

**Retry Logic**:
- Pokes every 30 seconds (configurable)
- Exponential backoff for 429 errors
- Respects `Retry-After` header

---

## Transformer Modules

### market_data.transformers.technical_indicators

Technical indicator calculations using Pandas.

#### Functions

##### `calculate_technical_indicators()`

```python
def calculate_technical_indicators(df: pd.DataFrame) -> pd.DataFrame
```

Calculates 12 technical indicators on market data.

**Parameters**:
- `df` (pd.DataFrame): DataFrame with columns: ticker, date, open, high, low, close, volume

**Returns**: `pd.DataFrame` - Original data + 12 new indicator columns

**New Columns**:
- `sma_7`, `sma_14`, `sma_30`: Simple Moving Averages
- `rsi`: Relative Strength Index (14 days)
- `macd`, `macd_signal`, `macd_histogram`: MACD indicators
- `bb_upper`, `bb_middle`, `bb_lower`: Bollinger Bands
- `daily_return`: Daily percentage change
- `volatility_20d`: 20-day rolling volatility

**Example**:
```python
from market_data.transformers.technical_indicators import calculate_technical_indicators
import pandas as pd

# Sample data
df = pd.DataFrame({
    'ticker': ['AAPL'] * 20,
    'date': pd.date_range('2025-10-01', periods=20),
    'close': [150.0, 151.0, 152.0, ...],
    'open': [149.0, 150.5, 151.5, ...],
    'high': [152.0, 153.0, 154.0, ...],
    'low': [148.0, 149.0, 150.0, ...],
    'volume': [1000000, 1100000, 1200000, ...]
})

# Calculate indicators
df_enriched = calculate_technical_indicators(df)

print(df_enriched[['date', 'close', 'sma_7', 'rsi', 'macd']])
```

**Output**:
```
        date   close   sma_7     rsi      macd
0  2025-10-01  150.0     NaN     NaN       NaN
1  2025-10-02  151.0     NaN     NaN       NaN
...
7  2025-10-08  157.0  153.43     NaN       NaN
14 2025-10-15  164.0  160.29   68.42     1.23
```

---

## Storage Modules

### market_data.storage.parquet_storage

Parquet file operations for market data persistence.

#### Functions

##### `get_parquet_path()`

```python
def get_parquet_path(ticker: str, data_dir: Optional[str] = None) -> str
```

Generates Parquet file path for ticker.

**Parameters**:
- `ticker` (str): Stock ticker symbol
- `data_dir` (str, optional): Custom directory. Default: from env `MARKET_DATA_STORAGE_DIR`

**Returns**: `str` - Full path to Parquet file

**Example**:
```python
from market_data.storage.parquet_storage import get_parquet_path

path = get_parquet_path("AAPL")
# Returns: "/opt/airflow/data/AAPL_market_data.parquet"
```

##### `check_parquet_exists()`

```python
def check_parquet_exists(ticker: str) -> bool
```

Checks if Parquet file exists for ticker.

**Parameters**:
- `ticker` (str): Stock ticker symbol

**Returns**: `bool` - True if file exists

**Example**:
```python
if check_parquet_exists("AAPL"):
    print("Parquet file found, will fetch single day")
else:
    print("No Parquet, will backfill 20 days")
```

##### `save_to_parquet()`

```python
def save_to_parquet(df: pd.DataFrame, ticker: str) -> str
```

Saves DataFrame to Parquet with automatic deduplication.

**Parameters**:
- `df` (pd.DataFrame): Data to save
- `ticker` (str): Stock ticker symbol

**Returns**: `str` - Path to saved file

**Behavior**:
- Creates directory if not exists
- Appends to existing file
- Removes duplicates by (ticker, date)
- Sorts by date descending

**Example**:
```python
from market_data.storage.parquet_storage import save_to_parquet
import pandas as pd

df = pd.DataFrame({...})
path = save_to_parquet(df, "AAPL")
print(f"Saved to: {path}")
```

##### `load_from_parquet()`

```python
def load_from_parquet(ticker: str) -> pd.DataFrame
```

Loads data from Parquet file.

**Parameters**:
- `ticker` (str): Stock ticker symbol

**Returns**: `pd.DataFrame` - Market data with indicators

**Raises**:
- `FileNotFoundError`: If Parquet doesn't exist

**Example**:
```python
df = load_from_parquet("AAPL")
print(f"Loaded {len(df)} records")
print(df[['date', 'close', 'sma_7', 'rsi']].head())
```

---

## Warehouse Modules

### market_data.warehouse.connection

Database connection management with pooling.

#### Class: `WarehouseConnection`

```python
class WarehouseConnection(config: Dict[str, Any])
```

**Parameters**:
- `config` (dict): Warehouse configuration from `get_warehouse_config()`

**Example**:
```python
from market_data.warehouse.connection import WarehouseConnection
from market_data.config.warehouse_config import get_warehouse_config

config = get_warehouse_config()
connection = WarehouseConnection(config)
```

##### Method: `get_connection()`

```python
@contextmanager
def get_connection() -> Iterator[Connection]
```

Context manager for database connections with automatic commit/rollback.

**Example**:
```python
with connection.get_connection() as conn:
    conn.execute("INSERT INTO ...")
    # Automatic COMMIT on success
    # Automatic ROLLBACK on exception
```

##### Method: `dispose()`

```python
def dispose() -> None
```

Dispose of connection pool and release resources.

**Example**:
```python
connection.dispose()
```

#### Helper Functions

##### `get_warehouse_connection()`

```python
def get_warehouse_connection(config: Optional[Dict] = None) -> WarehouseConnection
```

Factory function to create warehouse connection.

**Parameters**:
- `config` (dict, optional): Custom config. Default: from `get_warehouse_config()`

**Returns**: `WarehouseConnection` instance

**Example**:
```python
from market_data.warehouse import get_warehouse_connection

connection = get_warehouse_connection()
with connection.get_connection() as conn:
    result = conn.execute("SELECT COUNT(*) FROM fact_market_data")
```

---

### market_data.warehouse.loader

Data warehouse loading with multiple strategies.

#### Class: `WarehouseLoader`

```python
class WarehouseLoader()
```

**Example**:
```python
from market_data.warehouse.loader import WarehouseLoader

loader = WarehouseLoader()
```

##### Method: `load_from_parquet()`

```python
def load_from_parquet(ticker: str) -> Dict[str, Any]
```

Loads data from Parquet file to warehouse.

**Parameters**:
- `ticker` (str): Stock ticker symbol

**Returns**:
```python
{
    "records_loaded": int,
    "total_in_warehouse": int,
    "warehouse_type": str,
    "load_strategy": str,
    "execution_time_seconds": float
}
```

**Example**:
```python
loader = WarehouseLoader()
result = loader.load_from_parquet("AAPL")
print(f"Loaded {result['records_loaded']} records")
print(f"Total in warehouse: {result['total_in_warehouse']}")
```

##### Method: `create_tables()`

```python
def create_tables(conn: Connection) -> None
```

Creates warehouse tables if they don't exist.

**Parameters**:
- `conn` (Connection): SQLAlchemy connection

**Tables Created**:
- `fact_market_data` - Main data table with OHLCV + indicators
- Indexes on (ticker, date)

**Example**:
```python
with loader.connection.get_connection() as conn:
    loader.create_tables(conn)
```

#### Helper Functions

##### `load_parquet_to_warehouse()`

```python
def load_parquet_to_warehouse(ticker: str) -> Dict[str, Any]
```

Convenience function to load data to warehouse.

**Parameters**:
- `ticker` (str): Stock ticker symbol

**Returns**: Load result dictionary

**Example**:
```python
from market_data.warehouse import load_parquet_to_warehouse

result = load_parquet_to_warehouse("AAPL")
```

---

## Usage Examples

### Complete ETL Flow

```python
from market_data.utils import get_logger, YahooFinanceClient
from market_data.utils.validators import validate_ticker_format
from market_data.transformers.technical_indicators import calculate_technical_indicators
from market_data.storage.parquet_storage import save_to_parquet, load_from_parquet
from market_data.warehouse import load_parquet_to_warehouse
import pandas as pd

# Setup
logger = get_logger(__name__)
client = YahooFinanceClient(base_url="https://query2.finance.yahoo.com/v8/finance/chart")

# 1. Validate ticker
ticker = validate_ticker_format("AAPL")
logger.info(f"Validated ticker: {ticker}")

# 2. Fetch data
data = client.fetch_market_data(ticker, "2025-11-12")
if not data:
    raise ValueError("No data fetched")

# 3. Transform
df = pd.DataFrame([data])
df_enriched = calculate_technical_indicators(df)
logger.info(f"Calculated {12} indicators")

# 4. Save to Parquet
path = save_to_parquet(df_enriched, ticker)
logger.info(f"Saved to: {path}")

# 5. Load to Warehouse
result = load_parquet_to_warehouse(ticker)
logger.info(f"Loaded {result['records_loaded']} records to warehouse")
```

### Custom Logging

```python
from market_data.utils import get_logger

logger = get_logger(__name__)

# Basic logging
logger.info("Processing started")
logger.debug("Debug details", extra={"ticker": "AAPL"})

# Context
logger.set_context({"dag_run_id": "123", "user": "airflow"})
logger.info("This log includes context")
logger.clear_context()

# Metrics
logger.metric("api.calls", 15, {"endpoint": "/chart"})

# Audit
logger.audit("data_loaded", {"ticker": "AAPL", "records": 100})

# Timing
with logger.execution_timer("expensive_operation"):
    # Your code here
    pass
```

### Decorators

```python
from market_data.utils.logger import get_logger, log_execution, log_errors

logger = get_logger(__name__)

@log_execution(logger)
@log_errors(logger)
def my_airflow_task(**context):
    """Task with automatic logging"""
    ticker = context['ti'].xcom_pull(task_ids='validate_ticker')
    
    # Your logic
    result = process_data(ticker)
    
    return result
```

---

## Type Definitions

### Common Types

```python
from typing import Dict, List, Optional, Any
from datetime import datetime
import pandas as pd

# Market data dictionary
MarketDataDict = Dict[str, Any]  # Contains: ticker, date, OHLCV, metadata

# Warehouse config
WarehouseConfig = Dict[str, Any]  # Contains: type, host, port, database, user, password

# Load result
LoadResult = Dict[str, Any]  # Contains: records_loaded, total_in_warehouse, etc.
```

---

## Error Handling

### Common Exceptions

```python
# Validation errors
ValueError: "Ticker cannot be empty"
ValueError: "Invalid date format"

# API errors
requests.exceptions.HTTPError: "429 Too Many Requests"
requests.exceptions.Timeout: "Request timeout"
requests.exceptions.ConnectionError: "Connection failed"

# Data errors
pd.errors.EmptyDataError: "No data to process"
FileNotFoundError: "Parquet file not found"

# Warehouse errors
sqlalchemy.exc.OperationalError: "could not connect to server"
psycopg2.errors.UniqueViolation: "duplicate key value"
```

### Error Handling Pattern

```python
from market_data.utils import get_logger

logger = get_logger(__name__)

try:
    data = fetch_data()
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 429:
        logger.warning("Rate limited, will retry")
        raise  # Let Airflow retry
    else:
        logger.error(f"HTTP error: {e}", exc_info=True)
        raise
except Exception as e:
    logger.error(f"Unexpected error: {e}", exc_info=True)
    raise
```

---

## Configuration Examples

### Triple-Fallback Pattern

```python
from airflow.models import Variable
import os

# Priority: Airflow Variable > Env Var > Default
ticker = Variable.get(
    "market_data_default_tickers",
    default_var=os.environ.get("MARKET_DATA_DEFAULT_TICKERS[0]S", "AAPL")
)

timeout = int(Variable.get(
    "market_data_api_timeout",
    default_var=os.environ.get("MARKET_DATA_API_TIMEOUT", "30")
))
```

### Environment Detection

```python
from market_data.config.warehouse_config import get_warehouse_config

config = get_warehouse_config()

if config['type'] == 'postgresql':
    print("Using PostgreSQL (development)")
elif config['type'] == 'redshift':
    print("Using Redshift (staging/production)")
```

---

## Related Documentation

- [Architecture Overview](../architecture/overview.md)
- [Testing Guide](testing.md)
- [Code Style Guide](code-style.md)
- [User Guide - Configuration](../user-guide/configuration.md)

---

**Last Updated**: 2025-11-12  
**Version**: 1.0.0  
**Coverage**: All public APIs documented

