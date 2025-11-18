# Project Improvements Proposal

This document outlines potential improvements for the Airflow Market Data Pipeline project, organized by category and priority.

**Last Updated**: 2025-11-18  
**Status**: Proposal - Awaiting Review

---

## Table of Contents

- [Overview](#overview)
- [Performance & Optimization](#performance--optimization)
- [Monitoring & Observability](#monitoring--observability)
- [Testing & Quality Assurance](#testing--quality-assurance)
- [Security Enhancements](#security-enhancements)
- [CI/CD Improvements](#cicd-improvements)
- [Documentation Enhancements](#documentation-enhancements)
- [New Features & Functionality](#new-features--functionality)
- [Code Quality & Refactoring](#code-quality--refactoring)
- [DevOps & Infrastructure](#devops--infrastructure)
- [Data Quality & Validation](#data-quality--validation)
- [Implementation Priority](#implementation-priority)

---

## Overview

This proposal identifies areas for improvement across multiple dimensions of the project. Each improvement includes:

- **Priority**: High, Medium, or Low
- **Impact**: High, Medium, or Low
- **Effort**: High, Medium, or Low
- **Dependencies**: Any prerequisites
- **Resource Requirements**: Hardware, software, and infrastructure needs
- **Estimated Value**: Business/technical value

---

## Performance & Optimization

> **Important Note**: All performance optimizations must consider:
> - **Error Handling & Resilience**: Fallback mechanisms and error recovery strategies
> - **Security**: Input validation, data protection, access control, and secure coding practices
> - **Trade-offs**: Balance between performance gains and reliability/security risks

### 1. Batch API Calls for Backfill
**Priority**: High  
**Impact**: High  
**Effort**: Medium-High  
**Status**: Not Implemented

**Current State**: The DAG makes individual API calls for each date during backfill (120 calls for 120 days).

**Proposal**: Implement batch API calls using Yahoo Finance's range query capability to fetch multiple days in a single request, with intelligent chunking and error recovery.

**Benefits**:
- Reduce API calls from 120 to 1-12 for backfill (90-99% reduction)
- Faster backfill execution (from ~2 minutes to ~10-30 seconds)
- Lower risk of rate limiting
- Reduced network overhead

**Risks & Mitigation**:
- **Risk**: Single large request failure loses all progress
  - **Mitigation**: Implement chunking strategy (e.g., 10-30 day chunks)
  - **Mitigation**: Retry individual chunks on failure
  - **Mitigation**: Checkpoint progress after each successful chunk
  
- **Risk**: Partial data in large response (some dates missing)
  - **Mitigation**: Validate response completeness
  - **Mitigation**: Fallback to individual calls for missing dates
  
- **Risk**: API timeout on large date ranges
  - **Mitigation**: Adaptive chunk sizing based on API response time
  - **Mitigation**: Maximum chunk size limit (e.g., 30 days)

**Implementation Strategy**:
```python
# Hybrid approach: Batch with chunking and fallback
def fetch_backfill_data(ticker, dates):
    """
    Fetch backfill data using batch API with intelligent chunking.
    
    Strategy:
    1. Try batch API in chunks (10-30 days)
    2. On chunk failure, retry with smaller chunk
    3. On persistent failure, fallback to individual calls for that chunk
    4. Checkpoint progress after each successful chunk
    """
    chunks = create_chunks(dates, chunk_size=30)  # Configurable
    results = []
    
    for chunk in chunks:
        try:
            # Try batch API for chunk
            data = fetch_data_range(ticker, chunk.start, chunk.end)
            results.extend(data)
            checkpoint_progress(ticker, chunk.end)  # Save progress
        except APIError as e:
            if e.is_retryable():
                # Retry with smaller chunk
                smaller_chunks = split_chunk(chunk, size=10)
                for small_chunk in smaller_chunks:
                    try:
                        data = fetch_data_range(ticker, small_chunk.start, small_chunk.end)
                        results.extend(data)
                    except APIError:
                        # Fallback to individual calls for this chunk
                        results.extend(fetch_individual_dates(ticker, small_chunk.dates))
            else:
                # Non-retryable error, fallback to individual calls
                results.extend(fetch_individual_dates(ticker, chunk.dates))
    
    return results
```

**Error Recovery**:
- **Checkpointing**: Save last successfully processed date to resume on failure
- **Partial Success Handling**: Process successful chunks, retry only failed ones
- **Fallback Mechanism**: Automatic fallback to individual calls if batch fails
- **Retry Strategy**: Exponential backoff with max retries per chunk

**Security Considerations**:
- **Input Validation**: Validate ticker symbols and date ranges before API calls
  - **Risk**: Malformed input could cause API errors or expose internal structure
  - **Mitigation**: Strict validation using existing `validate_ticker_format()` function
  - **Mitigation**: Validate date ranges (prevent extremely large ranges that could cause DoS)
  
- **Sensitive Data in Logs**: Avoid logging full API responses or sensitive data
  - **Risk**: API responses might contain sensitive information
  - **Mitigation**: Log only metadata (ticker, date range, record count), not raw data
  - **Mitigation**: Use structured logging with data masking for sensitive fields
  
- **API Key Protection**: Ensure API credentials are not exposed
  - **Risk**: API keys in logs or error messages
  - **Mitigation**: Use Airflow Connections or secrets management (see #12)
  - **Mitigation**: Never log API keys or authentication tokens
  
- **Rate Limiting Abuse**: Prevent abuse of batch API functionality
  - **Risk**: Malicious users could trigger large batch requests
  - **Mitigation**: Enforce maximum date range limits (e.g., max 120 days)
  - **Mitigation**: Rate limiting at DAG level (max concurrent batch requests)
  - **Mitigation**: Monitor and alert on unusual API usage patterns

**Resource Requirements**:
- **Hardware**: No additional hardware required (uses existing infrastructure)
- **Software**: 
  - No new dependencies (uses existing libraries)
  - Checkpoint storage: Can use existing Parquet storage or add lightweight database table
- **Infrastructure**: 
  - Storage for checkpoints: ~1KB per ticker per checkpoint (minimal)
  - Network: Reduced bandwidth usage (fewer API calls)
- **Cost Impact**: Minimal (potentially reduces API costs if rate-limited)

**Files to Modify**:
- `dags/market_data/utils/api_client.py` - Add `fetch_data_range()` method with chunking
- `dags/market_data/operators/transform_operators.py` - Update `fetch_multiple_dates()` with hybrid strategy
- `dags/market_data/utils/checkpoint.py` - New checkpoint utility for progress tracking

---

### 2. Implement Caching Layer
**Priority**: Medium  
**Impact**: Medium  
**Effort**: Medium  
**Status**: Not Implemented

**Proposal**: Add Redis-based caching for API responses and computed indicators with cache invalidation and error handling.

**Benefits**:
- Avoid duplicate API calls within same DAG run
- Faster retries (use cached data)
- Reduce API rate limiting risk
- Cache computed indicators for faster dashboard loads

**Risks & Mitigation**:
- **Risk**: Stale data from cache
  - **Mitigation**: Appropriate TTL based on data type (24h for historical, 1h for indicators)
  - **Mitigation**: Cache invalidation on data updates
  - **Mitigation**: Option to bypass cache for fresh data
  
- **Risk**: Cache failures (Redis unavailable)
  - **Mitigation**: Graceful degradation (fallback to direct API calls)
  - **Mitigation**: Cache as optimization, not requirement
  - **Mitigation**: Health checks and automatic cache bypass on Redis errors
  
- **Risk**: Memory pressure from large cache
  - **Mitigation**: LRU eviction policy
  - **Mitigation**: Memory limits and monitoring
  - **Mitigation**: Selective caching (only cache expensive operations)

**Implementation**:
- Use existing Redis service (already in docker-compose)
- Cache API responses with TTL (24 hours for historical data)
- Cache computed indicators with TTL (1 hour)
- Add cache invalidation strategy
- Implement graceful degradation on cache failures

**Error Handling**:
```python
def fetch_with_cache(ticker, date):
    try:
        # Try cache first
        cached = redis_client.get(f"market_data:{ticker}:{date}")
        if cached:
            return json.loads(cached)
    except RedisError as e:
        logger.warning(f"Cache unavailable, falling back to API: {e}")
        # Continue to API call (graceful degradation)
    
    # Fetch from API
    data = api_client.fetch(ticker, date)
    
    # Try to cache (non-blocking)
    try:
        redis_client.setex(f"market_data:{ticker}:{date}", 86400, json.dumps(data))
    except RedisError:
        logger.warning("Failed to cache data, continuing without cache")
    
    return data
```

**Security Considerations**:
- **Cache Key Injection**: Prevent cache key manipulation
  - **Risk**: Malicious input in ticker/date could manipulate cache keys
  - **Mitigation**: Sanitize and validate cache keys (use validated ticker format)
  - **Mitigation**: Use fixed prefix and hash-based keys: `f"market_data:{hash(ticker)}:{date}"`
  
- **Data Exposure**: Ensure cached data is not accessible to unauthorized users
  - **Risk**: Redis accessible to other services/containers
  - **Mitigation**: Use Redis authentication (password protection)
  - **Mitigation**: Use Redis namespaces/prefixes to isolate data
  - **Mitigation**: Encrypt sensitive cached data if required
  
- **Cache Poisoning**: Prevent malicious data from being cached
  - **Risk**: Compromised API responses cached and served to users
  - **Mitigation**: Validate cached data before returning (schema validation)
  - **Mitigation**: Cache invalidation on data quality failures
  - **Mitigation**: TTL-based expiration to limit exposure window
  
- **Information Disclosure**: Avoid exposing cache structure or keys
  - **Risk**: Cache key patterns reveal internal structure
  - **Mitigation**: Use opaque cache keys (hashed or encrypted)
  - **Mitigation**: Don't log cache keys in production

**Resource Requirements**:
- **Hardware**: 
  - Redis memory: ~100MB-1GB depending on cache size and TTL
  - Additional CPU: Minimal (Redis is lightweight)
- **Software**: 
  - Redis (already in docker-compose, but may need configuration)
  - Python library: `redis` (add to requirements.txt)
- **Infrastructure**: 
  - Redis service: Already available in docker-compose
  - Memory allocation: Configure Redis maxmemory (e.g., 512MB-1GB)
  - Persistence: Optional Redis persistence (AOF/RDB) for cache durability
- **Cluster Considerations**:
  - **Single Instance**: Sufficient for development and small production
  - **Redis Cluster (Production/High Availability)**:
    - **Redis Sentinel**: For high availability (automatic failover)
      - Requires 3+ Redis instances (1 master + 2+ sentinels)
      - Benefits: Automatic failover, no data loss on master failure
      - Cost: ~$45-150/month (3 instances)
    - **Redis Cluster Mode**: For horizontal scaling and sharding
      - Requires 6+ Redis instances (3 masters + 3 replicas minimum)
      - Benefits: Distributed cache, horizontal scaling, fault tolerance
      - Cost: ~$90-300/month (6 instances)
    - **Managed Redis Cluster** (AWS ElastiCache, Azure Cache, etc.):
      - Automatic failover, backups, monitoring
      - Cost: ~$50-500/month depending on size and features
  - **When to Use Cluster**:
    - High cache hit rate requirements (>80%)
    - Cache size >10GB
    - Need for high availability (99.9%+ uptime)
    - Multi-region deployment
- **Cost Impact**: 
  - Development: No additional cost (uses existing Redis)
  - Production Single Instance: ~$15-50/month
  - Production Cluster: ~$50-500/month depending on configuration

**Files to Create/Modify**:
- `dags/market_data/utils/cache.py` - New caching utility with error handling
- `dags/market_data/utils/api_client.py` - Integrate caching with fallback
- `dags/market_data/transformers/technical_indicators.py` - Cache indicator calculations
- `requirements.txt` - Add `redis` library
- `docker-compose.yml` - Configure Redis memory limits if needed

---

### 3. Parallel Ticker Processing
**Priority**: Medium  
**Impact**: High  
**Effort**: Medium-High  
**Status**: Partially Implemented

**Current State**: Multiple tickers are processed sequentially in a single DAG run.

**Proposal**: Use Airflow Task Groups or dynamic task mapping to process multiple tickers in parallel with proper error isolation and resource management.

**Benefits**:
- Process 10 tickers in ~1 minute instead of ~10 minutes
- Better resource utilization
- Scalable to hundreds of tickers

**Risks & Mitigation**:
- **Risk**: One ticker failure fails entire DAG run
  - **Mitigation**: Use `trigger_rule='all_done'` to continue on partial failures
  - **Mitigation**: Isolate errors per ticker (one failure doesn't affect others)
  - **Mitigation**: Aggregate task to collect results and report failures
  
- **Risk**: Resource exhaustion with too many parallel tasks
  - **Mitigation**: Limit concurrent ticker processing (configurable pool)
  - **Mitigation**: Use task pools to control parallelism
  - **Mitigation**: Monitor worker capacity and adjust accordingly
  
- **Risk**: API rate limiting with parallel requests
  - **Mitigation**: Implement rate limiting across parallel tasks
  - **Mitigation**: Stagger task start times slightly
  - **Mitigation**: Use task pools to limit concurrent API calls

**Implementation**:
```python
from airflow.utils.task_group import TaskGroup
from airflow.models import TaskInstance

# Create task pool for API calls to prevent rate limiting
api_pool = Pool(pool='api_pool', slots=5, description='Yahoo Finance API calls')

with TaskGroup("process_tickers") as ticker_group:
    ticker_tasks = {}
    
    for ticker in tickers:
        with TaskGroup(f"ticker_{ticker}") as ticker_subgroup:
            # Isolated task group per ticker
            validate_task = PythonOperator(
                task_id=f'validate_{ticker}',
                python_callable=validate_ticker,
                op_kwargs={'ticker': ticker},
                trigger_rule='all_done',  # Continue even if validation fails
            )
            
            fetch_task = PythonOperator(
                task_id=f'fetch_{ticker}',
                python_callable=fetch_multiple_dates,
                op_kwargs={'ticker': ticker},
                pool='api_pool',  # Limit concurrent API calls
                trigger_rule='all_done',
            )
            
            # ... other tasks
            
            validate_task >> fetch_task >> transform_task >> load_task
        
        ticker_tasks[ticker] = ticker_subgroup
    
    # Aggregate task to collect results and handle partial failures
    aggregate_task = PythonOperator(
        task_id='aggregate_results',
        python_callable=aggregate_ticker_results,
        trigger_rule='all_done',  # Run even if some tickers failed
    )
    
    # All ticker groups run in parallel, then aggregate
    ticker_tasks.values() >> aggregate_task
```

**Error Handling Strategy**:
- **Per-Ticker Isolation**: Each ticker has its own task group, failures are isolated
- **Partial Success**: DAG continues even if some tickers fail
- **Aggregation**: Final task collects results and reports which tickers succeeded/failed
- **Retry Strategy**: Individual ticker retries don't affect others

**Security Considerations**:
- **Input Validation**: Validate all tickers before parallel processing
  - **Risk**: Malicious or malformed ticker input could cause issues
  - **Mitigation**: Validate all tickers upfront using `validate_ticker_format()`
  - **Mitigation**: Reject invalid tickers before creating task groups
  - **Mitigation**: Limit maximum number of tickers per run (prevent resource exhaustion)
  
- **Resource Exhaustion**: Prevent DoS through excessive parallel tasks
  - **Risk**: Malicious user submits hundreds of tickers, exhausting resources
  - **Mitigation**: Enforce maximum ticker limit (configurable, e.g., 50 tickers)
  - **Mitigation**: Use task pools to limit concurrent execution
  - **Mitigation**: Monitor and alert on unusual task counts
  
- **Data Isolation**: Ensure ticker data is properly isolated
  - **Risk**: Data leakage between parallel ticker processing
  - **Mitigation**: Each ticker task group uses isolated context
  - **Mitigation**: No shared mutable state between ticker tasks
  - **Mitigation**: Validate data isolation in tests
  
- **Access Control**: Ensure only authorized tickers can be processed
  - **Risk**: Unauthorized ticker processing (if access control exists)
  - **Mitigation**: Validate ticker against allowed list (if applicable)
  - **Mitigation**: Log all ticker processing for audit trail
  - **Mitigation**: Rate limit per user/tenant if multi-tenant
  - **Mitigation**: Implement role-based ticker restrictions (see #11)
  - **Mitigation**: Require authentication for DAG triggers

**Resource Requirements**:
- **Hardware**: 
  - CPU: Increased CPU usage during parallel execution (scales with number of tickers)
  - Memory: Additional memory per parallel task (~50-100MB per ticker task)
  - Workers: May need additional Airflow workers for optimal parallelism
- **Software**: 
  - No new dependencies (uses Airflow Task Groups, already available)
  - Task pools: Configure Airflow pools to limit resource usage
- **Infrastructure**: 
  - Airflow workers: May need to scale from 1 to 3-5 workers for optimal performance
  - Database connections: More concurrent connections (1 per parallel task)
  - Worker resources: Each worker needs 1-2 CPU cores, 1-2GB RAM
- **Cluster Considerations**:
  - **Single Node**: Works but limited parallelism (constrained by single worker)
  - **Worker Cluster (Recommended)**: 
    - **Celery Executor**: Requires Redis/RabbitMQ for task queue
    - **Kubernetes Executor**: Requires K8s cluster (see #28)
    - **Benefits**: True parallel execution, auto-scaling, high availability
    - **Setup**: Configure Celery workers in cluster mode or use K8s horizontal pod autoscaling
  - **Scaling Strategy**:
    - **Horizontal**: Add more worker nodes (recommended for high ticker counts)
    - **Vertical**: Increase worker resources (limited by single node capacity)
  - **Resource Management**:
    - Use Airflow pools to limit concurrent tasks per resource type
    - Configure worker concurrency based on cluster capacity
    - Monitor cluster utilization and scale accordingly
- **Cost Impact**: 
  - Development: Minimal (Docker resources)
  - Production: Additional worker instances if scaling horizontally
    - Cloud: ~$50-200/month per additional worker (depending on instance size)
    - Self-hosted: Additional server costs
  - **Cluster Mode**: 
    - Celery cluster: +$50-200/month for queue broker (Redis/RabbitMQ)
    - K8s cluster: See #28 for full cluster costs

**Files to Modify**:
- `dags/get_market_data_dag.py` - Refactor to support dynamic task groups with error isolation
- `dags/market_data/operators/aggregate_operators.py` - New operator for result aggregation
- `docker-compose.yml` - Configure worker scaling and resource limits

---

### 4. Optimize Warehouse Load Strategy
**Priority**: Low  
**Impact**: Medium  
**Effort**: Medium  
**Status**: Not Implemented

**Proposal**: Implement bulk insert optimization for warehouse loads with transaction management and rollback capabilities.

**Current State**: UPSERT strategy processes records one by one or in small batches.

**Benefits**:
- Faster warehouse loads (2-5x improvement)
- Reduced database connection overhead
- Better for large backfills

**Risks & Mitigation**:
- **Risk**: Large transaction failure loses all progress
  - **Mitigation**: Implement chunked transactions (e.g., 1000 records per transaction)
  - **Mitigation**: Savepoint/checkpoint after each successful chunk
  - **Mitigation**: Resume from last successful chunk on failure
  
- **Risk**: Memory issues with very large datasets
  - **Mitigation**: Streaming/chunked processing instead of loading all data in memory
  - **Mitigation**: Configurable batch size based on available memory
  - **Mitigation**: Monitor memory usage and adjust batch size dynamically
  
- **Risk**: Database connection timeout on large operations
  - **Mitigation**: Chunked operations with connection refresh
  - **Mitigation**: Increase timeout for bulk operations
  - **Mitigation**: Use connection pooling effectively

**Implementation**:
```python
def load_to_warehouse_optimized(df, strategy='upsert', batch_size=1000):
    """
    Optimized warehouse load with chunked transactions and error recovery.
    
    Strategy:
    1. Process data in chunks (configurable batch_size)
    2. Each chunk in separate transaction
    3. Savepoint after each successful chunk
    4. On failure, rollback current chunk and resume from last savepoint
    """
    total_records = len(df)
    processed = 0
    last_successful_chunk = get_checkpoint()  # Resume from checkpoint if exists
    
    for start_idx in range(last_successful_chunk, total_records, batch_size):
        end_idx = min(start_idx + batch_size, total_records)
        chunk = df.iloc[start_idx:end_idx]
        
        try:
            with transaction.atomic():  # Transaction per chunk
                if strategy == 'upsert':
                    bulk_upsert(chunk)  # Use COPY + ON CONFLICT
                elif strategy == 'append':
                    bulk_insert(chunk)  # Use COPY
                
                # Savepoint after successful chunk
                save_checkpoint(end_idx)
                processed += len(chunk)
                
        except DatabaseError as e:
            logger.error(f"Failed to load chunk {start_idx}-{end_idx}: {e}")
            # Rollback current chunk, but keep previous chunks
            raise  # Re-raise to trigger retry mechanism
    
    return processed
```

**Error Recovery**:
- **Chunked Transactions**: Each batch in separate transaction, isolated failures
- **Checkpointing**: Save progress after each successful chunk
- **Resume Capability**: Resume from last successful chunk on retry
- **Partial Success**: Keep successfully loaded chunks, retry only failed ones

**Security Considerations**:
- **SQL Injection Prevention**: Ensure bulk operations are safe from SQL injection
  - **Risk**: User-controlled data in SQL queries
  - **Mitigation**: Use parameterized queries for all SQL operations
  - **Mitigation**: Use ORM/SQLAlchemy methods instead of raw SQL where possible
  - **Mitigation**: Validate and sanitize all input data before database operations
  - **Mitigation**: Audit all SQL query construction (see #13)
  
- **Data Validation**: Validate data before bulk insert
  - **Risk**: Malicious or malformed data inserted into warehouse
  - **Mitigation**: Schema validation before bulk operations
  - **Mitigation**: Data type validation (prevent type confusion attacks)
  - **Mitigation**: Business rule validation (price ranges, volume limits)
  
- **Transaction Isolation**: Ensure proper transaction boundaries
  - **Risk**: Data corruption or partial updates on failures
  - **Mitigation**: Use proper transaction isolation levels
  - **Mitigation**: Rollback failed chunks completely
  - **Mitigation**: Validate data integrity after each chunk
  
- **Access Control**: Ensure proper database permissions
  - **Risk**: Unauthorized database access or privilege escalation
  - **Mitigation**: Use least-privilege database user (only INSERT/UPDATE, no DROP/ALTER)
  - **Mitigation**: Separate read/write database users
  - **Mitigation**: Audit database access logs
  
- **Sensitive Data Protection**: Protect sensitive data in transit and at rest
  - **Risk**: Data exposure in logs or error messages
  - **Mitigation**: Use encrypted database connections (SSL/TLS)
  - **Mitigation**: Don't log full data records, only metadata
  - **Mitigation**: Mask sensitive fields in error messages

**Resource Requirements**:
- **Hardware**: 
  - Database CPU: Increased during bulk operations (temporary spikes)
  - Database Memory: More memory for bulk operations (temporary)
  - Network: Higher bandwidth during bulk transfers
- **Software**: 
  - No new dependencies (uses existing SQLAlchemy/psycopg2)
  - Database: PostgreSQL COPY command or bulk INSERT support
- **Infrastructure**: 
  - Database connections: Fewer connections needed (bulk operations are more efficient)
  - Database resources: May need to increase `work_mem` for large batches
  - Storage: No additional storage (uses existing warehouse)
- **Cost Impact**: 
  - Development: No additional cost
  - Production: Potentially reduced costs (fewer database operations)
  - Database: May need to scale database resources if processing very large datasets

**Files to Modify**:
- `dags/market_data/operators/warehouse_operators.py` - Optimize `load_to_warehouse()` with chunking
- `dags/market_data/warehouse/loader.py` - Implement bulk operations with error handling

---

## Monitoring & Observability

### 5. Implement Prometheus Metrics Export
**Priority**: High  
**Impact**: High  
**Effort**: Medium  
**Status**: Not Implemented

**Proposal**: Add Prometheus metrics export for Airflow tasks and custom business metrics.

**Benefits**:
- Real-time monitoring dashboards
- Alerting on key metrics
- Performance tracking over time
- Integration with Grafana

**Metrics to Track**:
- DAG run duration
- Task success/failure rates
- API call latency
- Records processed per run
- Warehouse load duration
- Error rates by type

**Implementation**:
- Add `prometheus_client` library
- Create metrics decorator for tasks
- Export metrics via HTTP endpoint
- Configure Prometheus scraping

**Resource Requirements**:
- **Hardware**: 
  - Prometheus server: 2-4 CPU cores, 4-8GB RAM, 50-100GB storage (for metrics retention)
  - Grafana (optional): 1-2 CPU cores, 1-2GB RAM
  - Metrics endpoint: Minimal overhead (~1-5% CPU, ~50-100MB RAM per Airflow component)
- **Software**: 
  - Python library: `prometheus_client` (add to requirements.txt)
  - Prometheus server: Docker image `prom/prometheus:latest`
  - Grafana (optional): Docker image `grafana/grafana:latest`
- **Infrastructure**: 
  - Prometheus service: New Docker container or external service
  - Metrics endpoint: HTTP endpoint on Airflow webserver (port 9090 or custom)
  - Storage: Time-series database for metrics (Prometheus TSDB)
  - Network: Additional network traffic for metrics scraping
- **Cluster Considerations**:
  - **Single Instance**: Sufficient for small to medium deployments
  - **Prometheus HA Cluster** (Production):
    - **Prometheus Federation**: For scaling and high availability
      - Requires 2+ Prometheus instances (1 per region/zone)
      - Benefits: Distributed scraping, fault tolerance, reduced load
      - Cost: ~$100-400/month (2-4 instances)
    - **Thanos/Cortex**: For long-term storage and global querying
      - Requires object storage (S3, GCS) + Thanos components
      - Benefits: Unlimited retention, global querying, deduplication
      - Cost: ~$200-800/month (storage + compute)
    - **Managed Solutions** (AWS Managed Prometheus, Grafana Cloud):
      - Automatic scaling, high availability, managed storage
      - Cost: ~$100-500/month depending on metrics volume
  - **Grafana HA** (Optional):
    - Requires 2+ Grafana instances behind load balancer
    - Shared database (PostgreSQL) for session persistence
    - Cost: ~$50-200/month additional
  - **When to Use Cluster**:
    - High metrics volume (>1M samples/second)
    - Need for high availability (99.9%+ uptime)
    - Multi-region deployment
    - Long-term metrics retention (>90 days)
- **Cost Impact**: 
  - Development: Minimal (Docker containers)
  - Production Single Instance: ~$50-200/month
  - Production HA Cluster: ~$200-800/month depending on configuration
  - Managed Solutions: ~$100-500/month depending on metrics volume

**Files to Create/Modify**:
- `dags/market_data/utils/metrics.py` - New metrics utility
- `dags/market_data/operators/*.py` - Add metrics decorators
- `docker-compose.yml` - Add Prometheus service
- `requirements.txt` - Add `prometheus_client` library
- `monitoring/prometheus.yml` - Prometheus configuration
- `monitoring/grafana/dashboards/` - Grafana dashboard definitions

---

### 6. Structured Logging with Context
**Priority**: Medium  
**Impact**: Medium  
**Effort**: Low  
**Status**: Partially Implemented

**Current State**: Logging exists but could be more structured with consistent context.

**Proposal**: Enhance logging to include structured context (ticker, task_id, run_id, etc.) in all log messages.

**Benefits**:
- Better log aggregation and search
- Easier debugging with full context
- Integration with log analysis tools (ELK, Splunk)

**Implementation**:
- Use structured logging format (JSON)
- Add context manager for automatic context injection
- Ensure all log messages include relevant context

**Files to Modify**:
- `dags/market_data/utils/logger.py` - Enhance structured logging

---

### 7. Health Check Endpoint
**Priority**: Medium  
**Impact**: Medium  
**Effort**: Low  
**Status**: Not Implemented

**Proposal**: Create a health check endpoint for the dashboard and DAG health monitoring.

**Benefits**:
- Kubernetes/Docker health checks
- Load balancer health monitoring
- Quick status checks

**Implementation**:
- Add health check endpoint to dashboard
- Check database connectivity
- Check warehouse connectivity
- Return status (healthy/unhealthy)

**Files to Create/Modify**:
- `dashboard/health.py` - New health check module
- `dashboard/app.py` - Add health endpoint

---

## Testing & Quality Assurance

### 8. Increase Test Coverage to 95%+
**Priority**: Medium  
**Impact**: Medium  
**Effort**: Medium  
**Status**: Current: 91.84%

**Proposal**: Increase test coverage by adding tests for edge cases and error scenarios.

**Areas Needing Coverage**:
- API client error handling (85% → 95%)
- Warehouse loader edge cases (98% → 100%)
- Transform operators error scenarios
- Configuration edge cases

**Benefits**:
- Higher confidence in code changes
- Better error handling validation
- Reduced production bugs

**Files to Modify**:
- `tests/unit/test_api_client.py` - Add more error scenarios
- `tests/unit/test_warehouse_loader.py` - Add edge cases
- `tests/unit/test_transform_operators.py` - Add error scenarios

---

### 9. Add Performance Regression Tests
**Priority**: Low  
**Impact**: Medium  
**Effort**: Medium  
**Status**: Not Implemented

**Proposal**: Create performance benchmarks and regression tests to detect performance degradation.

**Benefits**:
- Catch performance regressions early
- Track performance improvements
- Set performance SLAs

**Implementation**:
- Create benchmark DAG
- Track key metrics (API latency, task duration, warehouse load time)
- Fail CI if performance degrades beyond threshold

**Files to Create**:
- `tests/performance/test_benchmarks.py` - Performance tests
- `.github/workflows/performance.yml` - Performance CI job

---

### 10. Integration Tests for Multi-Ticker Scenarios
**Priority**: Medium  
**Impact**: Medium  
**Effort**: Low  
**Status**: Not Implemented

**Proposal**: Add integration tests that validate multi-ticker processing end-to-end.

**Benefits**:
- Validate multi-ticker functionality
- Catch integration issues early
- Ensure parallel processing works correctly

**Files to Create/Modify**:
- `tests/integration/test_multi_ticker.py` - New integration tests

---

## Security Enhancements

### 11. Access Control & User Management
**Priority**: High  
**Impact**: High  
**Effort**: High  
**Status**: Partially Implemented

**Current State**: 
- **Airflow UI**: Basic authentication (username/password), no role-based access control
- **Dashboard**: No authentication, accessible to anyone with network access
- **Warehouse Explorer**: Read-only SQL queries, but no user authentication
- **DAG Execution**: No restrictions on who can trigger DAGs
- **Configuration**: No restrictions on who can modify Airflow Variables

**Proposal**: Implement comprehensive access control and user management across all components.

**Areas Requiring Access Control**:

#### 1. Dashboard Access Control
**Priority**: High  
**Current Risk**: Anyone with network access can view all data

**Required Controls**:
- **Authentication**: User login (username/password, OAuth, SSO)
- **Authorization**: Role-based access control (RBAC)
- **View Restrictions**: 
  - **Viewer Role**: Read-only access to Market Dashboard
  - **Analyst Role**: Read-only access + export capabilities
  - **Admin Role**: Full access including Warehouse Explorer
- **Data Filtering**: Users can only see data for authorized tickers/environments
- **Session Management**: Timeout, secure session storage

**Implementation**:
- Streamlit authentication (streamlit-authenticator or custom)
- OAuth integration (Google, Microsoft, Okta)
- Session state management
- Role-based view filtering

**Files to Create/Modify**:
- `dashboard/auth.py` - Authentication module
- `dashboard/rbac.py` - Role-based access control
- `dashboard/app.py` - Add authentication check
- `dashboard/config.py` - Add user roles configuration

#### 2. Warehouse Explorer Access Control
**Priority**: High  
**Current Risk**: SQL injection mitigated, but no user restrictions

**Required Controls**:
- **Query Restrictions**: 
  - **Viewer Role**: Predefined queries only (no custom SQL)
  - **Analyst Role**: Custom SELECT queries (current behavior)
  - **Admin Role**: Full SQL access (with audit logging)
- **Data Access**: 
  - **Row-Level Security**: Users can only query data for authorized tickers
  - **Environment Access**: Restrict access to specific environments (dev/staging/prod)
- **Query Limits**: 
  - Max query execution time
  - Max result set size
  - Rate limiting per user
- **Audit Logging**: Log all SQL queries with user, timestamp, query text

**Implementation**:
- Database-level row security policies (PostgreSQL RLS)
- Query result filtering based on user permissions
- Query execution limits and timeouts
- Comprehensive audit logging

**Files to Modify**:
- `dashboard/views/warehouse.py` - Add user-based restrictions
- `dashboard/data.py` - Add query filtering based on user permissions
- `dashboard/auth.py` - Add permission checking

#### 3. Airflow DAG Execution Control
**Priority**: Medium  
**Current Risk**: Any authenticated user can trigger DAGs

**Required Controls**:
- **DAG Permissions**: 
  - **Viewer Role**: View DAGs only (no execution)
  - **Operator Role**: Trigger and monitor DAGs
  - **Admin Role**: Full DAG management (edit, delete, configure)
- **Parameter Restrictions**: 
  - Limit which parameters can be modified
  - Validate parameter values based on user role
  - Restrict ticker selection (e.g., only allow specific tickers)
- **Execution Limits**: 
  - Max concurrent DAG runs per user
  - Rate limiting on DAG triggers
  - Resource quotas per user/team

**Implementation**:
- Airflow RBAC (built-in, but needs configuration)
- Custom DAG parameter validation
- Resource pools per user/role
- Execution audit logging

**Files to Modify**:
- `dags/get_market_data_dag.py` - Add parameter validation based on user
- Airflow configuration - Enable and configure RBAC
- `docs/operations/deployment.md` - Document RBAC setup

#### 4. Configuration Access Control
**Priority**: Medium  
**Current Risk**: Any user can modify Airflow Variables

**Required Controls**:
- **Variable Permissions**: 
  - **Viewer Role**: Read-only access to variables
  - **Operator Role**: Read + modify non-sensitive variables
  - **Admin Role**: Full access including sensitive variables (secrets, credentials)
- **Sensitive Variables**: 
  - Mark certain variables as sensitive (masked in UI)
  - Require admin role to modify
  - Audit all changes to sensitive variables
- **Connection Management**: 
  - Restrict who can create/modify database connections
  - Encrypt connection credentials
  - Audit connection access

**Implementation**:
- Airflow Variable permissions (RBAC)
- Custom variable validation
- Connection encryption
- Change audit logging

**Files to Modify**:
- Airflow configuration - Configure variable permissions
- `docs/operations/deployment.md` - Document access control setup

#### 5. Data Export Access Control
**Priority**: Medium  
**Current Risk**: Anyone with dashboard access can export all data

**Required Controls**:
- **Export Permissions**: 
  - **Viewer Role**: No export (view only)
  - **Analyst Role**: Export with data limits (e.g., max 10K rows)
  - **Admin Role**: Full export capabilities
- **Export Restrictions**: 
  - Limit export frequency per user
  - Restrict export formats based on role
  - Watermark exports with user information
- **Audit Logging**: Log all exports (user, timestamp, data scope, format)

**Implementation**:
- Role-based export restrictions
- Export rate limiting
- Export audit logging
- Data watermarking

**Files to Modify**:
- `dashboard/components/export.py` - Add permission checks
- `dashboard/views/market.py` - Add export restrictions

#### 6. Monitoring & Metrics Access Control
**Priority**: Low  
**Current Risk**: Monitoring data accessible to all users

**Required Controls**:
- **Metrics Visibility**: 
  - **Viewer Role**: Basic metrics only (success rates, counts)
  - **Operator Role**: Detailed metrics (latency, errors)
  - **Admin Role**: Full metrics including system metrics
- **Alert Configuration**: 
  - Restrict who can configure alerts
  - Require approval for alert rule changes
- **Log Access**: 
  - Restrict log viewing based on role
  - Mask sensitive data in logs for non-admin users

**Implementation**:
- Role-based metrics filtering
- Alert configuration permissions
- Log access control

**Files to Modify**:
- `dags/market_data/utils/metrics.py` - Add role-based filtering
- Monitoring dashboards - Add access control

**Resource Requirements**:
- **Hardware**: Minimal overhead (~1-2% CPU, ~50-100MB RAM for auth)
- **Software**: 
  - Authentication library: `streamlit-authenticator` or `python-jose` for JWT
  - OAuth libraries: `authlib` or `python-social-auth` (if using OAuth)
  - Database: User/role storage (can use existing PostgreSQL)
- **Infrastructure**: 
  - Session storage: Redis or database
  - OAuth provider: Google, Microsoft, Okta (if using OAuth)
  - LDAP/Active Directory: For enterprise SSO (optional)
- **Cost Impact**: 
  - Development: Minimal (open-source libraries)
  - Production: 
    - OAuth provider: Usually free for basic tier
    - Managed SSO (Okta, Auth0): ~$2-8/user/month
    - Self-hosted: Server costs if using LDAP/AD

**Security Considerations**:
- **Password Security**: 
  - Enforce strong password policies
  - Password hashing (bcrypt, argon2)
  - Password rotation requirements
- **Session Security**: 
  - Secure session tokens (JWT with expiration)
  - HTTPS only for session cookies
  - Session timeout and refresh
- **Multi-Factor Authentication (MFA)**: 
  - Optional MFA for admin roles
  - TOTP (Google Authenticator, Authy)
  - SMS/Email verification (optional)
- **Audit Trail**: 
  - Log all authentication attempts
  - Log all authorization failures
  - Log all sensitive operations (exports, config changes)
  - Retain audit logs for compliance (90+ days)

**Files to Create/Modify**:
- `dashboard/auth.py` - Authentication module
- `dashboard/rbac.py` - Role-based access control
- `dashboard/app.py` - Add authentication middleware
- `dashboard/config.py` - Add user roles and permissions
- `dashboard/views/warehouse.py` - Add permission checks
- `dashboard/components/export.py` - Add export restrictions
- `docs/operations/access-control.md` - New documentation
- `docs/user-guide/dashboard.md` - Update with access control info

---

### 12. Secrets Management
**Priority**: High  
**Impact**: High  
**Effort**: Medium  
**Status**: Not Implemented

**Proposal**: Implement proper secrets management instead of environment variables for sensitive data.

**Current State**: Passwords and API keys are stored in `.env` files.

**Benefits**:
- Better security for production
- Rotation of secrets without code changes
- Audit trail for secret access

**Implementation Options**:
- **Option 1**: Airflow Connections (for database credentials)
- **Option 2**: HashiCorp Vault integration
- **Option 3**: AWS Secrets Manager (for production)
- **Option 4**: Kubernetes Secrets (for K8s deployments)

**Files to Modify**:
- `dags/market_data/config/warehouse_config.py` - Use Airflow Connections
- `docs/operations/deployment.md` - Document secrets management

---

### 13. SQL Injection Prevention Audit
**Priority**: High  
**Impact**: High  
**Effort**: Low  
**Status**: Partially Implemented

**Current State**: Warehouse Explorer has SQL injection prevention, but should be audited.

**Proposal**: Conduct comprehensive security audit of all SQL query construction.

**Benefits**:
- Ensure no SQL injection vulnerabilities
- Validate input sanitization
- Security best practices

**Files to Review**:
- `dashboard/views/warehouse.py` - SQL query construction
- `dags/market_data/operators/warehouse_operators.py` - SQL queries
- `dags/market_data/warehouse/loader.py` - SQL construction

---

### 14. API Rate Limiting Protection
**Priority**: Medium  
**Impact**: Medium  
**Effort**: Low  
**Status**: Partially Implemented

**Proposal**: Enhance API rate limiting protection with exponential backoff and circuit breaker pattern.

**Benefits**:
- Better handling of API rate limits
- Automatic recovery from API issues
- Prevent cascading failures

**Implementation**:
- Implement circuit breaker pattern
- Enhanced exponential backoff
- Rate limit detection and automatic throttling

**Files to Modify**:
- `dags/market_data/utils/api_client.py` - Add circuit breaker
- `dags/market_data/sensors/api_sensor.py` - Enhanced rate limit detection

---

## CI/CD Improvements

### 15. Multi-Python Version Testing
**Priority**: Low  
**Impact**: Low  
**Effort**: Low  
**Status**: Not Implemented

**Proposal**: Test against multiple Python versions (3.10, 3.11) to ensure compatibility.

**Benefits**:
- Future-proof codebase
- Catch version-specific issues
- Support for newer Python features

**Implementation**:
- Update `.github/workflows/ci.yml` to test multiple Python versions
- Use matrix strategy

---

### 16. Automated Dependency Updates
**Priority**: Low  
**Impact**: Low  
**Effort**: Low  
**Status**: Not Implemented

**Proposal**: Use Dependabot or Renovate to automatically create PRs for dependency updates.

**Benefits**:
- Keep dependencies up to date
- Security patches applied quickly
- Reduce manual maintenance

**Implementation**:
- Add `.github/dependabot.yml` configuration
- Configure update schedule and scope

---

### 17. Pre-commit Hooks
**Priority**: Medium  
**Impact**: Medium  
**Effort**: Low  
**Status**: Not Implemented

**Proposal**: Add pre-commit hooks for code quality checks before commits.

**Benefits**:
- Catch issues before CI
- Consistent code quality
- Faster feedback loop

**Implementation**:
- Create `.pre-commit-config.yaml`
- Add hooks for: black, isort, flake8, mypy
- Document setup in contributing guide

**Files to Create**:
- `.pre-commit-config.yaml`
- `docs/developer-guide/contributing.md` - Update with pre-commit setup

---

## Documentation Enhancements

### 18. API Documentation with Examples
**Priority**: Medium  
**Impact**: Medium  
**Effort**: Medium  
**Status**: Partially Implemented

**Proposal**: Enhance API reference documentation with more practical examples and use cases.

**Benefits**:
- Easier onboarding for new developers
- Better understanding of API usage
- Reduced support questions

**Files to Modify**:
- `docs/developer-guide/api-reference.md` - Add more examples

---

### 19. Video Tutorials or Screencasts
**Priority**: Low  
**Impact**: High  
**Effort**: High  
**Status**: Not Implemented

**Proposal**: Create video tutorials for common tasks (setup, running DAG, using dashboard).

**Benefits**:
- Better user onboarding
- Visual learning
- Reduced support burden

**Content Ideas**:
- Quick start tutorial (5 minutes)
- Dashboard walkthrough (10 minutes)
- Troubleshooting common issues (15 minutes)

---

### 20. Architecture Decision Records (ADRs)
**Priority**: Low  
**Impact**: Low  
**Effort**: Low  
**Status**: Not Implemented

**Proposal**: Document major architectural decisions in ADR format.

**Benefits**:
- Historical context for decisions
- Onboarding for new team members
- Reference for future decisions

**Files to Create**:
- `docs/adr/` - Directory for ADRs
- Template and examples

---

## New Features & Functionality

### 21. Data Quality Checks
**Priority**: High  
**Impact**: High  
**Effort**: Medium  
**Status**: Not Implemented

**Proposal**: Implement data quality checks (completeness, validity, consistency) as Airflow tasks.

**Checks to Implement**:
- Data completeness (no missing dates)
- Price validity (high >= low, close within range)
- Volume validity (non-negative)
- Indicator validity (RSI 0-100, etc.)
- Data freshness (last update within 24 hours)

**Benefits**:
- Early detection of data issues
- Confidence in data quality
- Automated data validation

**Implementation**:
- Create `dags/market_data/operators/data_quality_operators.py`
- Add data quality task to DAG
- Fail DAG if quality checks fail

**Resource Requirements**:
- **Hardware**: 
  - CPU: Additional processing for data validation (~10-20% per quality check task)
  - Memory: Minimal (~50-100MB for validation operations)
- **Software**: 
  - No new dependencies (uses existing pandas/numpy)
  - Optional: `great-expectations` library for advanced validation (if using)
- **Infrastructure**: 
  - Database queries: Additional queries for data validation
  - Storage: Optional storage for quality check results/reports
- **Cost Impact**: 
  - Development: Minimal (uses existing resources)
  - Production: Minimal overhead (~5-10% additional task execution time)

**Files to Create**:
- `dags/market_data/operators/data_quality_operators.py`
- `tests/unit/test_data_quality.py`
- `requirements.txt` - Add `great-expectations` if using advanced validation (optional)

---

### 22. Data Lineage Tracking
**Priority**: Low  
**Impact**: Medium  
**Effort**: High  
**Status**: Not Implemented

**Proposal**: Implement data lineage tracking to understand data flow and dependencies.

**Benefits**:
- Understand data dependencies
- Impact analysis for changes
- Compliance and auditing

**Implementation Options**:
- **Option 1**: OpenLineage integration
- **Option 2**: Custom lineage tracking
- **Option 3**: DataHub integration

---

### 23. Alert System for Dashboard
**Priority**: Medium  
**Impact**: Medium  
**Effort**: Medium  
**Status**: Partially Implemented (Phase 2)

**Proposal**: Complete Phase 2 alert system with UI configuration and alert history.

**Features**:
- User-configurable thresholds in UI
- Alert history/log
- Email/webhook notifications (optional)

**Benefits**:
- Proactive issue detection
- User-friendly alert management
- Better monitoring

**Access Control Considerations**:
- **Alert Configuration**: 
  - **Viewer Role**: View alerts only (no configuration)
  - **Analyst Role**: Create/modify personal alerts
  - **Admin Role**: Create/modify global alerts
- **Alert Visibility**: 
  - Users can only see alerts for tickers they have access to
  - Admin alerts visible to all users
- **Notification Permissions**: 
  - Restrict who can configure email/webhook notifications
  - Require approval for external webhook configurations

**Files to Create/Modify**:
- `dashboard/components/alerts.py` - Alert management component with access control
- `dashboard/views/market.py` - Integrate alert configuration
- `dashboard/rbac.py` - Add alert permissions

---

### 24. Scheduled Reports
**Priority**: Low  
**Impact**: Low  
**Effort**: Medium  
**Status**: Not Implemented

**Proposal**: Add scheduled report generation (daily/weekly summaries) via Airflow DAG.

**Benefits**:
- Automated reporting
- Executive summaries
- Historical trend tracking

**Access Control Considerations**:
- **Report Generation**: 
  - Only authorized users can trigger report generation
  - Restrict report content based on user role
- **Report Distribution**: 
  - Restrict who can configure report recipients
  - Validate email addresses before sending
  - Audit all report generations and distributions
- **Report Content**: 
  - Filter report data based on user permissions
  - Mask sensitive data for non-admin users
  - Include data access restrictions in reports

**Implementation**:
- Create report generation DAG
- Generate PDF/HTML reports
- Email reports to stakeholders
- Add access control checks

**Files to Create/Modify**:
- `dags/report_generation_dag.py` - New report DAG with access control
- `dags/market_data/operators/report_operators.py` - Report generation with permissions

---

## Code Quality & Refactoring

### 25. Type Hints Coverage
**Priority**: Medium  
**Impact**: Medium  
**Effort**: Medium  
**Status**: Partially Implemented

**Proposal**: Add comprehensive type hints to all functions and methods.

**Benefits**:
- Better IDE support
- Catch type errors early
- Self-documenting code
- Enable mypy static analysis

**Implementation**:
- Add type hints to all functions
- Configure mypy for type checking
- Add mypy to CI pipeline

**Files to Modify**:
- All Python files in `dags/market_data/`
- `dashboard/` Python files

---

### 26. Reduce Code Complexity
**Priority**: Low  
**Impact**: Low  
**Effort**: Medium  
**Status**: Not Implemented

**Proposal**: Refactor complex functions to reduce cyclomatic complexity.

**Current Issues**:
- Some functions have high complexity (C901 flake8 warnings)
- `technical_indicators.py` has complex calculations

**Benefits**:
- More maintainable code
- Easier testing
- Better readability

**Files to Review**:
- `dags/market_data/transformers/technical_indicators.py`
- Functions with high complexity scores

---

### 27. Standardize Error Handling
**Priority**: Medium  
**Impact**: Medium  
**Effort**: Low  
**Status**: Partially Implemented

**Proposal**: Create custom exception classes and standardize error handling across the codebase.

**Benefits**:
- Consistent error handling
- Better error messages
- Easier debugging

**Implementation**:
- Create `dags/market_data/exceptions.py` with custom exceptions
- Replace generic exceptions with specific ones
- Update error handling throughout codebase

**Files to Create/Modify**:
- `dags/market_data/exceptions.py` - New exception classes
- All operator files - Use custom exceptions

---

## DevOps & Infrastructure

### 28. Kubernetes Deployment Guide
**Priority**: Low  
**Impact**: Medium  
**Effort**: High  
**Status**: Not Implemented

**Proposal**: Create Kubernetes deployment manifests and documentation.

**Benefits**:
- Production-ready deployment option
- Scalability
- Cloud-native approach

**Resource Requirements**:
- **Hardware**: 
  - Kubernetes cluster: Minimum 3 nodes (for HA)
    - Each node: 4-8 CPU cores, 8-16GB RAM, 50-100GB storage
  - Total: 12-24 CPU cores, 24-48GB RAM, 150-300GB storage
- **Software**: 
  - Kubernetes cluster (managed or self-hosted)
  - kubectl CLI tool
  - Helm (optional, for package management)
- **Infrastructure**: 
  - Kubernetes cluster: EKS (AWS), GKE (GCP), AKS (Azure), or self-hosted
  - Load balancer: For external access
  - Ingress controller: For routing
  - Persistent volumes: For data storage
- **Cost Impact**: 
  - Managed Kubernetes (EKS/GKE/AKS): ~$70-200/month for control plane + node costs
  - Node costs: ~$50-200/month per node (depending on instance size)
  - Total: ~$220-800/month for small cluster (3 nodes)
  - Self-hosted: Server costs + maintenance overhead

**Files to Create**:
- `k8s/` - Kubernetes manifests
- `docs/operations/kubernetes-deployment.md` - Deployment guide
- `k8s/helm/` - Helm charts (optional)

---

### 29. Infrastructure as Code (Terraform)
**Priority**: Low  
**Impact**: Low  
**Effort**: High  
**Status**: Not Implemented

**Proposal**: Create Terraform modules for AWS/GCP/Azure infrastructure.

**Benefits**:
- Reproducible infrastructure
- Version-controlled infrastructure
- Multi-cloud support

**Files to Create**:
- `terraform/` - Terraform modules
- `docs/operations/terraform-deployment.md` - Deployment guide

---

### 30. Docker Image Optimization
**Priority**: Low  
**Impact**: Low  
**Effort**: Low  
**Status**: Not Implemented

**Proposal**: Optimize Docker images (multi-stage builds, smaller base images).

**Benefits**:
- Faster builds
- Smaller images
- Better security (fewer packages)

**Files to Modify**:
- `dashboard/Dockerfile` - Optimize build
- Consider custom Airflow image with only needed packages

---

## Data Quality & Validation

### 31. Data Validation Framework
**Priority**: High  
**Impact**: High  
**Effort**: Medium  
**Status**: Not Implemented

**Proposal**: Create comprehensive data validation framework with configurable rules.

**Validation Rules**:
- Schema validation
- Data type validation
- Range validation (prices, volumes)
- Business rule validation
- Referential integrity

**Benefits**:
- Ensure data quality
- Early error detection
- Configurable validation rules

**Files to Create**:
- `dags/market_data/validators/data_validator.py` - Validation framework
- `dags/market_data/validators/rules.py` - Validation rules

---

### 32. Data Profiling
**Priority**: Low  
**Impact**: Medium  
**Effort**: Medium  
**Status**: Not Implemented

**Proposal**: Add data profiling capabilities to understand data characteristics.

**Features**:
- Statistical summaries
- Data distribution analysis
- Missing value analysis
- Outlier detection

**Benefits**:
- Better understanding of data
- Data quality insights
- Anomaly detection

**Implementation**:
- Use pandas-profiling or similar
- Generate profiles after each load
- Store profiles for comparison

---

## Implementation Priority

### Phase 1: High Priority, High Impact (Next 1-2 Months)

1. **Access Control & User Management** (#11) - ⚠️ **CRITICAL** before production
2. **Batch API Calls for Backfill** (#1) - High impact on performance
3. **Prometheus Metrics Export** (#5) - Essential for monitoring
4. **Data Quality Checks** (#21) - Critical for data reliability
5. **Secrets Management** (#12) - Security requirement
6. **SQL Injection Prevention Audit** (#13) - Security requirement

### Phase 2: Medium Priority, Medium-High Impact (3-6 Months)

7. **Implement Caching Layer** (#2)
8. **Parallel Ticker Processing** (#3)
9. **Structured Logging with Context** (#6)
10. **Increase Test Coverage** (#8)
11. **Alert System for Dashboard** (#23)
12. **Data Validation Framework** (#31)

### Phase 3: Lower Priority, Nice to Have (6+ Months)

13. **Performance Regression Tests** (#9)
14. **Type Hints Coverage** (#25)
15. **API Documentation with Examples** (#18)
16. **Pre-commit Hooks** (#17)
17. **Standardize Error Handling** (#27)

---

## Resource Planning Summary

### High Resource Requirements
- **Kubernetes Deployment** (#28): Requires full K8s cluster (~$220-800/month, ~$500-2000/month for HA)
- **DataHub Integration** (#22, Option 3): Requires significant infrastructure (~$500-2000/month)
- **Prometheus + Grafana HA Cluster** (#5): Requires monitoring cluster (~$200-800/month for HA)
- **HashiCorp Vault** (#12, Option 2): Requires Vault server (~$50-500/month)
- **Redis Cluster** (#2, Production): Requires Redis cluster for HA (~$50-500/month)
- **Access Control System** (#11): Requires authentication infrastructure (~$0-100/month depending on solution)

### Medium Resource Requirements
- **Parallel Ticker Processing** (#3): May require worker cluster (~$50-200/month per worker, +$50-200/month for queue broker)
- **Caching Layer** (#2): Redis memory allocation (minimal if using existing Redis, ~$50-500/month for cluster)
- **Data Lineage (OpenLineage)** (#22, Option 1): Requires OpenLineage backend (~$50-200/month)
- **Prometheus Single Instance** (#5): Basic monitoring (~$50-200/month)
- **Access Control (Basic)** (#11): Minimal if using built-in auth (~$0-50/month)

### Low/No Resource Requirements
- **Batch API Calls** (#1): No additional resources (reduces resource usage)
- **Warehouse Load Optimization** (#4): No additional resources (improves efficiency)
- **Health Check Endpoint** (#7): Negligible overhead
- **Data Quality Checks** (#21): Minimal overhead (~5-10% additional processing)
- **Airflow Connections** (#12, Option 1): No additional resources (for secrets management)
- **Custom Lineage** (#22, Option 2): Minimal (uses existing database)

### Cluster Deployment Recommendations

#### When to Use Clusters
1. **High Availability Requirements**: 99.9%+ uptime SLA
2. **High Load**: Processing 50+ tickers simultaneously, high metrics volume
3. **Multi-Region**: Need for geographic distribution
4. **Scalability**: Dynamic scaling based on demand
5. **Production Environment**: Critical business operations

#### Cluster Architecture Patterns
1. **Worker Cluster** (Airflow Celery/K8s):
   - Use for: Parallel ticker processing, high task throughput
   - Setup: Celery workers or K8s executor with auto-scaling
   - Cost: ~$200-800/month for 3-5 worker nodes

2. **Redis Cluster** (Cache/Queue):
   - Use for: High cache hit rates, task queue for worker cluster
   - Setup: Redis Sentinel (HA) or Redis Cluster (sharding)
   - Cost: ~$50-500/month depending on size

3. **Monitoring Cluster** (Prometheus/Grafana):
   - Use for: High metrics volume, long-term retention, multi-region
   - Setup: Prometheus federation or Thanos/Cortex
   - Cost: ~$200-800/month for HA setup

4. **Kubernetes Cluster** (Full Stack):
   - Use for: Complete container orchestration, auto-scaling, multi-service
   - Setup: Managed (EKS/GKE/AKS) or self-hosted
   - Cost: ~$500-2000/month for production HA cluster

#### Migration Path to Clusters
1. **Phase 1**: Single instance deployment (current state)
2. **Phase 2**: Add worker cluster for parallel processing (#3)
3. **Phase 3**: Add Redis cluster for cache/queue HA (#2)
4. **Phase 4**: Add monitoring cluster for observability (#5)
5. **Phase 5**: Full Kubernetes migration (#28)

### Cost Optimization Recommendations
1. Start with low-resource improvements for quick wins
2. Use managed services for high-resource requirements (better TCO)
3. Consider cloud-native options (AWS Secrets Manager vs. self-hosted Vault)
4. Scale infrastructure incrementally based on actual usage
5. Monitor resource usage and optimize based on metrics
6. **Cluster Strategy**: Start single instance, migrate to cluster only when needed
7. **Auto-scaling**: Use cluster autoscaling to optimize costs (scale down during low usage)
8. **Resource Right-sizing**: Monitor and adjust cluster node sizes based on actual usage

---

## Notes

- All improvements should maintain backward compatibility
- Each improvement should include tests
- Documentation should be updated for each change
- Consider user feedback before implementing new features
- Prioritize improvements based on business value and technical debt
- **Resource planning**: Consider hardware, software, and infrastructure costs before implementation
- **Phased approach**: Start with low-resource improvements, scale infrastructure as needed
- **Cluster migration**: Plan cluster adoption based on actual requirements, not theoretical needs

---

**Next Steps**:
1. Review and prioritize improvements
2. Create implementation plan for Phase 1
3. Assign owners and timelines
4. Track progress in project management tool
5. Evaluate cluster requirements based on actual usage patterns