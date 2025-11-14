# Environment Variables Reference

Complete reference for all environment variables used in the project.

---

## Table of Contents

- [Core Airflow](#core-airflow)
- [Market Data Configuration](#market-data-configuration)
- [Logging Configuration](#logging-configuration)
- [Data Warehouse Configuration](#data-warehouse-configuration)
- [Monitoring Integration](#monitoring-integration)

---

## Core Airflow

### Basic Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `AIRFLOW_IMAGE_NAME` | `apache/airflow:2.11.0-python3.10` | Docker image to use |
| `AIRFLOW_UID` | `50000` | User ID for Airflow (Linux: use `$(id -u)`) |
| `_AIRFLOW_WWW_USER_USERNAME` | `airflow` | Admin username |
| `_AIRFLOW_WWW_USER_PASSWORD` | `airflow` | Admin password (⚠️ change in production) |

### DAG Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `AIRFLOW__CORE__DAGS_FOLDER` | `/opt/airflow/dags` | DAG files location |
| `AIRFLOW__CORE__LOAD_EXAMPLES` | `false` | Load example DAGs |
| `AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION` | `true` | Pause new DAGs by default |
| `AIRFLOW__CORE__PARALLELISM` | `32` | Max tasks across all DAGs |
| `AIRFLOW__CORE__MAX_ACTIVE_TASKS_PER_DAG` | `16` | Max tasks per DAG |
| `AIRFLOW__CORE__MAX_ACTIVE_RUNS_PER_DAG` | `3` | Max concurrent DAG runs |

### Executor Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `AIRFLOW__CORE__EXECUTOR` | `CeleryExecutor` | Executor type |
| `AIRFLOW__CELERY__BROKER_URL` | `redis://:@redis:6379/0` | Celery message broker |
| `AIRFLOW__CELERY__RESULT_BACKEND` | `db+postgresql://...` | Task result storage |
| `AIRFLOW__CELERY__WORKER_CONCURRENCY` | `16` | Tasks per worker |

### Database

| Variable | Default | Description |
|----------|---------|-------------|
| `AIRFLOW__DATABASE__SQL_ALCHEMY_CONN` | `postgresql+psycopg2://airflow:airflow@postgres/airflow` | Metadata DB connection |
| `AIRFLOW__DATABASE__SQL_ALCHEMY_POOL_SIZE` | `5` | Connection pool size |
| `AIRFLOW__DATABASE__SQL_ALCHEMY_MAX_OVERFLOW` | `10` | Max overflow connections |

---

## Market Data Configuration

### API Configuration

| Variable | Default | Description | Required |
|----------|---------|-------------|----------|
| `YAHOO_FINANCE_API_BASE_URL` | `https://query2.finance.yahoo.com/v8/finance/chart` | Yahoo Finance API base URL | Yes |
| `MARKET_DATA_DEFAULT_TICKER` | `AAPL` | Default stock ticker | Yes |
| `MARKET_DATA_API_TIMEOUT` | `30` | API request timeout (seconds) | No |

### Retry Configuration

| Variable | Default | Description | Required |
|----------|---------|-------------|----------|
| `MARKET_DATA_MAX_RETRIES` | `3` | Max API retry attempts | No |
| `MARKET_DATA_RETRY_DELAY` | `5` | Base retry delay (seconds) | No |

### Sensor Configuration

| Variable | Default | Description | Required |
|----------|---------|-------------|----------|
| `MARKET_DATA_SENSOR_POKE_INTERVAL` | `30` | Check interval (seconds) | No |
| `MARKET_DATA_SENSOR_TIMEOUT` | `600` | Max wait time (seconds) | No |
| `MARKET_DATA_SENSOR_EXPONENTIAL_BACKOFF` | `true` | Use exponential backoff | No |

### Storage Configuration

| Variable | Default | Description | Required |
|----------|---------|-------------|----------|
| `MARKET_DATA_STORAGE_DIR` | `/opt/airflow/data` | Parquet file location | Yes |

---

## Logging Configuration

### Basic Logging

| Variable | Default | Description | Options |
|----------|---------|-------------|---------|
| `ENVIRONMENT` | `development` | Environment name | `development`, `staging`, `production` |
| `AIRFLOW__LOGGING__LEVEL` | `INFO` | Log level | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `AIRFLOW__LOGGING__JSON_FORMAT` | `false` | Use JSON format | `true`, `false` |

### Log Storage

| Variable | Default | Description |
|----------|---------|-------------|
| `AIRFLOW__LOGGING__BASE_LOG_FOLDER` | `/opt/airflow/logs` | Log directory |
| `AIRFLOW__LOGGING__DAG_PROCESSOR_MANAGER_LOG_LOCATION` | `/opt/airflow/logs/dag_processor_manager/dag_processor_manager.log` | DAG processor logs |

### Remote Logging (Optional)

#### S3

| Variable | Default | Description |
|----------|---------|-------------|
| `AIRFLOW__LOGGING__REMOTE_LOGGING` | `false` | Enable remote logging |
| `AIRFLOW__LOGGING__REMOTE_BASE_LOG_FOLDER` | `s3://my-bucket/path` | S3 bucket path |
| `AIRFLOW__LOGGING__REMOTE_LOG_CONN_ID` | `aws_default` | AWS connection ID |

#### Google Cloud Storage

| Variable | Default | Description |
|----------|---------|-------------|
| `AIRFLOW__LOGGING__REMOTE_BASE_LOG_FOLDER` | `gs://my-bucket/path` | GCS bucket path |
| `AIRFLOW__LOGGING__REMOTE_LOG_CONN_ID` | `google_cloud_default` | GCP connection ID |

---

## Data Warehouse Configuration

### General Settings

| Variable | Default | Description | Required |
|----------|---------|-------------|----------|
| `ENVIRONMENT` | `development` | Environment selector | Yes |
| `WAREHOUSE_LOAD_STRATEGY` | `upsert` | Load strategy | No |
| `WAREHOUSE_BATCH_SIZE` | `1000` | Records per batch | No |

**Load Strategies**:
- `upsert`: Insert new + update existing
- `append`: Insert all records
- `truncate_insert`: Clear table + insert

### Connection Pooling

| Variable | Default | Description |
|----------|---------|-------------|
| `WAREHOUSE_POOL_SIZE` | `5` | Base connection pool size |
| `WAREHOUSE_MAX_OVERFLOW` | `10` | Max additional connections |
| `WAREHOUSE_POOL_TIMEOUT` | `30` | Connection timeout (seconds) |

### Table Names

| Variable | Default | Description |
|----------|---------|-------------|
| `WAREHOUSE_TABLE_MARKET_DATA` | `fact_market_data` | Main data table |
| `WAREHOUSE_TABLE_TICKERS` | `dim_tickers` | Ticker dimension |
| `WAREHOUSE_TABLE_DATES` | `dim_dates` | Date dimension |

### Development (PostgreSQL)

| Variable | Default | Description | Required |
|----------|---------|-------------|----------|
| `DEV_WAREHOUSE_HOST` | `warehouse-postgres` | Database host | Yes |
| `DEV_WAREHOUSE_PORT` | `5432` | Database port | Yes |
| `DEV_WAREHOUSE_DATABASE` | `market_data_warehouse` | Database name | Yes |
| `DEV_WAREHOUSE_SCHEMA` | `public` | Schema name | Yes |
| `DEV_WAREHOUSE_USER` | `warehouse_user` | Database user | Yes |
| `DEV_WAREHOUSE_PASSWORD` | `CHANGE_ME_dev_warehouse_password` | Database password | Yes |

### Staging (Redshift)

| Variable | Default | Description | Required |
|----------|---------|-------------|----------|
| `STAGING_WAREHOUSE_TYPE` | `redshift` | Warehouse type | Yes |
| `STAGING_WAREHOUSE_HOST` | `your-cluster.region.redshift.amazonaws.com` | Redshift endpoint | Yes |
| `STAGING_WAREHOUSE_PORT` | `5439` | Redshift port | Yes |
| `STAGING_WAREHOUSE_DATABASE` | `market_data_staging` | Database name | Yes |
| `STAGING_WAREHOUSE_SCHEMA` | `public` | Schema name | Yes |
| `STAGING_WAREHOUSE_USER` | `CHANGE_ME_staging_username` | Database user | Yes |
| `STAGING_WAREHOUSE_PASSWORD` | `CHANGE_ME_staging_password` | Database password | Yes |
| `STAGING_WAREHOUSE_REGION` | `us-east-1` | AWS region | Yes |

### Production (Redshift)

| Variable | Default | Description | Required |
|----------|---------|-------------|----------|
| `PROD_WAREHOUSE_TYPE` | `redshift` | Warehouse type | Yes |
| `PROD_WAREHOUSE_HOST` | `your-cluster.region.redshift.amazonaws.com` | Redshift endpoint | Yes |
| `PROD_WAREHOUSE_PORT` | `5439` | Redshift port | Yes |
| `PROD_WAREHOUSE_DATABASE` | `market_data_prod` | Database name | Yes |
| `PROD_WAREHOUSE_SCHEMA` | `public` | Schema name | Yes |
| `PROD_WAREHOUSE_USER` | `CHANGE_ME_prod_username` | Database user | Yes |
| `PROD_WAREHOUSE_PASSWORD` | `CHANGE_ME_prod_password` | Database password | Yes |
| `PROD_WAREHOUSE_REGION` | `us-east-1` | AWS region | Yes |

---

## Monitoring Integration

### Sentry (Error Tracking)

| Variable | Default | Description | Required |
|----------|---------|-------------|----------|
| `SENTRY_DSN` | - | Sentry project DSN | Optional |

**Example**:
```bash
SENTRY_DSN=https://examplePublicKey@o0.ingest.sentry.io/0
```

### Datadog (APM & Metrics)

| Variable | Default | Description | Required |
|----------|---------|-------------|----------|
| `DD_API_KEY` | - | Datadog API key | Optional |
| `DD_SITE` | `datadoghq.com` | Datadog site | Optional |
| `DD_ENV` | Same as `ENVIRONMENT` | Environment tag | Optional |
| `DD_SERVICE` | `airflow-market-data` | Service name | Optional |

**Example**:
```bash
DD_API_KEY=1234567890abcdef1234567890abcdef
DD_SITE=datadoghq.com
DD_ENV=production
DD_SERVICE=airflow-market-data
```

### StatsD (Metrics)

| Variable | Default | Description |
|----------|---------|-------------|
| `AIRFLOW__METRICS__STATSD_ON` | `false` | Enable StatsD |
| `AIRFLOW__METRICS__STATSD_HOST` | `statsd` | StatsD host |
| `AIRFLOW__METRICS__STATSD_PORT` | `8125` | StatsD port |
| `AIRFLOW__METRICS__STATSD_PREFIX` | `airflow` | Metric prefix |

---

## Security Configuration

### Webserver

| Variable | Default | Description |
|----------|---------|-------------|
| `AIRFLOW__WEBSERVER__SECRET_KEY` | (auto-generated) | Flask secret key |
| `AIRFLOW__WEBSERVER__EXPOSE_CONFIG` | `false` | Show config in UI |
| `AIRFLOW__WEBSERVER__RBAC` | `true` | Role-based access control |

**Generate secure key**:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### SMTP (Email Alerts)

| Variable | Default | Description |
|----------|---------|-------------|
| `AIRFLOW__SMTP__SMTP_HOST` | - | SMTP server |
| `AIRFLOW__SMTP__SMTP_STARTTLS` | `true` | Use STARTTLS |
| `AIRFLOW__SMTP__SMTP_SSL` | `false` | Use SSL |
| `AIRFLOW__SMTP__SMTP_USER` | - | SMTP username |
| `AIRFLOW__SMTP__SMTP_PASSWORD` | - | SMTP password |
| `AIRFLOW__SMTP__SMTP_PORT` | `587` | SMTP port |
| `AIRFLOW__SMTP__SMTP_MAIL_FROM` | `airflow@example.com` | From address |

**Gmail Example**:
```bash
AIRFLOW__SMTP__SMTP_HOST=smtp.gmail.com
AIRFLOW__SMTP__SMTP_USER=your-email@gmail.com
AIRFLOW__SMTP__SMTP_PASSWORD=your-app-password
AIRFLOW__SMTP__SMTP_PORT=587
```

---

## Docker Configuration

### Container Resources

```yaml
# Set in docker-compose.yml or docker-compose.prod.yml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 2G
    reservations:
      cpus: '0.5'
      memory: 512M
```

### Volume Mounts

| Path (Host) | Path (Container) | Description |
|-------------|------------------|-------------|
| `./dags` | `/opt/airflow/dags` | DAG files |
| `./logs` | `/opt/airflow/logs` | Log files |
| `./data` | `/opt/airflow/data` | Parquet files |
| `./plugins` | `/opt/airflow/plugins` | Custom plugins |
| `postgres-db-volume` | `/var/lib/postgresql/data` | Metadata DB data |
| `warehouse-db-volume` | `/var/lib/postgresql/data/pgdata` | Warehouse DB data |

---

## Environment-Specific Examples

### Development (.env)

```bash
# Minimal setup for local development
ENVIRONMENT=development
AIRFLOW__CORE__LOAD_EXAMPLES=false
AIRFLOW__LOGGING__LEVEL=DEBUG
MARKET_DATA_DEFAULT_TICKER=AAPL
DEV_WAREHOUSE_PASSWORD=local_dev_pass
```

### Staging (.env)

```bash
# Staging environment
ENVIRONMENT=staging
AIRFLOW__CORE__LOAD_EXAMPLES=false
AIRFLOW__LOGGING__LEVEL=INFO
AIRFLOW__LOGGING__JSON_FORMAT=true
MARKET_DATA_DEFAULT_TICKER=AAPL
STAGING_WAREHOUSE_HOST=staging-cluster.us-east-1.redshift.amazonaws.com
STAGING_WAREHOUSE_USER=staging_user
STAGING_WAREHOUSE_PASSWORD=secure_staging_pass
SENTRY_DSN=https://key@sentry.io/project
```

### Production (.env)

```bash
# Production environment
ENVIRONMENT=production
AIRFLOW__CORE__LOAD_EXAMPLES=false
AIRFLOW__LOGGING__LEVEL=INFO
AIRFLOW__LOGGING__JSON_FORMAT=true
AIRFLOW__WEBSERVER__SECRET_KEY=<SECURE_RANDOM_KEY>
_AIRFLOW_WWW_USER_PASSWORD=<SECURE_PASSWORD>
MARKET_DATA_DEFAULT_TICKER=AAPL
PROD_WAREHOUSE_HOST=prod-cluster.us-east-1.redshift.amazonaws.com
PROD_WAREHOUSE_USER=prod_user
PROD_WAREHOUSE_PASSWORD=secure_prod_pass
SENTRY_DSN=https://key@sentry.io/project
DD_API_KEY=<DATADOG_KEY>
AIRFLOW__SMTP__SMTP_HOST=smtp.company.com
AIRFLOW__SMTP__SMTP_USER=airflow@company.com
AIRFLOW__SMTP__SMTP_PASSWORD=<SMTP_PASSWORD>
```

---

## Configuration Priority

Variables are evaluated in this order:

1. **Airflow Variables** (highest priority)
   - Set via UI: Admin → Variables
   - Or CLI: `airflow variables set KEY VALUE`

2. **Environment Variables**
   - Defined in `.env` file
   - Or set in shell: `export KEY=value`

3. **Default Values** (lowest priority)
   - Hardcoded in application

**Example**:
```python
# Triple-fallback system
ticker = Variable.get("market_data_default_ticker",  # Try Airflow Variable first
    default_var=os.environ.get("MARKET_DATA_DEFAULT_TICKER",  # Then env var
        "AAPL"))  # Finally, default value
```

---

## Security Best Practices

### ⚠️ Never Commit Secrets

```bash
# .gitignore should contain:
.env
*.pem
*.key
secrets/
```

### ✅ Use Strong Passwords

```bash
# Generate secure password
openssl rand -base64 32

# Generate secure key
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### ✅ Use Placeholder Prefix

```bash
# In env.template
DEV_WAREHOUSE_PASSWORD=CHANGE_ME_dev_warehouse_password

# In .env (actual value pulled from secret store)
DEV_WAREHOUSE_PASSWORD=${DEV_WAREHOUSE_PASSWORD_FROM_VAULT}
```

### ✅ Rotate Credentials Regularly

- Database passwords: Every 90 days
- API keys: Every 6 months
- Service accounts: Every 12 months

---

## Validation Script

```bash
#!/bin/bash
# validate_env.sh - Check required variables

REQUIRED_VARS=(
    "AIRFLOW_UID"
    "MARKET_DATA_DEFAULT_TICKER"
    "YAHOO_FINANCE_API_BASE_URL"
    "DEV_WAREHOUSE_PASSWORD"
)

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Missing required variable: $var"
        exit 1
    fi
done

echo "✅ All required variables are set"
```

---

## Related Documentation

- [Configuration Guide](../user-guide/configuration.md)
- [Security Best Practices](../../SECURITY.md)
- [CLI Commands Reference](cli-commands.md)

---

**Last Updated**: 2025-11-12  
**Version**: 1.0.0

