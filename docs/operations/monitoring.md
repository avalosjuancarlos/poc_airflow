# Monitoring & Observability Guide

Comprehensive monitoring setup for Airflow Market Data Pipeline.

---

## Table of Contents

- [Monitoring Strategy](#monitoring-strategy)
- [Metrics to Track](#metrics-to-track)
- [Airflow Native Monitoring](#airflow-native-monitoring)
- [External Monitoring Tools](#external-monitoring-tools)
- [Alerting](#alerting)
- [Dashboards](#dashboards)

---

## Monitoring Strategy

### The Four Golden Signals

| Signal | Metric | Target | Alert Threshold |
|--------|--------|--------|-----------------|
| **Latency** | Task duration | < 2 min avg | > 5 min |
| **Traffic** | DAG runs/hour | 24 (hourly) | < 20 |
| **Errors** | Task failures | < 1% | > 5% |
| **Saturation** | Worker CPU | < 70% | > 85% |

---

## Metrics to Track

### Airflow Metrics

**DAG Metrics**:
- DAG run duration
- DAG run success rate
- DAG parse time
- Number of active DAG runs

**Task Metrics**:
- Task duration by task_id
- Task success/failure rate
- Task retry count
- Task queue time

**Infrastructure Metrics**:
- Scheduler heartbeat
- Worker availability
- Executor queue length
- Database connections

**Business Metrics**:
- Market data records fetched
- Technical indicators calculated
- Warehouse records loaded
- API call success rate

---

## Airflow Native Monitoring

### 1. Airflow UI

**Health Status**:
```
Navigate to: Admin → Health
```

Shows:
- ✅ Metadata database
- ✅ Scheduler
- ✅ Triggerer (if enabled)

**DAG Stats**:
```
Navigate to: Home (DAGs list)
```

View:
- Last run status
- Next run time
- Success/failure stats

### 2. Airflow Metrics

**Enable StatsD**:

```bash
# Add to .env
AIRFLOW__METRICS__STATSD_ON=True
AIRFLOW__METRICS__STATSD_HOST=statsd
AIRFLOW__METRICS__STATSD_PORT=8125
AIRFLOW__METRICS__STATSD_PREFIX=airflow
```

**Add StatsD to docker-compose**:

```yaml
services:
  statsd:
    image: prom/statsd-exporter:latest
    ports:
      - "9102:9102"
      - "8125:9125/udp"
    command:
      - '--statsd.mapping-config=/tmp/statsd_mapping.yml'
    volumes:
      - ./monitoring/statsd_mapping.yml:/tmp/statsd_mapping.yml
```

### 3. Flower (Celery Monitor)

**Access**: http://localhost:5555

**Metrics Available**:
- Active workers
- Tasks processed
- Task success/failure rate
- Worker resource usage
- Queue lengths

**Enable**:
```bash
docker-compose --profile flower up -d
```

---

## External Monitoring Tools

### Option 1: Prometheus + Grafana (Recommended)

#### Setup Prometheus

**docker-compose.monitoring.yml**:

```yaml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=30d'
    restart: unless-stopped
  
  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./monitoring/grafana/datasources:/etc/grafana/provisioning/datasources
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    restart: unless-stopped
  
  node-exporter:
    image: prom/node-exporter:latest
    container_name: node_exporter
    ports:
      - "9100:9100"
    restart: unless-stopped
  
  postgres-exporter:
    image: prometheuscommunity/postgres-exporter:latest
    container_name: postgres_exporter
    ports:
      - "9187:9187"
    environment:
      - DATA_SOURCE_NAME=postgresql://airflow:airflow@postgres:5432/airflow?sslmode=disable
    restart: unless-stopped

volumes:
  prometheus_data:
  grafana_data:
```

**prometheus.yml**:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  # Airflow metrics (via StatsD exporter)
  - job_name: 'airflow'
    static_configs:
      - targets: ['statsd:9102']
  
  # Node metrics
  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']
  
  # PostgreSQL metrics
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']
  
  # Flower metrics (Celery)
  - job_name: 'flower'
    static_configs:
      - targets: ['flower:5555']
    metrics_path: '/metrics'
```

**Start Monitoring Stack**:

```bash
docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d
```

**Access**:
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)

#### Grafana Dashboards

**Import Pre-built Dashboards**:

1. Airflow Dashboard: https://grafana.com/grafana/dashboards/11022
2. PostgreSQL Dashboard: https://grafana.com/grafana/dashboards/9628
3. Node Exporter: https://grafana.com/grafana/dashboards/1860

**Custom Market Data Dashboard**:

```json
{
  "dashboard": {
    "title": "Market Data Pipeline",
    "panels": [
      {
        "title": "DAG Run Success Rate",
        "targets": [
          {
            "expr": "rate(airflow_dag_run_success_total[5m])"
          }
        ]
      },
      {
        "title": "Records Fetched (Last Hour)",
        "targets": [
          {
            "expr": "sum(increase(market_data_records_fetched_total[1h]))"
          }
        ]
      },
      {
        "title": "Warehouse Load Latency",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(warehouse_load_duration_seconds_bucket[5m]))"
          }
        ]
      }
    ]
  }
}
```

### Option 2: Datadog

**Installation**:

```yaml
# Add to docker-compose.yml
  datadog:
    image: datadog/agent:latest
    environment:
      - DD_API_KEY=${DD_API_KEY}
      - DD_SITE=datadoghq.com
      - DD_APM_ENABLED=true
      - DD_LOGS_ENABLED=true
      - DD_DOGSTATSD_NON_LOCAL_TRAFFIC=true
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - /proc/:/host/proc/:ro
      - /sys/fs/cgroup/:/host/sys/fs/cgroup:ro
```

**Configure Airflow**:

```bash
# Add to .env
AIRFLOW__METRICS__STATSD_ON=True
AIRFLOW__METRICS__STATSD_HOST=datadog
AIRFLOW__METRICS__STATSD_PORT=8125
```

**Python Instrumentation**:

```python
# Add to DAG
from ddtrace import tracer

@tracer.wrap()
def fetch_market_data(**context):
    # Your code here
    pass
```

### Option 3: Sentry (Error Tracking)

**Installation**:

```bash
# Add to requirements.txt
sentry-sdk==1.40.0
```

**Configure**:

```bash
# Add to .env
SENTRY_DSN=https://your-key@sentry.io/project
```

**Integration** (already implemented):

```python
# dags/market_data/utils/logger.py
import sentry_sdk

if SENTRY_DSN:
    sentry_sdk.init(dsn=SENTRY_DSN, environment=ENVIRONMENT)
```

---

## Alerting

### Prometheus Alertmanager

**alertmanager.yml**:

```yaml
global:
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_from: 'airflow-alerts@yourdomain.com'
  smtp_auth_username: 'your-email@gmail.com'
  smtp_auth_password: 'your-app-password'

route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'team-email'

receivers:
  - name: 'team-email'
    email_configs:
      - to: 'team@yourdomain.com'
  
  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: '<PAGERDUTY_KEY>'
```

**Alert Rules** (alerts.yml):

```yaml
groups:
  - name: airflow_alerts
    interval: 30s
    rules:
      # DAG Failure Rate
      - alert: HighDAGFailureRate
        expr: |
          rate(airflow_dag_run_failed_total[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High DAG failure rate detected"
          description: "{{ $value }}% of DAG runs are failing"
      
      # Scheduler Heartbeat
      - alert: SchedulerDown
        expr: |
          time() - airflow_scheduler_heartbeat > 120
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Airflow Scheduler is down"
          description: "No heartbeat from scheduler for 2+ minutes"
      
      # Worker Availability
      - alert: NoWorkersAvailable
        expr: |
          airflow_celery_workers < 1
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "No Celery workers available"
          description: "All workers are down or unreachable"
      
      # Database Connections
      - alert: HighDatabaseConnections
        expr: |
          pg_stat_activity_count > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High database connection usage"
          description: "{{ $value }} connections active (>80)"
      
      # Disk Usage
      - alert: HighDiskUsage
        expr: |
          (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}) < 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Low disk space"
          description: "Only {{ $value }}% disk space remaining"
```

### Slack Integration

**Slack Webhook** (alertmanager.yml):

```yaml
receivers:
  - name: 'slack-notifications'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
        channel: '#airflow-alerts'
        title: '{{ .GroupLabels.alertname }}'
        text: '{{ .Annotations.description }}'
        send_resolved: true
```

### Email Alerts via Airflow

**Configure Email** (.env):

```bash
AIRFLOW__SMTP__SMTP_HOST=smtp.gmail.com
AIRFLOW__SMTP__SMTP_STARTTLS=True
AIRFLOW__SMTP__SMTP_SSL=False
AIRFLOW__SMTP__SMTP_USER=your-email@gmail.com
AIRFLOW__SMTP__SMTP_PASSWORD=your-app-password
AIRFLOW__SMTP__SMTP_PORT=587
AIRFLOW__SMTP__SMTP_MAIL_FROM=airflow@yourdomain.com
```

**DAG Email Alerts**:

```python
default_args = {
    'owner': 'airflow',
    'email': ['team@yourdomain.com'],
    'email_on_failure': True,
    'email_on_retry': False,
}
```

---

## Dashboards

### Key Dashboards to Create

#### 1. Executive Dashboard
- Total DAG runs today
- Success rate (%)
- Records processed
- System health status

#### 2. Operations Dashboard
- Active workers
- Task queue length
- Database connections
- CPU/Memory usage

#### 3. Business Dashboard
- Market data coverage (tickers)
- Data freshness (last update)
- Warehouse size (records)
- API call statistics

#### 4. Performance Dashboard
- P50/P95/P99 task durations
- Slowest tasks
- Retry rates by task
- Worker utilization

### Sample Queries

**DAG Success Rate (Last 24h)**:
```sql
SELECT 
    COUNT(CASE WHEN state='success' THEN 1 END) * 100.0 / COUNT(*) as success_rate
FROM dag_run
WHERE start_date > NOW() - INTERVAL '24 hours';
```

**Top 10 Slowest Tasks**:
```sql
SELECT 
    task_id,
    AVG(EXTRACT(EPOCH FROM (end_date - start_date))) as avg_duration_seconds
FROM task_instance
WHERE start_date > NOW() - INTERVAL '7 days'
    AND state = 'success'
GROUP BY task_id
ORDER BY avg_duration_seconds DESC
LIMIT 10;
```

**Worker Utilization**:
```promql
# Prometheus query
rate(celery_task_sent_total[5m])
```

---

## Log Aggregation

### ELK Stack (Elasticsearch + Logstash + Kibana)

**docker-compose.elk.yml**:

```yaml
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
    ports:
      - "9200:9200"
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data
  
  logstash:
    image: docker.elastic.co/logstash/logstash:8.11.0
    ports:
      - "5000:5000"
    volumes:
      - ./monitoring/logstash.conf:/usr/share/logstash/pipeline/logstash.conf
  
  kibana:
    image: docker.elastic.co/kibana/kibana:8.11.0
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200

volumes:
  elasticsearch_data:
```

**logstash.conf**:

```
input {
  file {
    path => "/opt/airflow/logs/**/*.log"
    start_position => "beginning"
    sincedb_path => "/dev/null"
  }
}

filter {
  grok {
    match => { "message" => "%{TIMESTAMP_ISO8601:timestamp} - %{LOGLEVEL:level} - %{GREEDYDATA:message}" }
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "airflow-logs-%{+YYYY.MM.dd}"
  }
}
```

---

## Health Check Script

**comprehensive_healthcheck.sh**:

```bash
#!/bin/bash

echo "=== AIRFLOW HEALTH CHECK ==="
echo "Timestamp: $(date)"
echo ""

# 1. Container Status
echo "1. Docker Containers:"
docker-compose ps --format "table {{.Service}}\t{{.Status}}\t{{.Ports}}"
echo ""

# 2. Airflow Health Endpoint
echo "2. Airflow Health:"
curl -s http://localhost:8080/health | jq '.'
echo ""

# 3. Scheduler Heartbeat
echo "3. Scheduler Heartbeat:"
docker-compose exec -T postgres psql -U airflow -d airflow -tAc \
  "SELECT EXTRACT(EPOCH FROM (NOW() - MAX(latest_heartbeat))) as seconds_since_heartbeat FROM job WHERE job_type='SchedulerJob';"
echo ""

# 4. Active Workers
echo "4. Active Celery Workers:"
docker-compose exec -T airflow-scheduler airflow celery inspect active | jq 'keys | length'
echo ""

# 5. DAG Runs (Last 24h)
echo "5. DAG Runs (Last 24h):"
docker-compose exec -T postgres psql -U airflow -d airflow -tAc \
  "SELECT state, COUNT(*) FROM dag_run WHERE start_date > NOW() - INTERVAL '24 hours' GROUP BY state;"
echo ""

# 6. Task Failures (Last hour)
echo "6. Task Failures (Last hour):"
docker-compose exec -T postgres psql -U airflow -d airflow -tAc \
  "SELECT COUNT(*) FROM task_instance WHERE state='failed' AND start_date > NOW() - INTERVAL '1 hour';"
echo ""

# 7. Database Connections
echo "7. Database Connections:"
docker-compose exec -T postgres psql -U airflow -d airflow -tAc \
  "SELECT COUNT(*) FROM pg_stat_activity;"
echo ""

# 8. Disk Usage
echo "8. Disk Usage:"
df -h | grep -E '(/opt/airflow|/var/lib/docker)'
echo ""

# 9. Warehouse Records
echo "9. Warehouse Records:"
docker-compose exec -T warehouse-postgres psql -U warehouse_user -d market_data_warehouse -tAc \
  "SELECT COUNT(*) as total_records FROM fact_market_data;"
echo ""

echo "=== HEALTH CHECK COMPLETE ==="
```

---

## Related Documentation

- [Architecture Overview](../architecture/overview.md)
- [Deployment Guide](deployment.md)
- [Troubleshooting Guide](troubleshooting.md)
- [Configuration Guide](../user-guide/configuration.md)

---

**Last Updated**: 2025-11-12  
**Version**: 1.0.0

