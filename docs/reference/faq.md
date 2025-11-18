# Frequently Asked Questions (FAQ)

Common questions and answers about the Airflow Market Data Pipeline.

---

## Table of Contents

- [General Questions](#general-questions)
- [Installation & Setup](#installation--setup)
- [DAG Execution](#dag-execution)
- [Data & Storage](#data--storage)
- [Dashboard](#dashboard)
- [Performance & Scaling](#performance--scaling)
- [Troubleshooting](#troubleshooting)
- [Advanced Topics](#advanced-topics)

---

## General Questions

### What is this project?

This is a production-ready Apache Airflow 2.11 pipeline that:
- Fetches market data from Yahoo Finance API
- Calculates 12 technical indicators
- Stores data in Parquet format
- Loads data to a Data Warehouse (PostgreSQL/Redshift)

**Schedule**: Runs daily at 6:00 PM ET (post market close), Monday-Friday only.

### What technologies are used?

- **Orchestration**: Apache Airflow 2.11
- **Executor**: CeleryExecutor (distributed task execution)
- **Language**: Python 3.10
- **Containers**: Docker Compose
- **Data Processing**: Pandas
- **Storage**: Parquet (Pyarrow)
- **Warehouse**: PostgreSQL (dev), Amazon Redshift (staging/prod)
- **Dashboard**: Streamlit (interactive visualizations)
- **Message Broker**: Redis
- **Testing**: pytest (197 tests, 92% coverage)

### Is this production-ready?

Yes! The project includes:
- ✅ Comprehensive error handling
- ✅ 197 tests (187 unit + 10 integration) with 92% coverage
- ✅ CI/CD pipeline (GitHub Actions)
- ✅ Centralized logging with extensible architecture
- ✅ Multi-environment configuration
- ✅ Complete documentation (90%)
- ✅ Security best practices

---

## Installation & Setup

### How long does installation take?

**Quick setup**: ~5 minutes
1. Clone repo (30s)
2. Copy `.env` (10s)
3. Initialize Airflow (2 min)
4. Start services (2 min)
5. Access UI (instant)

See: [Quick Start Guide](../getting-started/quick-start.md)

### What are the minimum system requirements?

**Minimum**:
- 4GB RAM
- 2 CPU cores
- 20GB disk space
- Docker 20.10+
- Docker Compose 2.0+

**Recommended**:
- 8GB RAM
- 4 CPU cores
- 50GB disk space

### Do I need to install Airflow locally?

No! Everything runs in Docker containers. You don't need to install:
- ❌ Airflow
- ❌ Python (except for local development)
- ❌ PostgreSQL
- ❌ Redis

Only Docker is required.

### Can I run this on Windows?

Yes, with Docker Desktop for Windows. However:
- Some shell scripts may need WSL2
- File permissions might differ
- Performance may be slower than Linux/Mac

**Recommended**: Use WSL2 (Windows Subsystem for Linux)

### How do I change the admin password?

Edit `.env` file:
```bash
_AIRFLOW_WWW_USER_PASSWORD=your_secure_password
```

Then restart:
```bash
docker compose down
docker compose up airflow-init
docker compose up -d
```

---

## DAG Execution

### When does the DAG run?

**Schedule**: `0 23 * * 1-5` (cron)
- **Time**: 6:00 PM ET (23:00 UTC)
- **Days**: Monday-Friday only
- **Frequency**: Daily (on business days)

**Why 6:00 PM ET?**
- US stock market closes at 4:00 PM ET
- 2-hour buffer ensures all data is finalized
- Aligns with smart timestamp logic (6 PM)

### Why doesn't the DAG run on weekends?

Stock markets are closed on weekends, so:
- No new data available
- API returns empty responses
- Saves unnecessary API calls

**Result**: Saves ~104 unnecessary runs per year (52 weekends × 2 days)

### How do I trigger a manual run?

**From UI**:
1. Go to DAGs page
2. Find `get_market_data`
3. Click ▶️ (trigger)
4. Optionally set params: `{"ticker": "TSLA"}`

**From CLI**:
```bash
docker compose exec airflow-scheduler airflow dags trigger get_market_data --conf '{"ticker": "AAPL"}'
```

### Can I change the ticker?

Yes, three ways:

**1. DAG Parameters** (per run):
```bash
airflow dags trigger get_market_data --conf '{"ticker": "TSLA"}'
```

**2. Airflow Variable** (runtime):
```bash
airflow variables set market_data_default_tickers '["AAPL","MSFT","NVDA"]'
```

**3. Environment Variable** (requires restart):
```bash
# .env
MARKET_DATA_DEFAULT_TICKERS=MSFT
```

### Airflow UI still shows `["AAPL"]` in the DAG parameters after I changed `.env` — why?

Two common causes:

1. **Airflow Variable overrides the env var.**  
   The CLI script `scripts/setup_airflow_variables.sh` sets `market_data.default_tickers`. If that variable exists, it wins over `.env`. Update it via UI/CLI or delete it:
   ```bash
   docker compose exec airflow-scheduler \
     airflow variables set market_data.default_tickers '["AAPL","MSFT","NVDA"]'
   # or remove if you prefer env-driven defaults
   docker compose exec airflow-scheduler \
     airflow variables delete market_data.default_tickers
   ```

2. **Scheduler/webserver are still running with the previous environment.**  
   Docker Compose only loads `.env` during startup. After changing `MARKET_DATA_DEFAULT_TICKERS`, restart the stack so the containers receive the new value:
   ```bash
   make down
   make up
   # or docker compose down && docker compose up -d
   ```

> ✅ **Sanity check:** `docker compose exec airflow-scheduler printenv MARKET_DATA_DEFAULT_TICKERS` should output the list you expect before you check the Airflow UI.

### How does backfill work?

**First Run** (no Parquet file):
- Fetches last 120 trading days (~6 months)
- Creates initial dataset with historical context
- ~85 days of data (excluding weekends)

**Subsequent Runs** (Parquet exists):
- Fetches only current day
- Appends to existing Parquet
- Incremental updates

**Example**:
```
Day 1: Fetch 120 days (2025-05-20 to 2025-11-14)
Day 2: Fetch 1 day (2025-11-15)
Day 3: Fetch 1 day (2025-11-18) [skips weekend]
...
```

**Configuration**:
```bash
# .env
MARKET_DATA_BACKFILL_DAYS=120  # Adjustable
```

### Can I run multiple tickers?

Yes! Each ticker gets its own Parquet file and warehouse records.

**Trigger multiple runs**:
```bash
airflow dags trigger get_market_data --conf '{"ticker": "AAPL"}'
airflow dags trigger get_market_data --conf '{"ticker": "GOOGL"}'
airflow dags trigger get_market_data --conf '{"ticker": "MSFT"}'
```

**Result**:
- `AAPL_market_data.parquet`
- `GOOGL_market_data.parquet`
- `MSFT_market_data.parquet`

---

## Data & Storage

### Where is data stored?

**Three storage layers**:

1. **XCom** (temporary): Task-to-task communication
2. **Parquet** (persistent local): `/opt/airflow/data/{TICKER}_market_data.parquet`
3. **Warehouse** (persistent database):
   - Dev: PostgreSQL container
   - Prod: Amazon Redshift

### How much disk space does Parquet use?

**Approximate sizes** (with Snappy compression):
- 20 days: ~10-20 KB
- 1 year: ~200-300 KB
- 5 years: ~1-1.5 MB

**Very efficient!** Parquet's columnar format compresses well.

### Can I access Parquet files directly?

Yes! Files are on your host machine:

```bash
# Location
./data/AAPL_market_data.parquet

# Read with Pandas
python3 -c "import pandas as pd; df = pd.read_parquet('data/AAPL_market_data.parquet'); print(df.head())"

# Read with DuckDB
duckdb -c "SELECT * FROM 'data/AAPL_market_data.parquet' LIMIT 5"
```

### What technical indicators are calculated?

**12 indicators**:

**Trend**:
- SMA (7, 14, 30 days)
- MACD (line, signal, histogram)

**Momentum**:
- RSI (14 days)

**Volatility**:
- Bollinger Bands (upper, middle, lower)
- 20-day volatility

**Returns**:
- Daily return (%)

### How do I query the warehouse?

**Development (PostgreSQL)**:
```bash
docker compose exec warehouse-postgres psql -U warehouse_user -d market_data_warehouse

# Query
SELECT ticker, date, close, sma_7, rsi 
FROM fact_market_data 
WHERE ticker='AAPL' 
ORDER BY date DESC 
LIMIT 10;
```

**Production (Redshift)**:
Use your SQL client or AWS Query Editor.

### Can I export data to CSV?

Yes, from Parquet:

```bash
docker compose exec airflow-scheduler python3 << 'EOF'
import pandas as pd
df = pd.read_parquet('/opt/airflow/data/AAPL_market_data.parquet')
df.to_csv('/opt/airflow/data/AAPL_export.csv', index=False)
print(f"Exported {len(df)} records")
EOF
```

Or from warehouse:
```bash
docker compose exec warehouse-postgres psql -U warehouse_user -d market_data_warehouse \
  -c "COPY (SELECT * FROM fact_market_data WHERE ticker='AAPL') TO STDOUT WITH CSV HEADER" > AAPL_export.csv
```

---

## Dashboard

### How do I access the dashboard?

The dashboard is a Streamlit web application for visualizing market data.

**Start dashboard**:
```bash
make dashboard
```

**Access**: http://localhost:8501

**Features**:
- Market Data Dashboard with 7 interactive tabs + responsive KPIs
- Warehouse Explorer view with SQL preview, filters, and CSV export
- Sidebar view selector and 🔄 refresh button for warehouse queries
- Multiple tickers support & customizable date ranges

### Can I run INSERT/UPDATE/DELETE from the Warehouse Explorer?

No. The explorer is intentionally **read-only**:

- The backend rejects any statement that does not start with `SELECT`.
- Custom filter text is validated to block semicolons, SQL comments, and destructive keywords (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, etc.).
- Ticker/date filters always use bound parameters to avoid SQL injection.

If you need to run maintenance SQL, use psql/Redshift Query Editor or an admin tool instead of the dashboard.

See: [Dashboard Guide](../user-guide/dashboard.md)

### Dashboard shows "Error loading tickers"?

**Common causes**:

**1. No data in warehouse**:
```bash
# Check if data exists
docker compose exec warehouse-postgres psql -U warehouse_user -d market_data_warehouse \
  -c "SELECT COUNT(*) FROM fact_market_data;"

# Solution: Run the DAG first to load data
```

**2. Connection refused (localhost:5433)**:

**Problem**: Dashboard running in Docker can't connect to `localhost`

**Solution**: Dashboard must connect to `warehouse-postgres:5432` via Docker network

```bash
# Check dashboard/.env
DEV_WAREHOUSE_HOST=warehouse-postgres  # NOT localhost
DEV_WAREHOUSE_PORT=5432                 # NOT 5433

# Restart dashboard
cd dashboard && docker compose restart
```

**3. Wrong password**:

**Problem**: Default template password doesn't match docker-compose.yml

**Solution**: Use `warehouse_pass` (from docker-compose.yml)
```bash
# dashboard/.env
DEV_WAREHOUSE_PASSWORD=warehouse_pass
```

### Dashboard shows SQL syntax error with INTERVAL?

**Error**: `syntax error at or near "180" LINE 25: AND date >= CURRENT_DATE - INTERVAL '180 days'`

**Cause**: Cannot parametrize values inside `INTERVAL` in PostgreSQL

**Fixed in v1.1.0**: Query now uses `CURRENT_DATE - :days * INTERVAL '1 day'`

**If you see this**: Update to latest version or modify `dashboard/app.py` line 144

### Dashboard shows "column sma_30 does not exist"?

**Error**: `column "sma_30" does not exist HINT: Perhaps you meant "sma_20"`

**Cause**: Table schema has `sma_20`, not `sma_30`

**Fixed in v1.1.0**: Dashboard now correctly uses `sma_20`

**Actual indicators**:
- SMA: 7, 14, 20 days (not 30)
- EMA: 12 days
- All other indicators as documented

### Warehouse Explorer is still showing old data after a DAG run?

The explorer caches queries for a few minutes. Click **🔄 Refresh warehouse data** (top of the Warehouse Explorer view) to clear the cache and rerun the SQL with the latest records—no need to restart Streamlit.

### EMA or company names show as NULL in the warehouse/dashboard?

Make sure you are running the latest DAG:

1. The `transform_and_save` task now flattens metadata (`long_name`, `short_name`, `fifty_two_week_high`, `fifty_two_week_low`) and calculates `ema_12`.
2. If historical rows were loaded before this change, trigger a backfill per ticker:
   ```bash
   # Optional: remove local Parquet/cache if you want a clean recompute
   rm data/AAPL_market_data.parquet

   # Trigger DAG per ticker
   docker compose exec airflow-scheduler \
     airflow dags trigger get_market_data --conf '{"ticker": "AAPL"}'
   ```
3. Verify via SQL:
   ```sql
   SELECT ticker, COUNT(ema_12) AS ema12_nn, COUNT(long_name) AS long_name_nn
   FROM fact_market_data GROUP BY ticker;
   ```

### How do I run dashboard locally (without Docker)?

**For development** (connects to Docker warehouse on host):

```bash
# Install dependencies
cd dashboard
pip install -r requirements.txt

# Configure for localhost
cat > .env << EOF
ENVIRONMENT=development
DEV_WAREHOUSE_HOST=localhost
DEV_WAREHOUSE_PORT=5433  # Host port, not container port
DEV_WAREHOUSE_DATABASE=market_data_warehouse
DEV_WAREHOUSE_USER=warehouse_user
DEV_WAREHOUSE_PASSWORD=warehouse_pass
EOF

# Run
streamlit run app.py
```

**Access**: http://localhost:8501

### Can I deploy dashboard to production?

Yes! See: [Dashboard Deployment](../user-guide/dashboard.md#deployment)

**Options**:
1. **Streamlit Cloud** (free tier available)
2. **Docker Compose** (recommended for internal use)
3. **Kubernetes** (for scalability)

**Requirements**:
- Network access to warehouse
- Proper credentials in environment
- HTTPS for production (use reverse proxy)

### Dashboard is slow, how to improve?

**Performance tips**:

**1. Reduce date range**:
- Default: 180 days
- Try: 90 days for faster queries

**2. Enable caching** (already configured):
```python
@st.cache_data(ttl=300)  # 5 min cache
```

**3. Optimize warehouse queries**:
```sql
-- Ensure indexes exist
CREATE INDEX IF NOT EXISTS idx_fact_market_data_ticker_date 
ON fact_market_data(ticker, date DESC);
```

**4. Scale warehouse**:
- Development: Increase PostgreSQL resources
- Production: Use Redshift with proper dist/sort keys

---

## Performance & Scaling

### How many workers can I run?

**Default**: 1 worker

**Scaling**:
```bash
# Scale to 5 workers
docker compose up -d --scale airflow-worker=5

# Each worker handles 16 concurrent tasks
# Total capacity: 80 tasks
```

**Resource per worker**: ~512MB-1GB RAM, 1 CPU

### How fast is the DAG?

**Typical execution** (AAPL, single day):
- validate_ticker: ~1s
- determine_dates: ~1s
- check_api_availability: ~5-30s (depends on API)
- fetch_data: ~10s
- transform_and_save: ~5s
- load_to_warehouse: ~3s

**Total**: ~30-60 seconds

**Backfill** (120 days):
- fetch_data: ~3-4 minutes (120 API calls)
- transform_and_save: ~30s
- load_to_warehouse: ~10s

**Total**: ~4-5 minutes

### Can I run multiple DAGs in parallel?

Yes! Default allows 3 concurrent runs per DAG:

```python
# In DAG definition
max_active_runs=3
```

**For multiple tickers**:
- Each ticker is a separate DAG run
- Can run in parallel
- Limited by worker capacity

### What's the rate limit for Yahoo Finance?

**Observed limits**:
- ~2,000 requests per hour per IP
- 429 errors when exceeded

**Mitigation**:
- Exponential backoff (5s, 10s, 20s)
- Respect `Retry-After` header
- Smart scheduling (weekdays only)

### How do I improve performance?

**1. Increase workers**:
```bash
docker compose up -d --scale airflow-worker=5
```

**2. Increase concurrency**:
```bash
# .env
AIRFLOW__CELERY__WORKER_CONCURRENCY=32
```

**3. Batch processing** (already optimized):
- Warehouse loads in batches of 1000
- Parquet writes are append-only

**4. Connection pooling** (already configured):
- PostgreSQL: 5 base + 10 overflow
- Automatic connection reuse

---

## Troubleshooting

### DAG not appearing in UI?

**Check**:
1. Import errors:
   ```bash
   docker compose exec airflow-scheduler airflow dags list-import-errors
   ```

2. File permissions:
   ```bash
   ls -la dags/get_market_data_dag.py
   # Should be readable
   ```

3. Scheduler logs:
   ```bash
   docker compose logs airflow-scheduler | grep -i error
   ```

### API returns 429 (Rate Limited)?

**This is normal** for high-frequency requests.

**Automatic handling**:
- Exponential backoff (5s, 10s, 20s)
- Respects `Retry-After` header
- Retries up to 3 times

**Manual mitigation**:
- Wait 1 hour between runs
- Use different IP (VPN)
- Increase `SENSOR_POKE_INTERVAL` to 60s

### Task stuck in "running" state?

**Possible causes**:
1. **Worker crashed**: Check `docker compose ps`
2. **Task timeout**: Increase `execution_timeout`
3. **Zombie task**: Clear and retry

**Solution**:
```bash
# Restart worker
docker compose restart airflow-worker

# Clear task
docker compose exec airflow-scheduler airflow tasks clear get_market_data -t stuck_task --yes
```

### No data for today?

**Possible reasons**:
1. **Market not closed yet**: Run after 6 PM ET
2. **Weekend/holiday**: Markets closed
3. **API issue**: Check `check_api_availability` task logs

**Verify**:
```bash
# Check if market is open
curl -s "https://query2.finance.yahoo.com/v8/finance/chart/AAPL?interval=1d" | jq '.chart.result[0].meta.regularMarketTime'
```

### Warehouse connection failed?

**Development (PostgreSQL)**:
```bash
# Check service
docker compose ps warehouse-postgres

# Test connection
docker compose exec warehouse-postgres psql -U warehouse_user -d market_data_warehouse -c "SELECT 1"

# Check logs
docker compose logs warehouse-postgres
```

**Production (Redshift)**:
- Verify credentials in `.env`
- Check security groups
- Verify VPC configuration
- Test connection from Airflow worker

### Tests failing in CI?

**Common issues**:

1. **Coverage too low**:
   - Add more tests
   - Or adjust `pytest.ini`: `--cov-fail-under=70`

2. **Linting errors**:
   ```bash
   # Format code
   black dags/market_data tests/
   isort dags/market_data tests/
   ```

3. **Import errors**:
   - Check `PYTHONPATH` in CI
   - Ensure `sys.path` includes `dags/`

---

## Advanced Topics

### How do I add a new ticker dimension table?

**1. Update warehouse schema**:

```python
# In warehouse/loader.py create_tables()
CREATE TABLE dim_tickers (
    ticker_id SERIAL PRIMARY KEY,
    ticker VARCHAR(10) UNIQUE,
    company_name VARCHAR(100),
    sector VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

**2. Create population logic**:
```python
def populate_ticker_dimension(ticker: str, metadata: dict):
    # Extract from metadata
    # Insert to dim_tickers
```

**3. Add foreign key to fact table**:
```sql
ALTER TABLE fact_market_data 
ADD COLUMN ticker_id INTEGER REFERENCES dim_tickers(ticker_id);
```

### How do I add a new indicator?

**1. Add calculation to technical_indicators.py**:

```python
def calculate_ema(df: pd.DataFrame, period: int = 12) -> pd.Series:
    """Calculate Exponential Moving Average"""
    return df['close'].ewm(span=period, adjust=False).mean()

def calculate_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    # ... existing indicators ...
    
    # Add new indicator
    df['ema_12'] = calculate_ema(df, period=12)
    
    return df
```

**2. Update warehouse schema**:
```sql
ALTER TABLE fact_market_data 
ADD COLUMN ema_12 NUMERIC(10,2);
```

**3. Write tests**:
```python
def test_ema_calculation():
    df = create_sample_data()
    result = calculate_technical_indicators(df)
    assert 'ema_12' in result.columns
    assert result['ema_12'].notna().any()
```

### How do I switch to Redshift?

**1. Update `.env`**:
```bash
ENVIRONMENT=production  # or staging

PROD_WAREHOUSE_HOST=your-cluster.region.redshift.amazonaws.com
PROD_WAREHOUSE_PORT=5439
PROD_WAREHOUSE_DATABASE=market_data_prod
PROD_WAREHOUSE_USER=your_user
PROD_WAREHOUSE_PASSWORD=your_password
PROD_WAREHOUSE_REGION=us-east-1
```

**2. Restart Airflow**:
```bash
docker compose restart airflow-webserver airflow-scheduler airflow-worker
```

**3. Verify**:
```python
docker compose exec airflow-scheduler python3 << 'EOF'
from market_data.config.warehouse_config import get_warehouse_config
config = get_warehouse_config()
print(f"Using: {config['type']} at {config['host']}")
EOF
```

### How do I add Sentry or Datadog monitoring?

The logging system is designed to be extensible. To add external monitoring:

**See**: [Logging Guide - Adding External Monitoring Integrations](../user-guide/logging.md#adding-external-monitoring-integrations)

The guide includes step-by-step instructions for:
- Installing required packages
- Extending the logger module
- Configuring environment variables
- Testing the integration

**Note**: These integrations are not included by default to keep dependencies minimal. You can add them when needed by following the documentation.

### How do I add email alerts?

**1. Configure SMTP** (.env):
```bash
AIRFLOW__SMTP__SMTP_HOST=smtp.gmail.com
AIRFLOW__SMTP__SMTP_PORT=587
AIRFLOW__SMTP__SMTP_USER=your-email@gmail.com
AIRFLOW__SMTP__SMTP_PASSWORD=your-app-password
AIRFLOW__SMTP__SMTP_MAIL_FROM=airflow@yourdomain.com
```

**2. Enable in DAG**:
```python
default_args = {
    'email': ['team@company.com'],
    'email_on_failure': True,
    'email_on_retry': False,
}
```

**3. Restart scheduler**:
```bash
docker compose restart airflow-scheduler
```

### How do I backup data?

**Parquet files** (already on host):
```bash
tar -czf backup_$(date +%Y%m%d).tar.gz ./data/
```

**Metadata DB**:
```bash
docker compose exec postgres pg_dump -U airflow airflow > backup_metadata.sql
```

**Warehouse**:
```bash
docker compose exec warehouse-postgres pg_dump -U warehouse_user market_data_warehouse > backup_warehouse.sql
```

**Restore**:
```bash
cat backup_warehouse.sql | docker compose exec -T warehouse-postgres psql -U warehouse_user -d market_data_warehouse
```

### Can I use a different data source?

Yes! The architecture is modular:

**1. Create new API client** (e.g., `alpha_vantage_client.py`):
```python
class AlphaVantageClient:
    def fetch_market_data(self, ticker: str, date: str) -> Dict:
        # Your implementation
        pass
```

**2. Update operators** to use new client:
```python
from market_data.utils.alpha_vantage_client import AlphaVantageClient

def fetch_market_data(**context):
    client = AlphaVantageClient()
    # ...
```

**3. Add tests** for new client

### How do I deploy to Kubernetes?

See: [Deployment Guide - Kubernetes](../operations/deployment.md#option-2-kubernetes-recommended-for-large-scale)

**Quick version**:
1. Use official Airflow Helm chart
2. Configure CeleryExecutor
3. Use external PostgreSQL and Redis
4. Mount DAGs via Git-sync or ConfigMap

### How do I migrate from development to production?

**1. Export DAG and configuration**:
```bash
# Copy DAGs
tar -czf dags.tar.gz dags/

# Export variables
docker compose exec airflow-scheduler airflow variables export variables.json
```

**2. Setup production environment**:
- Configure `.env` with production values
- Set `ENVIRONMENT=production`
- Configure Redshift credentials

**3. Deploy**:
- Upload DAGs to production server
- Import variables
- Start services

**4. Verify**:
- Check DAG appears
- Run test execution
- Monitor first runs

See: [Deployment Guide](../operations/deployment.md)

---

## Data Quality

### How do I know if data is accurate?

**Validation checks** (automatic):
- ✅ Ticker format validation
- ✅ Date format validation
- ✅ Numeric type conversion
- ✅ Non-null close price check
- ✅ Deduplication by (ticker, date)

**Manual verification**:
```bash
# Compare with Yahoo Finance website
# Check: https://finance.yahoo.com/quote/AAPL/history

# Query warehouse
docker compose exec warehouse-postgres psql -U warehouse_user -d market_data_warehouse \
  -c "SELECT date, close FROM fact_market_data WHERE ticker='AAPL' ORDER BY date DESC LIMIT 5;"
```

### What happens if API returns bad data?

**Error handling**:
1. **Invalid JSON**: Task fails, retries
2. **Empty response**: Logs warning, continues (weekends)
3. **Missing fields**: Uses `None`, calculates indicators with available data
4. **Non-numeric values**: Converts with `pd.to_numeric(errors='coerce')`

### How often should I validate data?

**Recommendations**:
- **Daily**: Automated data quality checks in DAG
- **Weekly**: Manual spot checks
- **Monthly**: Compare with alternative sources

**Create validation DAG**:
```python
# Example validation task
def validate_data_quality(**context):
    df = load_from_parquet("AAPL")
    
    # Check for nulls
    null_count = df['close'].isna().sum()
    if null_count > 5:
        raise ValueError(f"Too many null close prices: {null_count}")
    
    # Check for outliers
    std = df['close'].std()
    outliers = df[df['close'] > df['close'].mean() + 3*std]
    if len(outliers) > 2:
        raise ValueError(f"Suspected outliers: {len(outliers)}")
```

---

## Security & Compliance

### Is my data secure?

**Security measures**:
- ✅ Passwords in `.env` (gitignored)
- ✅ `CHANGE_ME_` prefix prevents accidental commits
- ✅ Warehouse runs as non-root user
- ✅ md5 authentication (not trust)
- ✅ Connection pooling limits
- ✅ Password masking in logs

See: [SECURITY.md](../SECURITY.md)

### How do I comply with data regulations?

**Audit logging** (built-in):
```python
logger.audit("data_accessed", {
    "user": "analyst@company.com",
    "ticker": "AAPL",
    "date_range": "2025-01-01 to 2025-12-31",
    "records": 252
})
```

**Data retention**:
- Configure in warehouse (e.g., DELETE old records)
- Implement TTL policies
- Archive to S3/Glacier

**Access control**:
- Airflow RBAC (role-based access control)
- Warehouse user permissions
- Separate credentials per environment

### Are API keys stored securely?

**Currently**: Environment variables in `.env` (gitignored)

**Production recommendation**:
- AWS Secrets Manager
- HashiCorp Vault
- Azure Key Vault

**Example** (AWS Secrets Manager):
```python
AIRFLOW__SECRETS__BACKEND=airflow.providers.amazon.aws.secrets.secrets_manager.SecretsManagerBackend
AIRFLOW__SECRETS__BACKEND_KWARGS='{"region_name": "us-east-1"}'
```

---

## Monitoring & Alerts

### How do I know if the DAG failed?

**1. Email alerts** (if configured):
Automatic email on failure

**2. Airflow UI**:
Red boxes indicate failures

**3. Logs**:
```bash
docker compose logs airflow-scheduler | grep -i "failed"
```

**4. External monitoring** (optional):
- Add Sentry for error tracking (see [Logging Guide](../user-guide/logging.md))
- Add Datadog for APM and metrics (see [Logging Guide](../user-guide/logging.md))
- Prometheus: Alerts via Alertmanager

### What metrics should I monitor?

**Critical**:
- DAG run success rate (> 95%)
- Task duration (< 5 min)
- API errors (< 5%)
- Worker availability (> 1)

**Important**:
- Records fetched per day
- Warehouse load time
- Disk usage
- Database connections

**Nice to have**:
- API response time
- Indicator calculation time
- Parquet file sizes

See: [Monitoring Guide](../operations/monitoring.md)

### How do I set up alerts?

**Prometheus + Alertmanager**:

```yaml
# alerts.yml
- alert: DAGFailureRate
  expr: rate(airflow_dag_run_failed_total[5m]) > 0.05
  for: 5m
  annotations:
    summary: "High DAG failure rate"
```

**Slack webhook**:
```yaml
# alertmanager.yml
receivers:
  - name: 'slack'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK'
        channel: '#airflow-alerts'
```

See: [Monitoring Guide - Alerting](../operations/monitoring.md#alerting)

---

## Development

### How do I run tests locally?

**Full test suite**:
```bash
docker compose -f docker-compose.test.yml up test
```

**Specific tests**:
```bash
docker compose -f docker-compose.test.yml run --rm test bash -lc "pytest tests/unit/test_api_client.py -v"
```

**With coverage**:
```bash
docker compose -f docker-compose.test.yml up test-coverage
```

See: [Testing Guide](../developer-guide/testing.md)

### How do I contribute?

**Steps**:
1. Fork repository
2. Create feature branch
3. Make changes + add tests
4. Run tests and linting
5. Commit and push
6. Open Pull Request

See: [Contributing Guide](../developer-guide/contributing.md)

### What's the code style?

**Tools**:
- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting

**Standards**:
- PEP 8 compliant
- Type hints required
- Docstrings for all functions
- 70%+ test coverage

See: [Code Style Guide](../developer-guide/code-style.md)

---

## Related Documentation

- [Quick Start Guide](../getting-started/quick-start.md)
- [Market Data DAG Guide](../user-guide/market-data-dag.md)
- [Troubleshooting Guide](../operations/troubleshooting.md)
- [CLI Commands Reference](cli-commands.md)

---

**Last Updated**: 2025-11-14  
**Questions not answered?** [Open an issue](https://github.com/avalosjuancarlos/poc_airflow/issues) or check [Troubleshooting](../operations/troubleshooting.md)

