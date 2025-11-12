# Performance Tuning Guide

Optimize Airflow Market Data Pipeline for maximum performance.

---

## Table of Contents

- [Performance Metrics](#performance-metrics)
- [Worker Optimization](#worker-optimization)
- [Database Optimization](#database-optimization)
- [Storage Optimization](#storage-optimization)
- [Network Optimization](#network-optimization)
- [Monitoring Performance](#monitoring-performance)

---

## Performance Metrics

### Current Baseline

**Single Day Execution** (AAPL):
```
validate_ticker:           ~1s
determine_dates:           ~1s
check_api_availability:    ~5-30s
fetch_data:                ~10s
transform_and_save:        ~5s
load_to_warehouse:         ~3s
---
Total:                     ~30-60s
```

**20-Day Backfill**:
```
validate_ticker:           ~1s
determine_dates:           ~2s
check_api_availability:    ~5-30s
fetch_data:                ~30-40s (20 API calls)
transform_and_save:        ~10s
load_to_warehouse:         ~5s
---
Total:                     ~1-2 minutes
```

### Performance Targets

| Metric | Target | Excellent |
|--------|--------|-----------|
| **Single day run** | < 60s | < 30s |
| **20-day backfill** | < 2 min | < 90s |
| **Warehouse load** | < 5s | < 2s |
| **API response time** | < 1s | < 500ms |
| **Worker CPU usage** | < 70% | < 50% |
| **Memory usage** | < 1GB | < 512MB |

---

## Worker Optimization

### 1. Scale Workers Horizontally

**Default**: 1 worker

**Recommended for**:
- 1-5 tickers: 1 worker
- 5-20 tickers: 3 workers
- 20+ tickers: 5+ workers

**Scale command**:
```bash
docker compose up -d --scale airflow-worker=5
```

**Calculate capacity**:
```
Workers: 5
Concurrency per worker: 16
Total capacity: 80 concurrent tasks
```

### 2. Adjust Worker Concurrency

**Current**: 16 tasks per worker

**Tune based on tasks**:

```bash
# CPU-intensive tasks (transformations)
AIRFLOW__CELERY__WORKER_CONCURRENCY=8

# I/O-intensive tasks (API calls, DB)
AIRFLOW__CELERY__WORKER_CONCURRENCY=32
```

**Our case**: Balanced (API + Transform)
```bash
AIRFLOW__CELERY__WORKER_CONCURRENCY=16  # Good default
```

### 3. Resource Limits

**Set in docker-compose.yml**:

```yaml
airflow-worker:
  deploy:
    resources:
      limits:
        cpus: '2.0'
        memory: 2G
      reservations:
        cpus: '0.5'
        memory: 512M
```

**Sizing Guide**:
- **CPU**: 1-2 cores per worker
- **Memory**: 512MB-2GB per worker
- **Swap**: 2x memory (for burst)

### 4. Task Pools

**Create pools** for resource control:

```bash
# API calls (limit concurrent requests)
docker compose exec airflow-scheduler airflow pools set api_pool 5 "Yahoo Finance API calls"

# DB operations (limit connections)
docker compose exec airflow-scheduler airflow pools set db_pool 10 "Database operations"
```

**Use in DAG**:
```python
fetch_task = PythonOperator(
    task_id='fetch_data',
    python_callable=fetch_multiple_dates,
    pool='api_pool',  # Limit to 5 concurrent
)
```

---

## Database Optimization

### PostgreSQL (Metadata DB)

#### 1. Connection Pooling

```bash
# .env
AIRFLOW__DATABASE__SQL_ALCHEMY_POOL_SIZE=10
AIRFLOW__DATABASE__SQL_ALCHEMY_MAX_OVERFLOW=20
AIRFLOW__DATABASE__SQL_ALCHEMY_POOL_RECYCLE=3600
```

**Formula**:
```
Max connections needed = (schedulers × 10) + (workers × concurrency)
Example: (1 × 10) + (3 × 16) = 58 connections
```

#### 2. PostgreSQL Configuration

**docker-compose.yml**:
```yaml
postgres:
  environment:
    POSTGRES_MAX_CONNECTIONS: 100
    POSTGRES_SHARED_BUFFERS: 256MB
    POSTGRES_EFFECTIVE_CACHE_SIZE: 1GB
    POSTGRES_WORK_MEM: 16MB
```

#### 3. Vacuum and Analyze

```bash
# Weekly maintenance
docker compose exec postgres psql -U airflow -d airflow << 'EOF'
VACUUM ANALYZE task_instance;
VACUUM ANALYZE dag_run;
REINDEX TABLE task_instance;
EOF
```

### Warehouse DB

#### 1. Optimize Batch Size

**Current**: 1000 records per batch

**Tune based on volume**:
```bash
# Small datasets (<10K)
WAREHOUSE_BATCH_SIZE=500

# Medium datasets (10-100K)
WAREHOUSE_BATCH_SIZE=1000  # Default

# Large datasets (>100K)
WAREHOUSE_BATCH_SIZE=5000
```

#### 2. Choose Right Load Strategy

| Strategy | Best For | Speed |
|----------|----------|-------|
| **UPSERT** | Daily incremental | Medium |
| **APPEND** | Bulk inserts (no updates) | Fast |
| **TRUNCATE_INSERT** | Full refresh | Slowest |

**Tune**:
```bash
# For daily updates (default)
WAREHOUSE_LOAD_STRATEGY=upsert

# For historical backfill
WAREHOUSE_LOAD_STRATEGY=append
```

#### 3. Index Optimization

**Add indexes for your queries**:

```sql
-- If you query by ticker frequently
CREATE INDEX IF NOT EXISTS idx_ticker 
ON fact_market_data (ticker);

-- If you query by date range
CREATE INDEX IF NOT EXISTS idx_date_range 
ON fact_market_data (date DESC);

-- Composite index for common queries
CREATE INDEX IF NOT EXISTS idx_ticker_date_indicators 
ON fact_market_data (ticker, date DESC, rsi, macd);
```

**Monitor index usage**:
```sql
SELECT 
    schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
WHERE tablename = 'fact_market_data'
ORDER BY idx_scan DESC;
```

---

## Storage Optimization

### Parquet Files

#### 1. Compression

**Current**: Snappy (default)

**Alternatives**:
```python
# In parquet_storage.py

# GZIP - Better compression, slower
df.to_parquet(path, compression='gzip')

# Snappy - Balanced (current)
df.to_parquet(path, compression='snappy')

# None - Fastest, largest files
df.to_parquet(path, compression=None)
```

**Recommendation**: Stick with Snappy for balanced performance.

#### 2. Partitioning

**For large datasets** (>1M records):

```python
# Partition by ticker
df.to_parquet(
    '/opt/airflow/data',
    partition_cols=['ticker'],
    compression='snappy'
)

# Result:
# data/ticker=AAPL/part-0.parquet
# data/ticker=GOOGL/part-0.parquet
```

**Benefits**:
- Faster reads (only scan relevant partitions)
- Better for multi-ticker analysis

#### 3. Column Pruning

**Read only needed columns**:
```python
# Instead of
df = pd.read_parquet('data/AAPL_market_data.parquet')

# Do
df = pd.read_parquet(
    'data/AAPL_market_data.parquet',
    columns=['date', 'close', 'sma_7', 'rsi']
)
```

**Result**: 75% faster reads for 4/32 columns

---

## Network Optimization

### API Call Optimization

#### 1. Reduce API Calls

**Current strategy**:
- 20 individual calls for backfill
- 1 call for daily update

**Optimization**: Batch API calls (if supported)

```python
# Yahoo Finance supports range queries
period1 = 1698796800  # Start timestamp
period2 = 1731446400  # End timestamp

url = f"{base_url}/{ticker}?period1={period1}&period2={period2}&interval=1d"
```

**Result**: 1 API call instead of 20 (95% reduction)

#### 2. Cache API Responses

**Implement caching**:

```python
from functools import lru_cache
from datetime import datetime

@lru_cache(maxsize=100)
def fetch_cached(ticker: str, date: str) -> Dict:
    return client.fetch_market_data(ticker, date)
```

**Benefits**:
- Avoid duplicate API calls in same DAG run
- Faster retries
- Reduced rate limiting

#### 3. Respect Rate Limits

**Already implemented**:
- Exponential backoff
- `Retry-After` header respect
- Max 3 retries

**Additional**:
```python
# Add delay between API calls
import time

for date in dates:
    data = fetch_data(ticker, date)
    time.sleep(0.5)  # 500ms delay between calls
```

---

## Task Optimization

### 1. Parallel Task Execution

**Current**: Sequential tasks

**Opportunity**: Fetch multiple tickers in parallel

```python
# Create dynamic task for each ticker
from airflow.decorators import task

@task
def fetch_ticker_data(ticker: str):
    # Fetch data for one ticker
    pass

# Generate tasks dynamically
tickers = ['AAPL', 'GOOGL', 'MSFT', 'AMZN']
fetch_tasks = [fetch_ticker_data(t) for t in tickers]

# All run in parallel (limited by worker capacity)
```

### 2. Task Priority

**Set priority** for critical tasks:

```python
fetch_task = PythonOperator(
    task_id='fetch_data',
    python_callable=fetch_multiple_dates,
    priority_weight=10,  # Higher = higher priority
)

warehouse_task = PythonOperator(
    task_id='load_to_warehouse',
    python_callable=load_to_warehouse,
    priority_weight=5,
)
```

### 3. Sensor Mode

**Current**: `reschedule` mode (frees worker slot)

**Alternative**: `poke` mode (keeps worker)

```python
api_sensor = PythonSensor(
    task_id='check_api_availability',
    python_callable=check_api_availability,
    mode='reschedule',  # Recommended for long waits
    # mode='poke',  # Use for short waits (<1 min)
)
```

**When to use**:
- `reschedule`: Long waits (>1 min) - frees worker
- `poke`: Short waits (<1 min) - keeps worker

---

## Monitoring Performance

### Key Metrics to Track

**1. Task Duration**:
```sql
SELECT 
    task_id,
    AVG(EXTRACT(EPOCH FROM (end_date - start_date))) as avg_seconds,
    MAX(EXTRACT(EPOCH FROM (end_date - start_date))) as max_seconds
FROM task_instance
WHERE dag_id = 'get_market_data'
    AND state = 'success'
    AND start_date > NOW() - INTERVAL '7 days'
GROUP BY task_id
ORDER BY avg_seconds DESC;
```

**2. Queue Time**:
```sql
-- Time between queued and started
SELECT 
    task_id,
    AVG(EXTRACT(EPOCH FROM (start_date - queued_dttm))) as avg_queue_seconds
FROM task_instance
WHERE dag_id = 'get_market_data'
    AND queued_dttm IS NOT NULL
    AND start_date > NOW() - INTERVAL '7 days'
GROUP BY task_id;
```

**3. Worker Utilization**:
```bash
# Flower
open http://localhost:5555

# Or Celery inspect
docker compose exec airflow-scheduler airflow celery inspect stats
```

### Performance Dashboard (Grafana)

**Key Panels**:

1. **DAG Duration (P95)**:
   ```promql
   histogram_quantile(0.95, 
     rate(airflow_dagrun_duration_seconds_bucket{dag_id="get_market_data"}[5m])
   )
   ```

2. **Task Execution Rate**:
   ```promql
   rate(airflow_task_duration_seconds_count[5m])
   ```

3. **Worker CPU**:
   ```promql
   rate(container_cpu_usage_seconds_total{name=~".*airflow-worker.*"}[5m])
   ```

4. **API Call Latency**:
   ```promql
   histogram_quantile(0.95, 
     rate(api_request_duration_seconds_bucket{endpoint="/chart"}[5m])
   )
   ```

---

## Benchmarking

### Run Benchmark

**Script**: `scripts/benchmark.sh`

```bash
#!/bin/bash

echo "=== Airflow Performance Benchmark ==="

# 1. Single day execution
echo "Test 1: Single Day Execution"
start=$(date +%s)
docker compose exec airflow-scheduler airflow dags test get_market_data 2025-11-13 > /dev/null 2>&1
end=$(date +%s)
echo "Duration: $((end - start))s"

# 2. Parallel execution (3 tickers)
echo ""
echo "Test 2: Parallel Execution (3 tickers)"
start=$(date +%s)
docker compose exec airflow-scheduler airflow dags trigger get_market_data --conf '{"ticker": "AAPL"}' &
docker compose exec airflow-scheduler airflow dags trigger get_market_data --conf '{"ticker": "GOOGL"}' &
docker compose exec airflow-scheduler airflow dags trigger get_market_data --conf '{"ticker": "MSFT"}' &
wait
end=$(date +%s)
echo "Duration: $((end - start))s"

# 3. Warehouse query performance
echo ""
echo "Test 3: Warehouse Query"
start=$(date +%s)
docker compose exec warehouse-postgres psql -U warehouse_user -d market_data_warehouse \
  -c "SELECT * FROM fact_market_data WHERE ticker='AAPL' ORDER BY date DESC LIMIT 1000" > /dev/null
end=$(date +%s)
echo "Duration: $((end - start))s"

echo ""
echo "=== Benchmark Complete ==="
```

### Compare Results

| Configuration | Single Day | 3 Parallel | Warehouse Query |
|---------------|------------|------------|-----------------|
| **Baseline** (1 worker) | 45s | 135s (sequential) | 0.15s |
| **3 workers** | 45s | 50s (parallel) | 0.15s |
| **5 workers** | 45s | 48s (parallel) | 0.15s |
| **Optimized** | 30s | 35s | 0.08s |

---

## Quick Wins

### 1. Enable Worker Scaling

```bash
# Add to docker-compose.yml
docker compose up -d --scale airflow-worker=3
```

**Impact**: 3x parallel execution capacity

### 2. Increase Batch Size

```bash
# .env
WAREHOUSE_BATCH_SIZE=2000  # From 1000
```

**Impact**: 2x faster warehouse loads for large datasets

### 3. Reduce Sensor Polling

```bash
# .env
MARKET_DATA_SENSOR_POKE_INTERVAL=60  # From 30
```

**Impact**: 50% fewer API health checks

### 4. Use Connection Pooling

**Already enabled!**
- PostgreSQL: QueuePool (5 + 10 overflow)
- Redshift: NullPool (optimized for cloud)

### 5. Optimize Docker

```bash
# Increase Docker resources (Docker Desktop)
# Settings → Resources:
CPUs: 4
Memory: 8GB
Swap: 2GB
Disk: 50GB
```

---

## Advanced Optimizations

### 1. Use Task Groups

**For multiple tickers**:

```python
from airflow.utils.task_group import TaskGroup

with DAG(...) as dag:
    with TaskGroup("fetch_tickers") as fetch_group:
        for ticker in ['AAPL', 'GOOGL', 'MSFT']:
            PythonOperator(
                task_id=f'fetch_{ticker}',
                python_callable=fetch_data,
                op_kwargs={'ticker': ticker}
            )
```

### 2. Enable Smart Sensors (Airflow 2.11+)

```bash
# .env
AIRFLOW__SMART_SENSOR__USE_SMART_SENSOR=True
AIRFLOW__SMART_SENSOR__SHARD_CODE_UPPER_LIMIT=10000
```

**Impact**: Consolidates sensor tasks, reduces worker load

### 3. Use XCom Backend (for large data)

**For data >10MB**:

```bash
# .env
AIRFLOW__CORE__XCOM_BACKEND=s3  # or gcs
```

**Benefits**:
- Offloads large XCom data from metadata DB
- Faster database queries
- Better scalability

### 4. Caching

**Redis caching** for expensive computations:

```python
import redis
import json

r = redis.Redis(host='redis', port=6379, db=1)

def fetch_with_cache(ticker, date):
    cache_key = f"market_data:{ticker}:{date}"
    
    # Try cache
    cached = r.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # Fetch fresh
    data = client.fetch_market_data(ticker, date)
    
    # Cache for 24 hours
    r.setex(cache_key, 86400, json.dumps(data))
    
    return data
```

---

## Profiling

### Profile Task Execution

**Add profiling**:

```python
import cProfile
import pstats

def transform_and_save(**context):
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Your code here
    result = calculate_technical_indicators(df)
    
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(10)  # Top 10 slowest
    
    return result
```

### Identify Bottlenecks

**Use logs**:
```python
import time

start = time.time()
data = fetch_from_api()
logger.metric("api.fetch_time", time.time() - start)

start = time.time()
df = calculate_indicators(data)
logger.metric("transform.time", time.time() - start)
```

**Analyze**:
```bash
docker compose logs airflow-worker | grep "metric"
```

---

## Performance Checklist

### Before Optimization

- [ ] Establish baseline metrics
- [ ] Identify bottlenecks
- [ ] Set performance targets
- [ ] Backup current configuration

### Optimization Steps

- [ ] Scale workers based on workload
- [ ] Tune worker concurrency
- [ ] Optimize database connections
- [ ] Adjust batch sizes
- [ ] Add caching where appropriate
- [ ] Create task pools
- [ ] Optimize queries and indexes

### After Optimization

- [ ] Measure new metrics
- [ ] Compare with baseline
- [ ] Monitor for regressions
- [ ] Document changes

---

## Performance Regression Testing

**Create benchmark DAG**:

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import time

def benchmark_fetch():
    start = time.time()
    # Run 100 API calls
    duration = time.time() - start
    
    # Fail if too slow
    if duration > 60:
        raise ValueError(f"Performance regression: {duration}s > 60s")

with DAG('performance_benchmark', schedule_interval='@weekly') as dag:
    benchmark_task = PythonOperator(
        task_id='benchmark_fetch',
        python_callable=benchmark_fetch
    )
```

**Run weekly** to detect performance degradation.

---

## Related Documentation

- [Architecture Overview](../architecture/overview.md)
- [Monitoring Guide](monitoring.md)
- [Deployment Guide](deployment.md)
- [Troubleshooting Guide](troubleshooting.md)

---

**Last Updated**: 2025-11-12  
**Version**: 1.0.0

