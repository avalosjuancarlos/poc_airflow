.PHONY: help init up down restart logs test lint format clean dashboard dashboard-down all

# ============================================================================
# Help
# ============================================================================

help: ## Show this help message
	@echo "======================================================================"
	@echo "Market Data Pipeline - Makefile Commands"
	@echo "======================================================================"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""

# ============================================================================
# Airflow Commands
# ============================================================================

init: ## Initialize Airflow database
	@echo "Initializing Airflow database..."
	docker compose up airflow-init
	@echo "✅ Airflow initialized"

up: ## Start all Airflow services
	@echo "Starting Airflow services..."
	docker compose up -d
	@echo "✅ Airflow started"
	@echo ""
	@echo "Access Airflow UI: http://localhost:8080"
	@echo "Username: airflow"
	@echo "Password: airflow"

down: ## Stop all Airflow services
	@echo "Stopping Airflow services..."
	docker compose down
	@echo "✅ Airflow stopped"

restart: ## Restart all Airflow services
	@echo "Restarting Airflow services..."
	docker compose restart
	@echo "✅ Airflow restarted"

logs: ## View Airflow logs (all services)
	docker compose logs -f

logs-scheduler: ## View scheduler logs
	docker compose logs -f airflow-scheduler

logs-worker: ## View worker logs
	docker compose logs -f airflow-worker

logs-webserver: ## View webserver logs
	docker compose logs -f airflow-webserver

ps: ## Show running services
	docker compose ps

# ============================================================================
# Dashboard Commands
# ============================================================================

dashboard: ## Start dashboard (requires Airflow warehouse running)
	@echo "Starting Market Data Dashboard..."
	cd dashboard && docker compose up -d
	@echo "✅ Dashboard started"
	@echo ""
	@echo "Access Dashboard: http://localhost:8501"

dashboard-down: ## Stop dashboard
	@echo "Stopping dashboard..."
	cd dashboard && docker compose down
	@echo "✅ Dashboard stopped"

dashboard-logs: ## View dashboard logs
	cd dashboard && docker compose logs -f

dashboard-local: ## Run dashboard locally (without Docker)
	@echo "Starting dashboard locally..."
	cd dashboard && streamlit run app.py

# ============================================================================
# All Services
# ============================================================================

all: up dashboard ## Start both Airflow and Dashboard
	@echo ""
	@echo "======================================================================"
	@echo "✅ All services started"
	@echo "======================================================================"
	@echo "Airflow UI:  http://localhost:8080 (airflow/airflow)"
	@echo "Dashboard:   http://localhost:8501"
	@echo "Flower:      http://localhost:5555 (optional)"
	@echo "======================================================================"

stop-all: down dashboard-down ## Stop both Airflow and Dashboard
	@echo "✅ All services stopped"

# ============================================================================
# Development Commands
# ============================================================================

test: ## Run all tests
	@echo "Running tests..."
	docker compose -f docker-compose.test.yml up test
	@echo "✅ Tests complete"

test-unit: ## Run unit tests only
	@echo "Running unit tests..."
	docker compose exec airflow-webserver pytest tests/unit/ -v
	@echo "✅ Unit tests complete"

test-integration: ## Run integration tests only
	@echo "Running integration tests..."
	docker compose exec airflow-webserver pytest tests/integration/ -v
	@echo "✅ Integration tests complete"

coverage: ## Run tests with coverage report
	@echo "Running tests with coverage..."
	docker compose exec airflow-webserver pytest --cov=dags/market_data --cov-report=html --cov-report=term
	@echo "✅ Coverage report generated at htmlcov/index.html"

lint: ## Run linting (flake8, black, isort)
	@echo "Running linters..."
	docker compose exec airflow-webserver bash -c "flake8 dags/market_data --count --max-complexity=10 --max-line-length=127 --statistics && echo '✅ flake8 passed'"
	docker compose exec airflow-webserver bash -c "black --check dags/market_data && echo '✅ black passed'"
	docker compose exec airflow-webserver bash -c "isort --check-only dags/market_data && echo '✅ isort passed'"
	@echo "✅ All linters passed"

format: ## Format code with black and isort
	@echo "Formatting code..."
	docker compose exec airflow-webserver black dags/market_data tests/
	docker compose exec airflow-webserver isort dags/market_data tests/
	@echo "✅ Code formatted"

# ============================================================================
# Database Commands
# ============================================================================

db-backup: ## Backup Airflow metadata database
	@echo "Backing up metadata database..."
	docker compose exec postgres pg_dump -U airflow airflow > backups/metadata_$$(date +%Y%m%d_%H%M%S).sql
	@echo "✅ Backup saved to backups/"

