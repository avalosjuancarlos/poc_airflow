# Centralized Logging System Guide

## Overview

The market_data DAG uses a centralized logging system that provides:

- **Structured logging** with contextual information
- **Automatic function execution logging** via decorators
- **Metrics tracking** for monitoring and alerting
- **Audit logging** for compliance and tracking
- **Integration support** for Sentry and Datadog
- **Environment-based log levels**

## Quick Start

### Basic Usage

```python
from market_data.utils import get_logger

# Get a logger instance
logger = get_logger(__name__)

# Log messages
logger.info("Processing started")
logger.warning("Unusual condition detected")
logger.error("Failed to process data", exc_info=True)
```

### Using Decorators

```python
from market_data.utils import log_execution, log_errors

@log_execution()
def fetch_data():
    """This function will automatically log execution time and status"""
    return data

@log_errors(reraise=True)
def risky_operation():
    """This function will log any errors that occur"""
    pass
```

### Adding Context

```python
from market_data.utils import get_logger

logger = get_logger(__name__)

# Set context for all log messages
logger.set_context(
    task_id="fetch_market_data",
    execution_date="2023-11-09",
    ticker="AAPL"
)

# All subsequent logs will include this context
logger.info("Starting data fetch")  
# Output: [task_id=fetch_market_data | execution_date=2023-11-09 | ticker=AAPL] Starting data fetch
```

## Configuration

### Environment Variables

#### Log Levels

Set the logging level based on environment:

```bash
# Development: DEBUG level
ENVIRONMENT=development

# Staging: INFO level  
ENVIRONMENT=staging

# Production: WARNING level
ENVIRONMENT=production

# Or set explicitly
AIRFLOW__LOGGING__LEVEL=INFO
```

#### Log Format

Enable JSON formatting for log aggregation tools:

```bash
# Standard format (default)
AIRFLOW__LOGGING__JSON_FORMAT=false

# JSON format
AIRFLOW__LOGGING__JSON_FORMAT=true
```

### Adding External Monitoring Integrations

The logging system is designed to be extensible. You can add external monitoring tools like Sentry or Datadog by extending the logger module.

#### Adding Sentry Integration

To add Sentry error tracking:

1. **Install Sentry SDK**:
   ```bash
   pip install sentry-sdk==1.40.0
   ```

2. **Extend `dags/market_data/utils/logger.py`**:
   ```python
   # Add at top of file
   try:
       import sentry_sdk
       from sentry_sdk.integrations.logging import LoggingIntegration
       SENTRY_AVAILABLE = True
   except ImportError:
       SENTRY_AVAILABLE = False

   # In MarketDataLogger.__init__(), add:
   if SENTRY_AVAILABLE and os.environ.get("SENTRY_DSN"):
       sentry_logging = LoggingIntegration(
           level=logging.INFO, event_level=logging.ERROR
       )
       sentry_sdk.init(
           dsn=os.environ.get("SENTRY_DSN"),
           environment=os.environ.get("ENVIRONMENT", "development"),
           traces_sample_rate=float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
           integrations=[sentry_logging],
       )

   # In error() and exception() methods, add:
   if SENTRY_AVAILABLE:
       sentry_sdk.capture_message(message, level="error")  # or capture_exception()
   ```

3. **Configure environment variables**:
   ```bash
   SENTRY_DSN=https://your-key@sentry.io/project-id
   SENTRY_TRACES_SAMPLE_RATE=0.1
   SENTRY_SEND_PII=false
   ```

#### Adding Datadog Integration

To add Datadog APM:

1. **Install Datadog tracer**:
   ```bash
   pip install ddtrace==2.3.0
   ```

2. **Extend `dags/market_data/utils/logger.py`**:
   ```python
   # Add at top of file
   try:
       import ddtrace
       DATADOG_AVAILABLE = True
   except ImportError:
       DATADOG_AVAILABLE = False

   # In MarketDataLogger.__init__(), add:
   if DATADOG_AVAILABLE and os.environ.get("DD_API_KEY"):
       ddtrace.patch_all()  # Auto-instrument common libraries
   ```

3. **Configure environment variables**:
   ```bash
   DD_API_KEY=your-datadog-api-key
   DD_SITE=datadoghq.com
   DD_SERVICE=airflow-market-data
   DD_ENV=production
   ```

