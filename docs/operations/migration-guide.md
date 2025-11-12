# Migration Guide

Step-by-step guide for migrating between environments and versions.

---

## Table of Contents

- [Environment Migration](#environment-migration)
- [Version Upgrades](#version-upgrades)
- [Database Migration](#database-migration)
- [Data Migration](#data-migration)

---

## Environment Migration

### Development → Staging

Migrating from local development to staging environment.

#### 1. Prepare Staging Environment

```bash
# On staging server
git clone <repository-url> /opt/airflow-staging
cd /opt/airflow-staging
cp env.template .env
```

#### 2. Configure Staging

Edit `.env`:

```bash
# Environment
ENVIRONMENT=staging

# Airflow
_AIRFLOW_WWW_USER_PASSWORD=<SECURE_PASSWORD>
AIRFLOW__WEBSERVER__SECRET_KEY=<GENERATED_KEY>

# Warehouse (Redshift)
STAGING_WAREHOUSE_HOST=staging-cluster.region.redshift.amazonaws.com
STAGING_WAREHOUSE_DATABASE=market_data_staging
STAGING_WAREHOUSE_USER=staging_user
STAGING_WAREHOUSE_PASSWORD=<SECURE_PASSWORD>
STAGING_WAREHOUSE_REGION=us-east-1

# Monitoring
SENTRY_DSN=https://key@sentry.io/staging-project
DD_API_KEY=<DATADOG_KEY>
```

#### 3. Export Configuration

**From Development**:
```bash
# Export Airflow Variables
docker compose exec airflow-scheduler airflow variables export /tmp/variables.json
docker compose cp airflow-scheduler:/tmp/variables.json ./variables_export.json

# Export Connections (if any)
docker compose exec airflow-scheduler airflow connections export /tmp/connections.json
docker compose cp airflow-scheduler:/tmp/connections.json ./connections_export.json
```

#### 4. Deploy to Staging

```bash
# On staging server
cd /opt/airflow-staging

# Initialize
docker compose up airflow-init

# Start services
docker compose up -d

# Import configuration
docker compose exec -T airflow-scheduler airflow variables import - < variables_export.json
docker compose exec -T airflow-scheduler airflow connections import - < connections_export.json
```

#### 5. Verify Staging

```bash
# Check services
docker compose ps

# Test DAG
docker compose exec airflow-scheduler airflow dags test get_market_data 2025-11-13

# Check warehouse connection
docker compose exec airflow-scheduler python3 << 'EOF'
from market_data.config.warehouse_config import get_warehouse_config
print(get_warehouse_config())
EOF
```

### Staging → Production

Similar to dev→staging, with production credentials.

**Additional Steps**:

1. **Setup High Availability**:
   ```bash
   # Run 2 schedulers
   docker compose up -d --scale airflow-scheduler=2
   
   # Run 3+ workers
   docker compose up -d --scale airflow-worker=3
   ```

2. **Configure SSL/TLS**:
   - Setup nginx reverse proxy
   - Install SSL certificates
   - Force HTTPS

3. **Enable Monitoring**:
   - Prometheus + Grafana
   - Datadog APM
   - Sentry error tracking

4. **Setup Backups**:
   ```bash
   # Automated daily backups
   crontab -e
   # Add: 0 2 * * * /opt/airflow-production/scripts/backup.sh
   ```

---

## Version Upgrades

### Airflow 2.11.0 → 2.11.x (Minor Version)

**1. Check Release Notes**:
Visit: https://airflow.apache.org/docs/apache-airflow/stable/release_notes.html

**2. Update Image**:

```bash
# .env
AIRFLOW_IMAGE_NAME=apache/airflow:2.11.1-python3.10  # New version
```

**3. Backup**:
```bash
docker compose exec postgres pg_dump -U airflow airflow > backup_pre_upgrade.sql
```

**4. Upgrade**:
```bash
# Stop services
docker compose down

# Pull new image
docker compose pull

# Upgrade database
docker compose up airflow-init

# Start services
docker compose up -d
```

**5. Verify**:
```bash
# Check version
docker compose exec airflow-scheduler airflow version

# Test DAG
docker compose exec airflow-scheduler airflow dags test get_market_data 2025-11-13
```

### Airflow 2.11 → 3.0 (Major Version)

**⚠️ Breaking Changes Expected**

**Pre-Migration**:
1. Read Airflow 3.0 migration guide
2. Test in development first
3. Update all custom operators
4. Update requirements.txt

**Migration Steps**:
1. Backup everything
2. Update in dev environment
3. Run all tests
4. Fix breaking changes
5. Deploy to staging
6. Validate for 1 week
7. Deploy to production

### Python 3.10 → 3.11

**1. Update Image**:
```bash
AIRFLOW_IMAGE_NAME=apache/airflow:2.11.0-python3.11
```

**2. Test Dependencies**:
```bash
# Check compatibility
docker compose build
docker compose run --rm airflow-webserver pip check
```

**3. Run Tests**:
```bash
docker compose -f docker-compose.test.yml up test
```

**4. Deploy if tests pass**

---

## Database Migration

### PostgreSQL Schema Changes

**Add Column**:

```python
# In warehouse/loader.py create_tables()

ALTER TABLE fact_market_data 
ADD COLUMN IF NOT EXISTS new_indicator NUMERIC(10,2);

CREATE INDEX IF NOT EXISTS idx_new_indicator 
ON fact_market_data (new_indicator);
```

**Safe Deployment**:
1. Add column (nullable)
2. Deploy code
3. Backfill data
4. Make NOT NULL (if needed)

### Migrate Parquet Schema

**When**: Adding new columns to Parquet files

**Process**:

```python
import pandas as pd

# 1. Read existing Parquet
df = pd.read_parquet('data/AAPL_market_data.parquet')

# 2. Add new column
df['new_indicator'] = calculate_new_indicator(df)

# 3. Save (overwrites)
df.to_parquet('data/AAPL_market_data.parquet', engine='pyarrow')
```

**Automated Migration Task**:

```python
def migrate_parquet_schema(**context):
    """Migrate all Parquet files to new schema"""
    import os
    from market_data.storage.parquet_storage import load_from_parquet, save_to_parquet
    
    data_dir = os.environ.get('MARKET_DATA_STORAGE_DIR')
    files = [f for f in os.listdir(data_dir) if f.endswith('.parquet')]
    
    for file in files:
        ticker = file.replace('_market_data.parquet', '')
        df = load_from_parquet(ticker)
        
        # Add new column
        df['new_indicator'] = calculate_new(df)
        
        # Save
        save_to_parquet(df, ticker)
        logger.info(f"Migrated {ticker}")
```

---

## Data Migration

### Backfill Historical Data

**Scenario**: You want data from 2024-01-01 to present

**Option 1: DAG Backfill** (Recommended)

```bash
# Backfill range
docker compose exec airflow-scheduler airflow dags backfill get_market_data \
  --start-date 2024-01-01 \
  --end-date 2025-11-12 \
  --reset-dagruns

# Monitor progress
docker compose logs -f airflow-worker
```

**Option 2: Manual Script**

```python
# scripts/backfill_historical.py
from datetime import datetime, timedelta
import pandas as pd
from market_data.utils.api_client import YahooFinanceClient
from market_data.transformers.technical_indicators import calculate_technical_indicators
from market_data.storage.parquet_storage import save_to_parquet

client = YahooFinanceClient(base_url="https://query2.finance.yahoo.com/v8/finance/chart")

start_date = datetime(2024, 1, 1)
end_date = datetime(2025, 11, 12)
ticker = "AAPL"

all_data = []
current = start_date

while current <= end_date:
    date_str = current.strftime("%Y-%m-%d")
    data = client.fetch_market_data(ticker, date_str)
    
    if data:
        all_data.append(data)
    
    current += timedelta(days=1)

# Transform
df = pd.DataFrame(all_data)
df_enriched = calculate_technical_indicators(df)

# Save
save_to_parquet(df_enriched, ticker)
print(f"Backfilled {len(df_enriched)} records")
```

**Run**:
```bash
docker compose exec airflow-scheduler python3 /opt/airflow/scripts/backfill_historical.py
```

### Import External Data

**From CSV**:

```python
import pandas as pd
from market_data.transformers.technical_indicators import calculate_technical_indicators
from market_data.storage.parquet_storage import save_to_parquet

# Read CSV
df = pd.read_csv('external_data.csv')

# Ensure correct columns
required_columns = ['ticker', 'date', 'open', 'high', 'low', 'close', 'volume']
assert all(col in df.columns for col in required_columns)

# Calculate indicators
df_enriched = calculate_technical_indicators(df)

# Save to Parquet
ticker = df['ticker'].iloc[0]
save_to_parquet(df_enriched, ticker)
```

### Migrate to New Warehouse

**Scenario**: Moving from PostgreSQL dev to Redshift prod

**1. Export from PostgreSQL**:
```bash
docker compose exec warehouse-postgres psql -U warehouse_user -d market_data_warehouse \
  -c "COPY fact_market_data TO STDOUT WITH CSV HEADER" > export_warehouse.csv
```

**2. Upload to S3** (for Redshift):
```bash
aws s3 cp export_warehouse.csv s3://your-bucket/data/
```

**3. COPY to Redshift**:
```sql
COPY fact_market_data
FROM 's3://your-bucket/data/export_warehouse.csv'
IAM_ROLE 'arn:aws:iam::account:role/RedshiftCopyRole'
CSV
IGNOREHEADER 1;
```

**Alternative**: Use Parquet files directly

```bash
# 1. Ensure .env has production config
ENVIRONMENT=production

# 2. Restart Airflow
docker compose restart airflow-scheduler airflow-worker

# 3. Clear and rerun DAG
docker compose exec airflow-scheduler airflow tasks clear get_market_data --yes
```

The warehouse loader will automatically read Parquet and load to Redshift.

---

## Rollback Procedures

### Rollback Application

```bash
# 1. Stop services
docker compose down

# 2. Find previous version
git log --oneline -10

# 3. Checkout previous version
git checkout <PREVIOUS_COMMIT>

# 4. Restart
docker compose up -d

# 5. Verify
curl http://localhost:8080/health
```

### Rollback Database

```bash
# 1. Stop Airflow
docker compose stop airflow-scheduler airflow-webserver airflow-worker

# 2. Restore from backup
cat backup_metadata.sql | docker compose exec -T postgres psql -U airflow -d airflow

# 3. Restart
docker compose start airflow-scheduler airflow-webserver airflow-worker
```

### Rollback Warehouse Data

```bash
# Option 1: Restore from backup
cat backup_warehouse.sql | docker compose exec -T warehouse-postgres psql -U warehouse_user -d market_data_warehouse

# Option 2: Truncate and reload from Parquet
docker compose exec warehouse-postgres psql -U warehouse_user -d market_data_warehouse \
  -c "TRUNCATE TABLE fact_market_data;"

# Trigger reload
docker compose exec airflow-scheduler airflow tasks clear get_market_data -t load_to_warehouse --yes
```

---

## Zero-Downtime Migration

### Blue-Green Deployment

**Setup Two Environments**:

```bash
# Blue (current production)
/opt/airflow-blue/
  └── docker-compose.yml (port 8080)

# Green (new version)
/opt/airflow-green/
  └── docker-compose.yml (port 8081)
```

**Migration Steps**:

1. **Deploy to Green**:
   ```bash
   cd /opt/airflow-green
   git pull origin main
   docker compose up -d
   ```

2. **Test Green**:
   ```bash
   curl http://localhost:8081/health
   # Run test DAG
   ```

3. **Switch Traffic** (nginx):
   ```nginx
   upstream airflow {
       server localhost:8081;  # Point to green
   }
   ```

4. **Reload nginx**:
   ```bash
   sudo nginx -t
   sudo systemctl reload nginx
   ```

5. **Monitor for Issues**:
   - Check logs
   - Monitor error rates
   - Verify DAG executions

6. **Rollback if Needed**:
   ```nginx
   upstream airflow {
       server localhost:8080;  # Back to blue
   }
   ```

7. **Decommission Blue** (after 1 week):
   ```bash
   cd /opt/airflow-blue
   docker compose down
   ```

---

## Checklist

### Pre-Migration

- [ ] Backup all databases
- [ ] Export Airflow Variables
- [ ] Export Connections
- [ ] Document current configuration
- [ ] Test in development first
- [ ] Notify team of migration window
- [ ] Prepare rollback plan

### During Migration

- [ ] Stop schedulers (prevent new runs)
- [ ] Wait for running tasks to complete
- [ ] Run migration scripts
- [ ] Verify database schema
- [ ] Start services
- [ ] Import configuration

### Post-Migration

- [ ] Verify all services healthy
- [ ] Test DAG execution
- [ ] Check warehouse connectivity
- [ ] Monitor for 24 hours
- [ ] Remove old backups after 30 days

---

## Related Documentation

- [Deployment Guide](deployment.md)
- [Troubleshooting Guide](troubleshooting.md)
- [Data Warehouse Guide](../user-guide/data-warehouse.md)

---

**Last Updated**: 2025-11-12  
**Version**: 1.0.0

