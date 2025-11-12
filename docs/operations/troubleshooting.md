# Troubleshooting Guide

Common issues and solutions for Airflow Market Data Pipeline.

---

## Table of Contents

- [Quick Diagnostics](#quick-diagnostics)
- [Service Issues](#service-issues)
- [DAG Issues](#dag-issues)
- [Task Failures](#task-failures)
- [Performance Issues](#performance-issues)
- [Database Issues](#database-issues)
- [Network Issues](#network-issues)

---

## Quick Diagnostics

### Health Check One-Liner

```bash
# Run all basic checks
docker-compose ps && \
curl -s http://localhost:8080/health | jq && \
docker-compose logs --tail=20 airflow-scheduler
```

### Common Commands

```bash
# View logs
docker-compose logs -f airflow-scheduler
docker-compose logs -f airflow-worker
docker-compose logs -f postgres

# Restart services
docker-compose restart airflow-scheduler
docker-compose restart airflow-worker

# Check resource usage
docker stats

# List import errors
docker-compose exec airflow-scheduler airflow dags list-import-errors
```

---

## Service Issues

### 1. Services Not Starting

**Symptom**: `docker-compose up` fails or containers exit immediately

**Diagnosis**:
```bash
# Check container logs
docker-compose logs airflow-scheduler

# Check Docker daemon
sudo systemctl status docker

# Check disk space
df -h
```

**Common Causes & Solutions**:

| Cause | Solution |
|-------|----------|
| **Out of disk space** | Free up space: `docker system prune -a` |
| **Port already in use** | Change ports in `docker-compose.yml` |
| **Permission errors (Linux)** | `sudo chown -R $(id -u):$(id -g) dags logs plugins` |
| **Init failed** | Run `docker-compose up airflow-init` again |
| **Old containers** | `docker-compose down -v` then restart |

### 2. Webserver Not Accessible

**Symptom**: Cannot access http://localhost:8080

**Diagnosis**:
```bash
# Check if webserver is running
docker-compose ps airflow-webserver

# Check port binding
netstat -tuln | grep 8080

# Test from inside container
docker-compose exec airflow-webserver curl localhost:8080/health
```

**Solutions**:

1. **Port conflict**:
   ```yaml
   # docker-compose.yml
   airflow-webserver:
     ports:
       - "8081:8080"  # Use different port
   ```

2. **Firewall blocking**:
   ```bash
   # Ubuntu/Debian
   sudo ufw allow 8080
   
   # CentOS/RHEL
   sudo firewall-cmd --add-port=8080/tcp --permanent
   sudo firewall-cmd --reload
   ```

3. **Container crashed**:
   ```bash
   docker-compose logs airflow-webserver
   docker-compose restart airflow-webserver
   ```

### 3. Scheduler Not Picking Up DAGs

**Symptom**: DAGs not appearing in UI

**Diagnosis**:
```bash
# Check for import errors
docker-compose exec airflow-scheduler airflow dags list-import-errors

# Check DAG folder
docker-compose exec airflow-scheduler ls -la /opt/airflow/dags/

# Check scheduler logs
docker-compose logs --tail=50 airflow-scheduler
```

**Solutions**:

1. **Python syntax error**:
   ```bash
   # Test DAG file
   python3 dags/get_market_data_dag.py
   ```

2. **Missing imports**:
   ```bash
   # Add to requirements.txt and rebuild
   docker-compose build airflow-scheduler
   docker-compose up -d airflow-scheduler
   ```

3. **File permissions**:
   ```bash
   chmod 644 dags/*.py
   ```

### 4. Workers Not Picking Up Tasks

**Symptom**: Tasks stuck in "queued" state

**Diagnosis**:
```bash
# Check worker status
docker-compose ps airflow-worker

# Check Celery status
docker-compose exec airflow-scheduler airflow celery inspect active

# Check Redis
docker-compose exec redis redis-cli ping
```

**Solutions**:

1. **Worker crashed**:
   ```bash
   docker-compose restart airflow-worker
   ```

2. **Redis down**:
   ```bash
   docker-compose restart redis
   ```

3. **Queue full**:
   ```bash
   # Clear queue
   docker-compose exec redis redis-cli FLUSHALL
   # Restart workers
   docker-compose restart airflow-worker
   ```

---

## DAG Issues

### 1. DAG Not Running on Schedule

**Diagnosis**:
```bash
# Check DAG schedule
docker-compose exec airflow-scheduler airflow dags show get_market_data

# Check if DAG is paused
docker-compose exec airflow-scheduler airflow dags list | grep get_market_data
```

**Solutions**:

1. **DAG is paused**:
   ```bash
   # Unpause DAG
   docker-compose exec airflow-scheduler airflow dags unpause get_market_data
   ```

2. **Start date in future**:
   ```python
   # Update DAG
   start_date=datetime(2025, 1, 1)  # Must be in past
   ```

3. **Catchup disabled**:
   ```python
   # Enable catchup if needed
   dag = DAG(
       'get_market_data',
       catchup=False,  # Change to True for backfill
   )
   ```

### 2. Import Errors

**Common Errors**:

#### ModuleNotFoundError

```
ImportError: No module named 'requests'
```

**Solution**:
```bash
# Add to requirements.txt
echo "requests==2.32.5" >> requirements.txt

# Rebuild
docker-compose build
docker-compose up -d
```

#### Circular Import

```
ImportError: cannot import name 'get_logger' from partially initialized module
```

**Solution**: Use lazy imports
```python
def _get_logger():
    """Lazy import to avoid circular dependency"""
    from market_data.utils import get_logger
    return get_logger(__name__)
```

### 3. DAG Timeout

**Symptom**: Tasks fail with "Task exceeded maximum runtime"

**Solution**:
```python
# Increase task timeout
task = PythonOperator(
    task_id='long_running_task',
    execution_timeout=timedelta(hours=2),  # Default: None
)
```

---

## Task Failures

### 1. API Call Failures

#### Yahoo Finance 429 (Rate Limit)

**Error**:
```
429 Client Error: Too Many Requests
```

**Solutions**:

1. **Respect Retry-After**:
   ```python
   # Already implemented in api_client.py
   retry_after = int(response.headers.get('Retry-After', 60))
   time.sleep(retry_after)
   ```

2. **Reduce frequency**:
   ```python
   # Increase poke_interval
   api_sensor = PythonSensor(
       poke_interval=60,  # Check every 60s instead of 30s
   )
   ```

3. **Add delays between tickers**:
   ```python
   import time
   time.sleep(5)  # 5 second delay between tickers
   ```

#### Yahoo Finance 400 (Bad Request)

**Error**:
```
400 Client Error: Bad Request
Cause: Future timestamp
```

**Solution**: Already fixed in code (smart timestamp logic)
```python
# Uses 6 PM for historical dates
# Uses current time for today (if before 6 PM)
```

### 2. Transform Failures

#### ValueError: No valid 'close' prices

**Cause**: Weekend/holiday with no market data

**Solution**: Already handled
```python
# Continues gracefully for weekends
# Only processes dates with valid data
```

#### TypeError: unsupported operand type(s) for -: 'NoneType'

**Cause**: Non-numeric data in quote

**Solution**: Already fixed
```python
# Explicit type conversion
df['close'] = pd.to_numeric(df['close'], errors='coerce')
```

### 3. Warehouse Failures

#### psycopg2.OperationalError: could not connect to server

**Solutions**:

1. **Check warehouse service**:
   ```bash
   docker-compose ps warehouse-postgres
   docker-compose logs warehouse-postgres
   ```

2. **Verify connection string**:
   ```bash
   # Test connection
   docker-compose exec warehouse-postgres psql -U warehouse_user -d market_data_warehouse
   ```

3. **Check .env configuration**:
   ```bash
   grep DEV_WAREHOUSE .env
   ```

#### psycopg2.ProgrammingError: can't adapt type 'dict'

**Cause**: Trying to insert dict columns

**Solution**: Already fixed (excludes quote, metadata columns)

---

## Performance Issues

### 1. Slow DAG Runs

**Diagnosis**:
```sql
-- Find slowest tasks
SELECT 
    task_id,
    AVG(EXTRACT(EPOCH FROM (end_date - start_date))) as avg_seconds
FROM task_instance
WHERE dag_id = 'get_market_data'
    AND state = 'success'
    AND start_date > NOW() - INTERVAL '7 days'
GROUP BY task_id
ORDER BY avg_seconds DESC;
```

**Solutions**:

1. **Increase worker count**:
   ```bash
   docker-compose up -d --scale airflow-worker=5
   ```

2. **Increase task concurrency**:
   ```bash
   # .env
   AIRFLOW__CELERY__WORKER_CONCURRENCY=32
   ```

3. **Add task pools**:
   ```python
   # Limit concurrent API calls
   task = PythonOperator(
       task_id='fetch_data',
       pool='api_pool',  # Create pool in UI: Admin → Pools
   )
   ```

### 2. High Memory Usage

**Diagnosis**:
```bash
docker stats

# Check specific container
docker stats airflow-worker
```

**Solutions**:

1. **Limit worker memory**:
   ```yaml
   # docker-compose.yml
   airflow-worker:
     deploy:
       resources:
         limits:
           memory: 2G
   ```

2. **Reduce worker concurrency**:
   ```bash
   AIRFLOW__CELERY__WORKER_CONCURRENCY=8
   ```

3. **Process data in chunks**:
   ```python
   # Use batch processing
   for chunk in pd.read_parquet('file.parquet', chunksize=1000):
       process(chunk)
   ```

### 3. Database Connection Exhaustion

**Error**:
```
sqlalchemy.exc.TimeoutError: QueuePool limit of size 5 overflow 10 reached
```

**Solutions**:

1. **Increase pool size**:
   ```bash
   AIRFLOW__DATABASE__SQL_ALCHEMY_POOL_SIZE=10
   AIRFLOW__DATABASE__SQL_ALCHEMY_MAX_OVERFLOW=20
   ```

2. **Check for connection leaks**:
   ```sql
   -- Active connections
   SELECT COUNT(*) FROM pg_stat_activity;
   
   -- Long-running queries
   SELECT pid, now() - query_start as duration, query
   FROM pg_stat_activity
   WHERE state != 'idle'
   ORDER BY duration DESC;
   ```

3. **Restart database**:
   ```bash
   docker-compose restart postgres
   ```

---

## Database Issues

### 1. Metadata DB Corruption

**Symptoms**:
- Scheduler crashes
- "database is locked" errors
- Cannot create DAG runs

**Recovery**:

```bash
# 1. Backup current DB
docker-compose exec postgres pg_dump -U airflow airflow > backup_$(date +%Y%m%d).sql

# 2. Stop Airflow services
docker-compose stop airflow-scheduler airflow-webserver airflow-worker

# 3. Reset database
docker-compose down -v
docker-compose up -d postgres
docker-compose up airflow-init

# 4. Restore from backup (if needed)
cat backup_20251112.sql | docker-compose exec -T postgres psql -U airflow -d airflow

# 5. Restart services
docker-compose up -d
```

### 2. Warehouse DB Issues

**Table doesn't exist**:

```bash
# Recreate schema
docker-compose exec warehouse-postgres psql -U warehouse_user -d market_data_warehouse \
  -f /docker-entrypoint-initdb.d/init.sql
```

**Sequence out of sync**:

```sql
-- Fix sequence
SELECT setval('fact_market_data_id_seq', 
  (SELECT MAX(id) FROM fact_market_data));
```

---

## Network Issues

### 1. Container Cannot Reach External APIs

**Test connectivity**:
```bash
docker-compose exec airflow-worker curl -I https://query2.finance.yahoo.com
```

**Solutions**:

1. **Check DNS**:
   ```bash
   docker-compose exec airflow-worker nslookup query2.finance.yahoo.com
   ```

2. **Check firewall**:
   ```bash
   # Allow outbound HTTPS
   sudo ufw allow out 443/tcp
   ```

3. **Use proxy** (if required):
   ```yaml
   # docker-compose.yml
   airflow-common:
     environment:
       - HTTP_PROXY=http://proxy.company.com:8080
       - HTTPS_PROXY=http://proxy.company.com:8080
   ```

### 2. Containers Cannot Communicate

**Test**:
```bash
# From webserver to postgres
docker-compose exec airflow-webserver ping postgres
```

**Solution**:
```bash
# Recreate network
docker-compose down
docker network prune
docker-compose up -d
```

---

## Emergency Procedures

### Complete Reset

⚠️ **WARNING**: This deletes all data

```bash
# 1. Stop all services
docker-compose down -v

# 2. Remove data
rm -rf logs/* data/*

# 3. Rebuild
docker-compose build

# 4. Initialize
docker-compose up airflow-init

# 5. Start
docker-compose up -d
```

### Backup Before Reset

```bash
# Backup everything
mkdir backup_$(date +%Y%m%d)
docker-compose exec postgres pg_dump -U airflow airflow > backup_$(date +%Y%m%d)/metadata.sql
docker-compose exec warehouse-postgres pg_dump -U warehouse_user market_data_warehouse > backup_$(date +%Y%m%d)/warehouse.sql
cp -r logs backup_$(date +%Y%m%d)/
cp -r data backup_$(date +%Y%m%d)/
tar -czf backup_$(date +%Y%m%d).tar.gz backup_$(date +%Y%m%d)
```

---

## Getting Help

### 1. Check Logs First

```bash
# Recent errors
docker-compose logs --tail=100 | grep -i error

# Specific service
docker-compose logs -f airflow-scheduler
```

### 2. Enable Debug Logging

```bash
# .env
AIRFLOW__LOGGING__LEVEL=DEBUG
```

Restart:
```bash
docker-compose restart airflow-scheduler airflow-webserver
```

### 3. Collect Diagnostics

```bash
# Create support bundle
mkdir diagnostics
docker-compose ps > diagnostics/services.txt
docker-compose logs > diagnostics/logs.txt
docker stats --no-stream > diagnostics/stats.txt
df -h > diagnostics/disk.txt
cat .env > diagnostics/env.txt  # Remove passwords before sharing!
tar -czf diagnostics_$(date +%Y%m%d).tar.gz diagnostics/
```

### 4. Community Support

- **Airflow Slack**: [apache-airflow.slack.com](https://apache-airflow.slack.com)
- **Stack Overflow**: Tag `apache-airflow`
- **GitHub Issues**: [apache/airflow](https://github.com/apache/airflow/issues)

---

## Related Documentation

- [Architecture Overview](../architecture/overview.md)
- [Deployment Guide](deployment.md)
- [Monitoring Guide](monitoring.md)
- [Configuration Guide](../user-guide/configuration.md)

---

**Last Updated**: 2025-11-12  
**Version**: 1.0.0
