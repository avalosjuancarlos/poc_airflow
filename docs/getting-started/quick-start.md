# Quick Start Guide

Get up and running with Airflow Market Data Pipeline in 5 minutes.

---

## Prerequisites

- Docker Desktop or Docker Engine (v20.10+)
- Docker Compose (v2.0+)
- 4GB RAM minimum (8GB recommended)

---

## 1. Clone & Setup (1 minute)

```bash
# Clone the repository
git clone <repository-url>
cd poc_airflow

# Copy environment template
cp env.template .env

# (Linux only) Set Airflow UID
echo "AIRFLOW_UID=$(id -u)" >> .env
```

---

## 2. Start Airflow (2 minutes)

```bash
# Initialize database
docker compose up airflow-init

# Start all services
docker compose up -d

# Wait for services to be healthy (~60 seconds)
docker compose ps
```

**Expected output**: All services should show "healthy" status.

---

## 3. Access Airflow UI (30 seconds)

Open your browser at: **http://localhost:8080**

**Login Credentials**:
- Username: `airflow`
- Password: `airflow`

---

## 4. Run Your First DAG (1 minute)

### From Airflow UI:

1. Navigate to **DAGs** page
2. Find `get_market_data` DAG
3. Toggle it **ON** (unpause)
4. Click **▶️ Trigger DAG**
5. Optionally, click **▶️ with config** and use:
   ```json
   {"ticker": "AAPL"}
   ```

### From CLI:

```bash
# Trigger with default ticker
docker compose exec airflow-scheduler airflow dags trigger get_market_data

# Or with custom ticker
docker compose exec airflow-scheduler airflow dags trigger get_market_data \
  --conf '{"ticker": "TSLA"}'
```

---

## 5. Monitor Execution (30 seconds)

### In Airflow UI:

1. Click on the DAG run (colored circle)
2. View **Graph** or **Grid** view
3. Watch tasks turn green as they complete

### Expected Flow:

```
validate_ticker (5s) ✅
       ↓
determine_dates (2s) ✅  
       ↓
check_api_availability (10s) ✅
       ↓
fetch_data (30s) ✅
       ↓
transform_and_save (15s) ✅
       ↓
load_to_warehouse (5s) ✅
```

**Total time**: ~1-2 minutes

---

## 6. Verify Results (30 seconds)

### Check Parquet File:

```bash
# List data files
docker compose exec airflow-scheduler ls -lh /opt/airflow/data/

# Expected output:
# AAPL_market_data.parquet (~50-100KB)
```

### Check Warehouse:

```bash
# Connect to warehouse
docker compose exec warehouse-postgres psql -U warehouse_user -d market_data_warehouse

# Query data
SELECT ticker, date, close, sma_7, rsi FROM fact_market_data ORDER BY date DESC LIMIT 5;

# Exit
\q
```

**Expected**: 15-20 records with OHLCV data and technical indicators.

---

## 🎉 Success!

You now have:
- ✅ Airflow running with CeleryExecutor
- ✅ Market data from Yahoo Finance
- ✅ 12 technical indicators calculated
- ✅ Data stored in Parquet and PostgreSQL

---

## Next Steps

### Learn More

- 📖 [Market Data DAG Guide](../user-guide/market-data-dag.md) - Detailed DAG documentation
- ⚙️ [Configuration Guide](../user-guide/configuration.md) - Customize your setup
- 🗄️ [Data Warehouse Guide](../user-guide/data-warehouse.md) - Multi-environment warehouse
- 🧪 [Testing Guide](../developer-guide/testing.md) - Run tests

### Customize Your Setup

```bash
# Edit configuration
nano .env

# Set your default ticker
MARKET_DATA_DEFAULT_TICKER=TSLA

# Restart services
docker compose restart airflow-webserver airflow-scheduler
```

### Add More Tickers

```bash
# Trigger for multiple tickers
docker compose exec airflow-scheduler airflow dags trigger get_market_data --conf '{"ticker": "GOOGL"}'
docker compose exec airflow-scheduler airflow dags trigger get_market_data --conf '{"ticker": "MSFT"}'
docker compose exec airflow-scheduler airflow dags trigger get_market_data --conf '{"ticker": "AMZN"}'
```

### Enable Daily Automation

The DAG runs automatically every day at 00:00 UTC. No additional configuration needed!

---

## Troubleshooting

### Services not starting?

```bash
# Check logs
docker compose logs airflow-scheduler

# Restart services
docker compose restart
```

### DAG not appearing?

```bash
# Check for import errors
docker compose exec airflow-scheduler airflow dags list-import-errors

# Refresh DAGs
docker compose exec airflow-scheduler airflow dags list
```

### Port 8080 already in use?

Edit `docker-compose.yml`:
```yaml
webserver:
  ports:
    - "8081:8080"  # Change 8080 to 8081
```

Then restart:
```bash
docker compose up -d
```

---

## Quick Reference

| Command | Description |
|---------|-------------|
| `docker compose up -d` | Start all services |
| `docker compose down` | Stop all services |
| `docker compose ps` | Check service status |
| `docker compose logs -f airflow-scheduler` | View logs |
| `docker compose restart airflow-worker` | Restart a service |

---

## Getting Help

- 📚 [Full Documentation](../README.md)
- 🐛 [Troubleshooting Guide](../operations/troubleshooting.md) 🔜
- 🔒 [Security Best Practices](../../SECURITY.md)

---

**Estimated completion time**: 5 minutes ⏱️

**Next**: [Market Data DAG Guide](../user-guide/market-data-dag.md) to learn about all features