db-warehouse-backup: ## Backup warehouse database
	@echo "Backing up warehouse database..."
	docker compose exec warehouse-postgres pg_dump -U warehouse_user market_data_warehouse > backups/warehouse_$$(date +%Y%m%d_%H%M%S).sql
	@echo "✅ Warehouse backup saved to backups/"

db-warehouse-query: ## Connect to warehouse database
	docker compose exec warehouse-postgres psql -U warehouse_user -d market_data_warehouse

db-warehouse-stats: ## Show warehouse statistics
	@echo "Warehouse Statistics:"
	docker compose exec warehouse-postgres psql -U warehouse_user -d market_data_warehouse \
		-c "SELECT ticker, COUNT(*) as records, MIN(date) as first_date, MAX(date) as last_date FROM fact_market_data GROUP BY ticker ORDER BY ticker;"

# ============================================================================
# DAG Commands
# ============================================================================

dag-list: ## List all DAGs
	docker compose exec airflow-scheduler airflow dags list

dag-trigger: ## Trigger market data DAG (usage: make dag-trigger TICKER=AAPL)
	@if [ -z "$(TICKER)" ]; then \
		docker compose exec airflow-scheduler airflow dags trigger get_market_data; \
	else \
		docker compose exec airflow-scheduler airflow dags trigger get_market_data --conf '{"ticker": "$(TICKER)"}'; \
	fi

dag-errors: ## Check for DAG import errors
	docker compose exec airflow-scheduler airflow dags list-import-errors

dag-pause: ## Pause market data DAG
	docker compose exec airflow-scheduler airflow dags pause get_market_data

dag-unpause: ## Unpause market data DAG
	docker compose exec airflow-scheduler airflow dags unpause get_market_data

# ============================================================================
# Cleanup Commands
# ============================================================================

clean: ## Remove temporary files and caches
	@echo "Cleaning temporary files..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.coverage" -delete
	rm -rf htmlcov/ .pytest_cache/ .coverage
	@echo "✅ Cleanup complete"

clean-data: ## Remove Parquet data files (⚠️  deletes data!)
	@echo "⚠️  WARNING: This will delete all Parquet files!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		rm -rf data/*.parquet; \
		echo "✅ Data cleaned"; \
	else \
		echo "Cancelled"; \
	fi

clean-all: down dashboard-down clean ## Stop everything and clean
	@echo "✅ Everything stopped and cleaned"

# ============================================================================
# Utility Commands
# ============================================================================

health: ## Check health of all services
	@echo "======================================================================"
	@echo "Service Health Check"
	@echo "======================================================================"
	@echo ""
	@echo "Docker Services:"
	@docker compose ps
	@echo ""
	@echo "Airflow Health:"
	@curl -s http://localhost:8080/health | python3 -m json.tool || echo "Airflow not accessible"
	@echo ""
	@echo "Dashboard Health:"
	@curl -s http://localhost:8501/_stcore/health || echo "Dashboard not accessible"

setup-env: ## Copy env.template to .env files
	@echo "Setting up environment files..."
	@if [ ! -f .env ]; then cp env.template .env && echo "✅ Created .env"; else echo "ℹ️  .env already exists"; fi
	@if [ ! -f dashboard/.env ]; then cp dashboard/env.template dashboard/.env && echo "✅ Created dashboard/.env"; else echo "ℹ️  dashboard/.env already exists"; fi
	@echo ""
	@echo "⚠️  IMPORTANT: Edit .env and dashboard/.env with your credentials before running!"

backups-dir: ## Create backups directory
	@mkdir -p backups
	@echo "✅ Backups directory created"

scale-workers: ## Scale workers (usage: make scale-workers N=5)
	@if [ -z "$(N)" ]; then \
		echo "Usage: make scale-workers N=5"; \
	else \
		docker compose up -d --scale airflow-worker=$(N); \
		echo "✅ Scaled to $(N) workers"; \
	fi

# ============================================================================
# Quick Start Workflow
# ============================================================================

quickstart: setup-env init up dashboard ## Complete quick start (setup → start everything)
	@echo ""
	@echo "======================================================================"
	@echo "🚀 Quick Start Complete!"
	@echo "======================================================================"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Edit .env and dashboard/.env with your credentials"
	@echo "  2. Restart services: make restart"
	@echo "  3. Access Airflow UI: http://localhost:8080 (airflow/airflow)"
	@echo "  4. Access Dashboard: http://localhost:8501"
	@echo ""
	@echo "Useful commands:"
	@echo "  make dag-trigger TICKER=AAPL  # Trigger DAG"
	@echo "  make logs-worker              # View worker logs"
	@echo "  make db-warehouse-stats       # View data statistics"
	@echo "  make help                     # Show all commands"
	@echo ""

# ============================================================================
# Default Target
# ============================================================================

.DEFAULT_GOAL := help