**Note**: See [Sentry Python SDK](https://docs.sentry.io/platforms/python/) and [Datadog APM](https://docs.datadoghq.com/tracing/setup_overview/setup/python/) for complete integration guides.

## Features

### 1. Structured Logging

All log messages include contextual information:

```python
logger.info(
    "Market data fetched successfully",
    extra={
        "ticker": "AAPL",
        "date": "2023-11-09",
        "close_price": 150.25,
        "volume": 50000000
    }
)
```

### 2. Execution Timing

Track function execution times automatically:

```python
# Using decorator
@log_execution()
def slow_operation():
    time.sleep(2)
    return "done"

# Using context manager
with logger.execution_timer("database_query"):
    result = db.query("SELECT * FROM large_table")
```

### 3. Metrics Logging

Log metrics for monitoring and alerting:

```python
# Log a metric with tags
logger.metric(
    "api.response_time",
    value=1.234,
    tags={"endpoint": "/market-data", "status": "success"}
)

# Log business metrics
logger.metric(
    "market.close_price",
    value=150.25,
    tags={"ticker": "AAPL", "date": "2023-11-09"}
)
```

### 4. Audit Logging

Track important actions for compliance:

```python
logger.audit(
    "market_data_fetched",
    details={
        "ticker": "AAPL",
        "date": "2023-11-09",
        "user": "airflow",
        "success": True
    }
)
```

### 5. Error Handling

Enhanced error logging with context:

```python
try:
    risky_operation()
except Exception as e:
    logger.exception(
        "Operation failed",
        extra={"operation": "fetch_data", "ticker": "AAPL"}
    )
    logger.error("Critical failure")
```

## Best Practices

### 1. Use Appropriate Log Levels

```python
# DEBUG: Detailed diagnostic information
logger.debug("Variable values", extra={"var1": value1})

# INFO: General informational messages
logger.info("Processing completed successfully")

# WARNING: Warning messages for unusual situations
logger.warning("Rate limit approaching")

# ERROR: Error messages for failures
logger.error("Failed to fetch data", exc_info=True)
```

### 2. Add Context to Logs

Always include relevant context:

```python
# Bad
logger.info("Data fetched")

# Good
logger.info(
    "Market data fetched successfully",
    extra={"ticker": "AAPL", "records": 100}
)
```

### 3. Use Decorators for Functions

Automatically log function execution:

```python
from market_data.utils import log_execution

@log_execution()
def fetch_market_data(ticker, date):
    # Function will automatically log:
    # - Start of execution
    # - Execution time
    # - Success/failure status
    return data
```

### 4. Log Metrics for Monitoring

Track important metrics:

```python
# API performance
logger.metric("api.response_time", elapsed_time)

# Business metrics
logger.metric("market.daily_volume", volume)

# Error rates
logger.metric("api.error_rate", error_count)
```

### 5. Use Audit Logs for Important Actions

Track critical operations:

```python
logger.audit(
    "configuration_changed",
    details={
        "user": user_id,
        "setting": setting_name,
        "old_value": old_val,
        "new_value": new_val
    }
)
```

## Integration with Airflow

### Setting DAG Context

In your DAG tasks, set context for all loggers:

```python
from market_data.utils.logger import set_dag_context

def my_task(**context):
    # Set context for all loggers
    set_dag_context(
        task_id=context['task_instance'].task_id,
        execution_date=str(context['execution_date']),
        dag_id=context['dag'].dag_id
    )
    
    # Now all logs will include this context
    logger.info("Task started")
```

### Example DAG Task

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from market_data.utils import get_logger, log_execution

logger = get_logger(__name__)

@log_execution()
def fetch_data_task(**context):
    # Set context
    logger.set_context(
        task_id=context['task_instance'].task_id,
        execution_date=str(context['execution_date'])
    )
    
    # Log with context
    logger.info("Fetching market data")
    
    # Your code here
    data = fetch_data()
    
    # Log metrics
    logger.metric("records.fetched", len(data))
    
    # Audit log
    logger.audit("data_fetched", {"records": len(data)})
    
    return data

with DAG('market_data', ...):
    fetch_task = PythonOperator(
        task_id='fetch_data',
        python_callable=fetch_data_task,
        provide_context=True
    )
```

## Troubleshooting

### Logs Not Appearing

1. Check log level:
   ```bash
   # View current level
   echo $AIRFLOW__LOGGING__LEVEL
   
   # Set to DEBUG for maximum verbosity
   export AIRFLOW__LOGGING__LEVEL=DEBUG
   ```

2. Verify logger initialization:
   ```python
   from market_data.utils import get_logger
   logger = get_logger(__name__)
   logger.info("Test message")
   ```

### Performance Issues

If logging is impacting performance:

1. Increase log level in production:
   ```bash
   ENVIRONMENT=production  # Sets WARNING level
   ```

2. Use async logging (if available):
   ```python
   # Configure async handlers in logging config
   ```

3. Reduce log verbosity for high-frequency operations:
   ```python
   # Use DEBUG only when needed
   if logger.isEnabledFor(logging.DEBUG):
       logger.debug("Detailed diagnostic info")
   ```

## Examples

### Complete Example

```python
from market_data.utils import get_logger, log_execution
from market_data.config import DEFAULT_TICKERS

logger = get_logger(__name__)

@log_execution()
def process_market_data(tickers=DEFAULT_TICKERS, **context):
    """Process market data with comprehensive logging"""
    
    for ticker in tickers:
        logger.set_context(
            task_id=context.get('task_instance').task_id,
            ticker=ticker
        )
        
        logger.info(f"Starting processing for {ticker}")
        
        try:
            with logger.execution_timer("fetch_data"):
                data = fetch_data(ticker)
            
            logger.metric("data.records", len(data), {"ticker": ticker})
            
            result = process_data(data)
            
            logger.audit(
                "processing_completed",
                {
                    "ticker": ticker,
                    "records_processed": len(data),
                    "success": True
                }
            )
            
            logger.info(f"Processing completed successfully for {ticker}")
        except Exception as e:
            logger.exception(
                f"Processing failed for {ticker}",
                extra={"ticker": ticker, "error": str(e)}
            )
            logger.error("Critical processing failure")
            raise
        finally:
            logger.clear_context()
```

## Additional Resources

- [Airflow Logging Documentation](https://airflow.apache.org/docs/apache-airflow/stable/logging-monitoring/logging-tasks.html)
- [Python Logging Best Practices](https://docs.python.org/3/howto/logging.html)
- [Sentry Python SDK](https://docs.sentry.io/platforms/python/) - For adding error tracking
- [Datadog APM for Python](https://docs.datadoghq.com/tracing/setup_overview/setup/python/) - For adding APM and metrics

