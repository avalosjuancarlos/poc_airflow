# CLI Commands Reference

Complete command reference for Airflow CLI.

---

## Table of Contents

- [Docker Compose Commands](#docker-compose-commands)
- [Airflow DAG Commands](#airflow-dag-commands)
- [Airflow Task Commands](#airflow-task-commands)
- [Database Commands](#database-commands)
- [Maintenance Commands](#maintenance-commands)

---

## Docker Compose Commands

### Service Management

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# Restart a specific service
docker-compose restart airflow-scheduler

# View service logs
docker-compose logs -f airflow-scheduler

# Check service status
docker-compose ps

# Scale workers
docker-compose up -d --scale airflow-worker=5

# Rebuild services
docker-compose build
docker-compose up -d --force-recreate
```

### Maintenance

```bash
# Remove stopped containers
docker-compose down

# Remove volumes (⚠️ deletes data)
docker-compose down -v

# View resource usage
docker stats

# Clean up Docker
docker system prune -a
```

---

## Airflow DAG Commands

### List DAGs

```bash
# List all DAGs
docker-compose exec airflow-scheduler airflow dags list

# Show DAG details
docker-compose exec airflow-scheduler airflow dags show get_market_data

# List import errors
docker-compose exec airflow-scheduler airflow dags list-import-errors
```

### Trigger DAGs

```bash
# Trigger with default parameters
docker-compose exec airflow-scheduler airflow dags trigger get_market_data

# Trigger with custom parameters
docker-compose exec airflow-scheduler airflow dags trigger get_market_data \
  --conf '{"ticker": "TSLA"}'

# Trigger for specific execution date
docker-compose exec airflow-scheduler airflow dags trigger get_market_data \
  --exec-date "2025-11-12"
```

### Pause/Unpause DAGs

```bash
# Pause DAG
docker-compose exec airflow-scheduler airflow dags pause get_market_data

# Unpause DAG
docker-compose exec airflow-scheduler airflow dags unpause get_market_data
```

### Backfill DAGs

```bash
# Backfill for date range
docker-compose exec airflow-scheduler airflow dags backfill get_market_data \
  --start-date 2025-11-01 \
  --end-date 2025-11-10

# Backfill with reset (ignore previous runs)
docker-compose exec airflow-scheduler airflow dags backfill get_market_data \
  --start-date 2025-11-01 \
  --end-date 2025-11-10 \
  --reset-dagruns
```

---

## Airflow Task Commands

### Test Tasks

```bash
# Test a specific task
docker-compose exec airflow-scheduler airflow tasks test get_market_data validate_ticker 2025-11-12

# Test with parameters
docker-compose exec airflow-scheduler airflow tasks test get_market_data fetch_data 2025-11-12 \
  --task-params '{"ticker": "AAPL"}'
```

### Clear Tasks

```bash
# Clear task instance
docker-compose exec airflow-scheduler airflow tasks clear get_market_data \
  --task-regex validate_ticker \
  --yes

# Clear all tasks for a DAG run
docker-compose exec airflow-scheduler airflow tasks clear get_market_data \
  --start-date 2025-11-12 \
  --end-date 2025-11-12 \
  --yes
```

### View Task Logs

```bash
# View task log
docker-compose exec airflow-scheduler airflow tasks logs get_market_data fetch_data 2025-11-12

# Follow log in real-time
docker-compose exec airflow-scheduler airflow tasks logs get_market_data fetch_data 2025-11-12 --follow
```

---

## Database Commands

### Airflow Metadata DB

```bash
# Connect to database
docker-compose exec postgres psql -U airflow -d airflow

# Backup database
docker-compose exec postgres pg_dump -U airflow airflow > backup.sql

# Restore database
cat backup.sql | docker-compose exec -T postgres psql -U airflow -d airflow

# Initialize/upgrade database
docker-compose up airflow-init

# Check database migrations
docker-compose exec airflow-scheduler airflow db check-migrations
```

### Warehouse DB

```bash
# Connect to warehouse
docker-compose exec warehouse-postgres psql -U warehouse_user -d market_data_warehouse

# Backup warehouse
docker-compose exec warehouse-postgres pg_dump -U warehouse_user market_data_warehouse > warehouse_backup.sql

# Restore warehouse
cat warehouse_backup.sql | docker-compose exec -T warehouse-postgres psql -U warehouse_user -d market_data_warehouse

# Query records
docker-compose exec warehouse-postgres psql -U warehouse_user -d market_data_warehouse \
  -c "SELECT COUNT(*) FROM fact_market_data;"
```

### Common SQL Queries

```bash
# DAG run statistics
docker-compose exec postgres psql -U airflow -d airflow -c \
  "SELECT state, COUNT(*) FROM dag_run GROUP BY state;"

# Recent task failures
docker-compose exec postgres psql -U airflow -d airflow -c \
  "SELECT task_id, state, start_date FROM task_instance WHERE state='failed' ORDER BY start_date DESC LIMIT 10;"

# Active connections
docker-compose exec postgres psql -U airflow -d airflow -c \
  "SELECT COUNT(*) FROM pg_stat_activity;"
```

---

## Maintenance Commands

### Airflow Variables

```bash
# List all variables
docker-compose exec airflow-scheduler airflow variables list

# Get a variable
docker-compose exec airflow-scheduler airflow variables get market_data_default_ticker

# Set a variable
docker-compose exec airflow-scheduler airflow variables set market_data_default_ticker TSLA

# Delete a variable
docker-compose exec airflow-scheduler airflow variables delete market_data_default_ticker

# Import variables from JSON
docker-compose exec airflow-scheduler airflow variables import /path/to/variables.json

# Export variables to JSON
docker-compose exec airflow-scheduler airflow variables export /path/to/variables.json
```

### Connections

```bash
# List connections
docker-compose exec airflow-scheduler airflow connections list

# Add connection
docker-compose exec airflow-scheduler airflow connections add my_postgres \
  --conn-type postgres \
  --conn-host localhost \
  --conn-login myuser \
  --conn-password mypass \
  --conn-port 5432

# Delete connection
docker-compose exec airflow-scheduler airflow connections delete my_postgres
```

### Users

```bash
# List users
docker-compose exec airflow-scheduler airflow users list

# Create admin user
docker-compose exec airflow-scheduler airflow users create \
  --username admin \
  --firstname Admin \
  --lastname User \
  --role Admin \
  --email admin@example.com \
  --password admin

# Delete user
docker-compose exec airflow-scheduler airflow users delete admin
```

### Pools

```bash
# List pools
docker-compose exec airflow-scheduler airflow pools list

# Create pool
docker-compose exec airflow-scheduler airflow pools set api_pool 5 "API call pool"

# Delete pool
docker-compose exec airflow-scheduler airflow pools delete api_pool
```

---

## Celery Commands

### Worker Management

```bash
# List active workers
docker-compose exec airflow-scheduler airflow celery inspect active

# Get worker stats
docker-compose exec airflow-scheduler airflow celery inspect stats

# Shutdown workers gracefully
docker-compose exec airflow-scheduler airflow celery stop

# View registered tasks
docker-compose exec airflow-scheduler airflow celery inspect registered
```

### Queue Management

```bash
# Purge all tasks from queue
docker-compose exec redis redis-cli FLUSHALL

# View queue length
docker-compose exec redis redis-cli LLEN celery

# Monitor queue in real-time
docker-compose exec redis redis-cli MONITOR
```

---

## Monitoring Commands

### Service Health

```bash
# Check Airflow health
curl http://localhost:8080/health

# Check specific components
curl http://localhost:8080/health | jq '.metadatabase'
curl http://localhost:8080/health | jq '.scheduler'

# View Flower (Celery monitor)
open http://localhost:5555
```

### Log Analysis

```bash
# Recent errors
docker-compose logs --tail=100 | grep -i error

# Errors from specific service
docker-compose logs airflow-scheduler | grep -i error

# Follow logs with grep
docker-compose logs -f airflow-worker | grep -i "task failed"

# Export logs
docker-compose logs > airflow_logs_$(date +%Y%m%d).txt
```

### Resource Monitoring

```bash
# Container stats
docker stats

# Specific container
docker stats airflow-worker

# CPU usage
docker stats --format "table {{.Name}}\t{{.CPUPerc}}"

# Memory usage
docker stats --format "table {{.Name}}\t{{.MemUsage}}"
```

---

## Useful One-Liners

### Quick Diagnostics

```bash
# Full health check
docker-compose ps && curl -s http://localhost:8080/health | jq && docker-compose logs --tail=20 airflow-scheduler

# Check DAG and trigger
docker-compose exec airflow-scheduler bash -c "airflow dags list-import-errors && airflow dags trigger get_market_data"

# Restart all Airflow services
docker-compose restart airflow-webserver airflow-scheduler airflow-worker airflow-triggerer

# View recent failures
docker-compose exec postgres psql -U airflow -d airflow -c "SELECT task_id, state, start_date FROM task_instance WHERE state='failed' ORDER BY start_date DESC LIMIT 5;"
```

### Data Verification

```bash
# Check Parquet files
docker-compose exec airflow-scheduler ls -lh /opt/airflow/data/

# Check warehouse records
docker-compose exec warehouse-postgres psql -U warehouse_user -d market_data_warehouse -c "SELECT ticker, COUNT(*), MIN(date), MAX(date) FROM fact_market_data GROUP BY ticker;"

# Check XCom data
docker-compose exec postgres psql -U airflow -d airflow -c "SELECT key, value FROM xcom ORDER BY timestamp DESC LIMIT 10;"
```

### Cleanup

```bash
# Clean old logs (keep last 30 days)
find ./logs -name "*.log" -mtime +30 -delete

# Clean old Parquet files (be careful!)
find ./data -name "*.parquet" -mtime +90 -delete

# Docker cleanup
docker system prune -af && docker volume prune -f
```

---

## Aliases (Add to ~/.bashrc)

```bash
# Airflow aliases
alias af-scheduler='docker-compose exec airflow-scheduler airflow'
alias af-logs='docker-compose logs -f'
alias af-restart='docker-compose restart airflow-scheduler airflow-webserver airflow-worker'
alias af-ps='docker-compose ps'

# Usage:
# af-scheduler dags list
# af-logs airflow-scheduler
# af-restart
# af-ps
```

---

## Related Documentation

- [Configuration Guide](../user-guide/configuration.md)
- [Troubleshooting Guide](../operations/troubleshooting.md)
- [Environment Variables Reference](environment-variables.md)

---

**Last Updated**: 2025-11-12  
**Version**: 1.0.0

