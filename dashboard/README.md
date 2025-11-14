# Market Data Dashboard

Interactive web dashboard for visualizing market data and technical indicators.

---

## Features

- 📊 **Interactive Charts**: Candlestick, line charts, bar charts
- 📈 **Technical Indicators**: SMA, RSI, MACD, Bollinger Bands
- 💹 **Returns & Volatility**: Daily returns and 20-day volatility
- 🔄 **Real-time Updates**: Auto-refresh from warehouse
- 🌍 **Multi-Environment**: Development, staging, production
- ⬇️ **Data Export**: Download data as CSV

---

## Quick Start

### 1. Configure Environment

```bash
# Copy template
cp env.template .env

# Edit with your credentials
nano .env
```

### 2. Run Dashboard

**Development** (connects to local warehouse):

```bash
# From dashboard directory
docker compose up -d

# Or without Docker
pip install -r requirements.txt
streamlit run app.py
```

**Access**: http://localhost:8501

---

## Configuration

### Environment Variables

#### Required

```bash
ENVIRONMENT=development  # or staging, production

# Development (PostgreSQL)
# Docker: use warehouse-postgres:5432
# Local: use localhost:5433
DEV_WAREHOUSE_HOST=warehouse-postgres
DEV_WAREHOUSE_PORT=5432
DEV_WAREHOUSE_DATABASE=market_data_warehouse
DEV_WAREHOUSE_USER=warehouse_user
DEV_WAREHOUSE_PASSWORD=your_password
```

#### Optional

```bash
DASHBOARD_TITLE="Market Data Dashboard"
DASHBOARD_PORT=8501
```

### Staging/Production

For staging or production, set:

```bash
ENVIRONMENT=production

# Redshift credentials
PROD_WAREHOUSE_HOST=your-cluster.region.redshift.amazonaws.com
PROD_WAREHOUSE_PORT=5439
PROD_WAREHOUSE_DATABASE=market_data_prod
PROD_WAREHOUSE_USER=your_user
PROD_WAREHOUSE_PASSWORD=your_password
PROD_WAREHOUSE_REGION=us-east-1
```

---

## Usage

### Select Ticker

Use sidebar dropdown to select ticker (e.g., AAPL, GOOGL, MSFT)

### Choose Date Range

- 1 Month
- 3 Months
- 6 Months
- 1 Year
- All Data

### View Tabs

1. **Price & Volume**: Candlestick chart with volume
2. **Moving Averages**: Price with SMA 7, 14, 30
3. **Bollinger Bands**: Volatility bands
4. **RSI**: Relative Strength Index with overbought/oversold levels
5. **MACD**: MACD line, signal, and histogram
6. **Returns & Volatility**: Daily returns and 20-day volatility
7. **Data Table**: Raw data with download option

---

## Docker Deployment

### Development

```bash
# Start dashboard
cd dashboard
docker compose up -d

# View logs
docker compose logs -f

# Stop
docker compose down
```

### Production

```bash
# Use production .env
ENVIRONMENT=production docker compose up -d

# Or with custom port
DASHBOARD_PORT=8080 docker compose up -d
```

---

## Troubleshooting

### Connection Errors

**Error**: `could not connect to server`

**Solution**:
```bash
# Check warehouse is running
cd ..
docker compose ps warehouse-postgres

# Verify credentials in .env
grep DEV_WAREHOUSE .env
```

### No Data Showing

**Error**: No tickers in dropdown

**Solution**:
1. Ensure DAG has run at least once
2. Check warehouse has data:
   ```bash
   docker compose exec warehouse-postgres psql -U warehouse_user -d market_data_warehouse \
     -c "SELECT ticker, COUNT(*) FROM fact_market_data GROUP BY ticker;"
   ```

### Port Already in Use

**Error**: `Port 8501 is already in use`

**Solution**:
```bash
# Use different port
DASHBOARD_PORT=8502 streamlit run app.py
```

---

## Development

### Local Development (without Docker)

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment
export ENVIRONMENT=development
export DEV_WAREHOUSE_HOST=localhost
export DEV_WAREHOUSE_PORT=5433
export DEV_WAREHOUSE_PASSWORD=your_password

# Run
streamlit run app.py
```

### Add New Visualizations

Edit `app.py`:

```python
def plot_custom_indicator(df, ticker):
    """Your custom visualization"""
    fig = go.Figure()
    # Your plot logic
    return fig

# Add to tabs
tabs = st.tabs([..., "Custom"])
with tabs[N]:
    st.plotly_chart(plot_custom_indicator(df, ticker))
```

---

## Architecture

```
Dashboard (Streamlit) 
    ↓
SQLAlchemy Engine
    ↓
Database (PostgreSQL/Redshift)
    ↓
fact_market_data table
```

**Caching**: Data cached for 5 minutes (TTL=300s)

**Multi-Environment**: Reads from different warehouses based on `ENVIRONMENT` variable

---

## Security

- ✅ Passwords via environment variables
- ✅ No credentials in code
- ✅ `.env` in `.gitignore`
- ⚠️ For production, use VPN or auth proxy

---

## Performance

### Optimization Tips

1. **Adjust cache TTL**:
   ```python
   @st.cache_data(ttl=600)  # 10 minutes
   ```

2. **Limit data range**:
   - Don't load "All Data" for tickers with years of data
   - Use pagination for large datasets

3. **Index database**:
   ```sql
   CREATE INDEX idx_ticker_date ON fact_market_data (ticker, date DESC);
   ```

---

## Related Documentation

- [Data Warehouse Guide](../docs/user-guide/data-warehouse.md)
- [Configuration Guide](../docs/user-guide/configuration.md)
- [Architecture Overview](../docs/architecture/overview.md)

---

**Version**: 1.0.0  
**Last Updated**: 2025-11-14

