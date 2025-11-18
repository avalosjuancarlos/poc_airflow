# Deployment Guide

Production deployment guide for Airflow Market Data Pipeline.

---

## Table of Contents

- [Deployment Options](#deployment-options)
- [Production Requirements](#production-requirements)
- [Docker Deployment](#docker-deployment)
- [Cloud Deployment](#cloud-deployment)
- [Post-Deployment](#post-deployment)
- [Rollback Procedures](#rollback-procedures)

---

## Deployment Options

### Option 1: Docker Compose (Recommended for Small-Medium Scale)

**Best for**:
- Single server deployment
- 1-5 concurrent DAG runs
- < 1TB data volume
- Development, staging, and small production

**Pros**:
- ✅ Simple setup
- ✅ Resource efficient
- ✅ Easy maintenance
- ✅ Cost-effective

**Cons**:
- ❌ Single point of failure
- ❌ Limited scalability
- ❌ Manual scaling

### Option 2: Kubernetes (Recommended for Large Scale)

**Best for**:
- Enterprise deployments
- 10+ concurrent DAG runs
- Multi-region requirements
- High availability needs

**Pros**:
- ✅ Auto-scaling
- ✅ High availability
- ✅ Multi-region support
- ✅ Self-healing

**Cons**:
- ❌ Complex setup
- ❌ Higher costs
- ❌ Requires K8s expertise

### Option 3: Managed Services

**Options**:
- AWS MWAA (Managed Workflows for Apache Airflow)
- Google Cloud Composer
- Astronomer

**Pros**:
- ✅ Fully managed
- ✅ Auto-scaling
- ✅ Built-in monitoring

**Cons**:
- ❌ Vendor lock-in
- ❌ Higher costs
- ❌ Less control

---

## Production Requirements

### Hardware Requirements

**Minimum** (1-3 DAG runs):
```
CPU: 4 cores
RAM: 8GB
Disk: 50GB SSD
Network: 100 Mbps
```

**Recommended** (5-10 DAG runs):
```
CPU: 8 cores
RAM: 16GB
Disk: 200GB SSD
Network: 1 Gbps
```

**High Load** (10+ DAG runs):
```
CPU: 16+ cores
RAM: 32GB+
Disk: 500GB+ SSD (NVMe recommended)
Network: 10 Gbps
```

### Software Requirements

```
OS: Ubuntu 20.04 LTS or later
Docker: 20.10+
Docker Compose: 2.0+
Python: 3.10 (in containers)
```

---

## Docker Deployment

### 1. Server Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version
```

### 2. Clone Repository

```bash
# Clone to production directory
cd /opt
sudo git clone https://github.com/avalosjuancarlos/poc_airflow.git airflow-production
cd airflow-production

# Set ownership
sudo chown -R $USER:$USER /opt/airflow-production
```

### 3. Production Configuration

```bash
# Copy and edit environment file
cp env.template .env
nano .env
```

**Critical Production Settings**:

```bash
# === SECURITY ===
_AIRFLOW_WWW_USER_USERNAME=admin
_AIRFLOW_WWW_USER_PASSWORD=<STRONG_PASSWORD>
AIRFLOW__WEBSERVER__SECRET_KEY=<GENERATE_SECURE_KEY>

# === ENVIRONMENT ===
ENVIRONMENT=production

# === LOGGING ===
AIRFLOW__LOGGING__LEVEL=INFO
AIRFLOW__LOGGING__JSON_FORMAT=true

# === PRODUCTION WAREHOUSE ===
PROD_WAREHOUSE_TYPE=redshift
PROD_WAREHOUSE_HOST=your-prod-cluster.region.redshift.amazonaws.com
PROD_WAREHOUSE_DATABASE=market_data_prod
PROD_WAREHOUSE_USER=<WAREHOUSE_USER>
PROD_WAREHOUSE_PASSWORD=<WAREHOUSE_PASSWORD>

# === MONITORING (Optional) ===
# Optional: Add Sentry/Datadog (see docs/user-guide/logging.md)
# SENTRY_DSN=https://your-key@sentry.io/project
# DD_API_KEY=<DATADOG_API_KEY>

# === RESOURCES ===
AIRFLOW__CELERY__WORKER_CONCURRENCY=16
AIRFLOW__CORE__PARALLELISM=32
AIRFLOW__CORE__MAX_ACTIVE_TASKS_PER_DAG=16
```

**Generate Secure Secret Key**:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 4. Docker Compose Production Override

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  airflow-webserver:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
    restart: always
    
  airflow-scheduler:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
    restart: always
  
  airflow-worker:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
      replicas: 3
    restart: always
  
  postgres:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 2G
    restart: always
    volumes:
      - postgres-db-volume:/var/lib/postgresql/data
      - ./backups:/backups  # For automatic backups
  
  redis:
    restart: always
  
  warehouse-postgres:
    restart: always
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
```

### 5. Initialize & Start

```bash
# Initialize Airflow database
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up airflow-init

# Start all services
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Scale workers
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --scale airflow-worker=3

# Verify all services are healthy
docker-compose ps
```

### 6. Verify Deployment

```bash
# Check service health
curl http://localhost:8080/health

# Check logs
docker-compose logs --tail=100 airflow-scheduler
docker-compose logs --tail=100 airflow-worker

# Test DAG
docker-compose exec airflow-scheduler airflow dags test get_market_data 2025-11-12
```

---

## Cloud Deployment

### AWS Deployment

#### Using EC2 + Docker Compose

**1. Launch EC2 Instance**:
```
Instance Type: t3.xlarge (4 vCPU, 16GB RAM)
AMI: Ubuntu 20.04 LTS
Storage: 100GB GP3 SSD
Security Group: Allow 22, 8080, 5555
```

**2. Setup**:
```bash
# SSH to instance
ssh -i your-key.pem ubuntu@<EC2_IP>

# Follow Docker Deployment steps above
```

**3. Configure Security Groups**:
```
Inbound Rules:
- Port 22 (SSH): Your IP only
- Port 8080 (Webserver): VPN/Office IP range
- Port 5555 (Flower): Admin IPs only

Outbound Rules:
- Allow all (for API calls, package installs)
```

#### Using AWS MWAA (Managed Airflow)

**Pros**:
- Fully managed
- Auto-scaling
- Built-in monitoring

**Setup**:
1. Create S3 bucket for DAGs
2. Upload `dags/` folder to S3
3. Create MWAA environment via AWS Console
4. Configure:
   - Environment class: mw1.medium
   - Min workers: 1
   - Max workers: 5
   - Scheduler: 2 (HA)

**Cost**: ~$300-500/month for small deployment

---

## Post-Deployment

### 1. SSL/TLS Configuration

**Using nginx Reverse Proxy**:

```nginx
# /etc/nginx/sites-available/airflow
server {
    listen 443 ssl;
    server_name airflow.yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/airflow.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/airflow.yourdomain.com/privkey.pem;
    
    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/airflow /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 2. Monitoring Setup

**Prometheus + Grafana** (Recommended):

```yaml
# Add to docker-compose.prod.yml
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
  
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=<ADMIN_PASSWORD>
```

### 3. Automated Backups

**Metadata DB Backup**:

Create `/opt/airflow-production/scripts/backup.sh`:

```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/airflow-production/backups"

# Backup metadata DB
docker compose exec -T postgres pg_dump -U airflow airflow > "$BACKUP_DIR/metadata_$DATE.sql"

# Backup warehouse
docker compose exec -T warehouse-postgres pg_dump -U warehouse_user market_data_warehouse > "$BACKUP_DIR/warehouse_$DATE.sql"

# Compress
gzip "$BACKUP_DIR/metadata_$DATE.sql"
gzip "$BACKUP_DIR/warehouse_$DATE.sql"

# Rotate (keep last 30 days)
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
```

**Cron Job**:
```bash
# Run daily at 2 AM
0 2 * * * /opt/airflow-production/scripts/backup.sh >> /var/log/airflow-backup.log 2>&1
```

### 4. Log Rotation

**logrotate Configuration**:

```bash
# /etc/logrotate.d/airflow
/opt/airflow-production/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 airflow airflow
    sharedscripts
    postrotate
        docker compose -f /opt/airflow-production/docker-compose.yml restart airflow-scheduler
    endscript
}
```

---

## Rollback Procedures

### Application Rollback

```bash
# 1. Stop services
docker-compose down

# 2. Checkout previous version
git log --oneline -10  # Find commit
git checkout <PREVIOUS_COMMIT>

# 3. Restart services
docker-compose up -d

# 4. Verify
docker-compose ps
curl http://localhost:8080/health
```

### Database Rollback

```bash
# 1. Stop Airflow services
docker-compose stop airflow-scheduler airflow-webserver airflow-worker

# 2. Restore backup
docker compose exec -T postgres psql -U airflow -d airflow < backups/metadata_YYYYMMDD_HHMMSS.sql.gz

# 3. Restart services
docker-compose start airflow-scheduler airflow-webserver airflow-worker
```

### Blue-Green Deployment (Zero Downtime)

**Setup**:
1. Clone deployment to new directory: `/opt/airflow-blue` and `/opt/airflow-green`
2. Configure nginx to route traffic
3. Deploy to inactive environment
4. Test inactive environment
5. Switch nginx traffic
6. Monitor for issues
7. Rollback if needed (switch nginx back)

---

## Health Checks

### Automated Health Check Script

```bash
#!/bin/bash
# /opt/airflow-production/scripts/healthcheck.sh

echo "=== Airflow Health Check ==="
echo ""

# Check if containers are running
echo "1. Container Status:"
docker-compose ps | grep "Up"

# Check Airflow health endpoint
echo ""
echo "2. Airflow API Health:"
curl -s http://localhost:8080/health | jq '.'

# Check scheduler last heartbeat
echo ""
echo "3. Scheduler Heartbeat:"
docker-compose exec -T postgres psql -U airflow -d airflow -c \
  "SELECT MAX(latest_heartbeat) FROM job WHERE job_type='SchedulerJob';"

# Check recent task failures
echo ""
echo "4. Recent Task Failures (last hour):"
docker-compose exec -T postgres psql -U airflow -d airflow -c \
  "SELECT COUNT(*) FROM task_instance WHERE state='failed' AND start_date > NOW() - INTERVAL '1 hour';"

# Check warehouse connection
echo ""
echo "5. Warehouse Connection:"
docker-compose exec -T warehouse-postgres psql -U warehouse_user -d market_data_warehouse -c \
  "SELECT COUNT(*) FROM fact_market_data;"
```

**Run via cron** (every 5 minutes):
```
*/5 * * * * /opt/airflow-production/scripts/healthcheck.sh >> /var/log/airflow-health.log 2>&1
```

---

## Related Documentation

- [Architecture Overview](../architecture/overview.md)
- [Monitoring Guide](monitoring.md)
- [Troubleshooting Guide](troubleshooting.md)
- [Security Best Practices](../../SECURITY.md)

---

**Last Updated**: 2025-11-12  
**Version**: 1.0.0

