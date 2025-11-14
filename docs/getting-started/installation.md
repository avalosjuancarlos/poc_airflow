# Installation Guide

Complete step-by-step installation guide for Apache Airflow Market Data Pipeline.

## Prerequisites

### Required Software

- **Docker Desktop** or Docker Engine (v20.10+)
  - Download: https://www.docker.com/products/docker-desktop
- **Docker Compose** (v2.0+)
  - Included with Docker Desktop
  - Linux standalone: https://docs.docker.com/compose/install/

### System Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| **RAM** | 4GB | 8GB+ |
| **CPU** | 2 cores | 4+ cores |
| **Disk Space** | 10GB | 20GB+ |
| **OS** | Linux, macOS, Windows 10/11 with WSL2 | - |

### Verify Installation

```bash
# Check Docker
docker --version
# Expected: Docker version 20.10.0+

# Check Docker Compose
docker compose version
# Expected: Docker Compose version v2.0.0+
```

---

## Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/avalosjuancarlos/poc_airflow.git
cd poc_airflow
```

### 2. Configure Environment Variables

Copy the environment template:

```bash
cp env.template .env
```

**Linux/macOS only**: Set Airflow UID

```bash
echo "AIRFLOW_UID=$(id -u)" >> .env
```

### 3. Review and Customize `.env`

Edit `.env` to customize your installation:

```bash
# Essential variables
AIRFLOW_IMAGE_NAME=apache/airflow:2.11.0-python3.10
_AIRFLOW_WWW_USER_USERNAME=airflow  # Change for production
_AIRFLOW_WWW_USER_PASSWORD=airflow   # Change for production

# Market data configuration
MARKET_DATA_DEFAULT_TICKERS=AAPL
ENVIRONMENT=development
```

**See**: [Configuration Guide](../user-guide/configuration.md) for all options.

### 4. Initialize Airflow Database

```bash
docker compose up airflow-init
```

**Expected output**:
```
airflow-init_1  | Upgrades done
airflow-init_1  | Admin user airflow created
airflow-init_1 exited with code 0
```

### 5. Start Services

```bash
# Start all services in background
docker compose up -d

# Optional: Start with Flower monitoring
docker compose --profile flower up -d
```

### 6. Verify Installation

```bash
# Check service status
docker compose ps

# Expected: All services "Up" or "Up (healthy)"
```

### 7. Access Airflow Web UI

1. Open browser: **http://localhost:8080**
2. Login with:
   - **Username**: `airflow`
   - **Password**: `airflow`
3. You should see the Airflow dashboard

### 8. Optional: Access Flower

If started with Flower profile:

- Open browser: **http://localhost:5555**
- Monitor Celery workers in real-time

---

## Post-Installation

### Verify DAG Loading

1. In Airflow UI, go to **DAGs** page
2. You should see `get_market_data` DAG
3. Toggle it **ON** to activate
4. Click **▶️** to trigger a test run

### Check Logs

```bash
# View scheduler logs
docker compose logs -f airflow-scheduler

# View worker logs
docker compose logs -f airflow-worker

# View all logs
docker compose logs -f
```

### Test CLI Access

```bash
# List DAGs
docker compose exec airflow-scheduler airflow dags list

# List users
docker compose exec airflow-scheduler airflow users list
```

---

## Platform-Specific Instructions

### Linux

#### Permission Issues

If you encounter permission errors:

```bash
# Fix ownership
sudo chown -R $(id -u):$(id -g) dags logs plugins config

# Set AIRFLOW_UID
echo "AIRFLOW_UID=$(id -u)" >> .env
```

#### SELinux

If using SELinux:

```bash
# Add :z flag to volumes in docker-compose.yml
# volumes:
#   - ./dags:/opt/airflow/dags:z
```

### macOS

#### M1/M2 (ARM) Macs

The default image works on ARM Macs via Rosetta 2. For native ARM:

```bash
# In .env, use ARM-specific image
AIRFLOW_IMAGE_NAME=apache/airflow:2.11.0-python3.10-arm64
```

#### Port Conflicts

If port 8080 is in use:

```bash
# Change port in docker-compose.yml
# webserver:
#   ports:
#     - "8081:8080"  # Changed from 8080:8080
```

### Windows

#### WSL2 Required

Docker Desktop on Windows requires WSL2:

1. Install WSL2: https://docs.microsoft.com/windows/wsl/install
2. Install Docker Desktop for Windows
3. Enable WSL2 integration in Docker Desktop settings

#### Line Endings

Ensure Git doesn't convert line endings:

```bash
git config core.autocrlf false
```

---

## Troubleshooting Installation

### Services Won't Start

**Problem**: `docker compose up` fails or services crash

**Solutions**:
1. Check logs: `docker compose logs`
2. Ensure ports are free: `8080`, `5432`, `6379`
3. Verify Docker resources (RAM, CPU)
4. Try clean restart:
   ```bash
   docker compose down -v
   docker compose up airflow-init
   docker compose up -d
   ```

### Database Initialization Fails

**Problem**: `airflow-init` exits with error

**Solutions**:
1. Check PostgreSQL logs: `docker compose logs postgres`
2. Verify `.env` file exists and is valid
3. Remove volumes and retry:
   ```bash
   docker compose down -v
   docker compose up airflow-init
   ```

### Can't Access Web UI

**Problem**: Browser can't reach http://localhost:8080

**Solutions**:
1. Wait 30-60 seconds after `docker compose up`
2. Check webserver logs: `docker compose logs airflow-webserver`
3. Verify container is running: `docker compose ps airflow-webserver`
4. Try different port (see macOS section)
5. Check firewall settings

### DAGs Not Appearing

**Problem**: DAGs don't show in UI

**Solutions**:
1. Check DAG files are in `dags/` directory
2. Verify no syntax errors: `python dags/your_dag.py`
3. Check scheduler logs: `docker compose logs airflow-scheduler`
4. Wait 30 seconds and refresh browser
5. Verify `AIRFLOW__CORE__LOAD_EXAMPLES=false` in `.env`

### Permission Denied Errors (Linux)

**Problem**: Permission errors when accessing files

**Solutions**:
```bash
# Set correct ownership
sudo chown -R $(id -u):$(id -g) dags logs plugins

# Set AIRFLOW_UID in .env
echo "AIRFLOW_UID=$(id -u)" >> .env

# Restart services
docker compose down
docker compose up -d
```

---

## Uninstallation

### Stop Services

```bash
docker compose down
```

### Remove All Data

**⚠️ Warning**: This deletes all DAGs, logs, and database data

```bash
docker compose down -v
```

### Remove Project

```bash
cd ..
rm -rf poc_airflow
```

---

## Next Steps

✅ Installation complete! Now:

1. **[Market Data DAG Guide](../user-guide/market-data-dag.md)** - Run your first DAG
2. **[Configuration Guide](../user-guide/configuration.md)** - Customize settings
3. **[Logging Guide](../user-guide/logging.md)** - Understand the logging system

---

## Getting Help

- 📖 [Documentation Index](../README.md)
- 🐛 [Report Issues](https://github.com/avalosjuancarlos/poc_airflow/issues)
- 💬 [Discussions](https://github.com/avalosjuancarlos/poc_airflow/discussions)

---

[⬆ Back to Documentation Index](../README.md)

