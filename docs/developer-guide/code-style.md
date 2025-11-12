# Code Style Guide

Standards and conventions for writing high-quality, maintainable code in this project.

---

## Table of Contents

- [Overview](#overview)
- [Python Style Guide](#python-style-guide)
- [Code Formatting](#code-formatting)
- [Naming Conventions](#naming-conventions)
- [Documentation](#documentation)
- [Type Hints](#type-hints)
- [Error Handling](#error-handling)
- [Testing Standards](#testing-standards)
- [Git Commit Messages](#git-commit-messages)

---

## Overview

This project follows:
- **PEP 8** - Python style guide
- **Black** - Code formatter
- **isort** - Import sorter
- **flake8** - Linter
- **Type hints** - Python 3.10+ type annotations

---

## Python Style Guide

### PEP 8 Compliance

We strictly follow [PEP 8](https://peps.python.org/pep-0008/) with these key points:

#### **Indentation**
```python
# ✅ Good: 4 spaces
def function():
    if condition:
        do_something()

# ❌ Bad: Tabs or 2 spaces
def function():
	if condition:
	  do_something()
```

#### **Line Length**
- **Maximum**: 127 characters
- **Preferred**: 88 characters (Black default)

```python
# ✅ Good
result = some_function(
    parameter1=value1,
    parameter2=value2,
    parameter3=value3
)

# ❌ Bad
result = some_function(parameter1=value1, parameter2=value2, parameter3=value3, parameter4=value4)
```

#### **Imports**
```python
# ✅ Good: Organized by isort
import os
import sys
from datetime import datetime
from typing import Dict, List

import pandas as pd
import requests

from market_data.config import get_config
from market_data.utils import validate_ticker

# ❌ Bad: Unorganized
from market_data.config import get_config
import pandas as pd
import os
from typing import Dict
```

#### **Blank Lines**
```python
# ✅ Good
import os


class MyClass:
    """Class docstring"""

    def method_one(self):
        pass

    def method_two(self):
        pass


def standalone_function():
    pass

# ❌ Bad: Too many or too few blank lines
import os

class MyClass:
    def method_one(self):
        pass
    def method_two(self):
        pass
def standalone_function():
    pass
```

---

## Code Formatting

### Black Formatter

**Configuration** (`.black.toml`):
```toml
[tool.black]
line-length = 88
target-version = ['py310']
include = '\.pyi?$'
```

**Usage**:
```bash
# Format all files
black dags/ tests/

# Check without modifying
black --check dags/ tests/
```

### isort

**Configuration** (`.isort.cfg`):
```ini
[settings]
profile = black
line_length = 88
known_first_party = market_data
```

**Usage**:
```bash
# Sort imports
isort dags/ tests/

# Check without modifying
isort --check-only dags/ tests/
```

### flake8

**Configuration** (`.flake8`):
```ini
[flake8]
max-line-length = 127
extend-ignore = E203, W503
exclude = .git,__pycache__,build,dist
max-complexity = 10
```

**Usage**:
```bash
# Check code
flake8 dags/market_data

# With specific rules
flake8 dags/ --select=E9,F63,F7,F82
```

---

## Naming Conventions

### General Rules

| Type | Convention | Example |
|------|------------|---------|
| **Variables** | `snake_case` | `market_data`, `api_client` |
| **Functions** | `snake_case` | `fetch_data()`, `validate_ticker()` |
| **Classes** | `PascalCase` | `MarketDataLogger`, `YahooFinanceClient` |
| **Constants** | `UPPER_SNAKE_CASE` | `MAX_RETRIES`, `API_BASE_URL` |
| **Private** | `_leading_underscore` | `_internal_function()`, `_helper_method()` |
| **Modules** | `snake_case` | `api_client.py`, `warehouse_config.py` |

### Examples

```python
# ✅ Good
class YahooFinanceClient:
    MAX_RETRIES = 3
    
    def __init__(self):
        self._session = requests.Session()
    
    def fetch_market_data(self, ticker: str) -> Dict:
        """Public method"""
        return self._make_request(ticker)
    
    def _make_request(self, ticker: str) -> Dict:
        """Private helper method"""
        pass

# ❌ Bad
class yahooFinanceClient:  # Wrong case
    maxRetries = 3  # Should be UPPER_CASE
    
    def FetchMarketData(self, Ticker: str):  # Wrong case
        return self.makeRequest(Ticker)  # Private should have _
```

### Descriptive Names

```python
# ✅ Good: Clear intent
def calculate_moving_average(prices: List[float], window: int) -> List[float]:
    """Calculate simple moving average"""
    pass

# ❌ Bad: Unclear abbreviations
def calc_ma(p: List[float], w: int) -> List[float]:
    pass
```

---

## Documentation

### Docstrings

Follow **Google Style** docstrings:

```python
def fetch_market_data(ticker: str, date: str, max_retries: int = 3) -> Dict:
    """
    Fetch market data from Yahoo Finance API.
    
    Retrieves OHLCV data for a specific ticker and date with automatic
    retry logic for handling rate limits and transient errors.
    
    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL')
        date: Date in YYYY-MM-DD format
        max_retries: Maximum number of retry attempts (default: 3)
    
    Returns:
        Dictionary containing:
            - ticker: str
            - date: str
            - open: float
            - high: float
            - low: float
            - close: float
            - volume: int
    
    Raises:
        ValueError: If ticker format is invalid
        requests.HTTPError: If API returns error after retries
        requests.Timeout: If request times out
    
    Example:
        >>> data = fetch_market_data('AAPL', '2025-11-09')
        >>> print(data['close'])
        259.57
    """
    pass
```

### Class Docstrings

```python
class WarehouseLoader:
    """
    Load market data from Parquet to data warehouse.
    
    Supports multiple load strategies (UPSERT, APPEND, TRUNCATE_INSERT)
    and handles batch processing with automatic transaction management.
    
    Attributes:
        config: Warehouse configuration dictionary
        connection: WarehouseConnection instance
        warehouse_type: Type of warehouse ('postgresql' or 'redshift')
    
    Example:
        >>> loader = WarehouseLoader()
        >>> result = loader.load_from_parquet('AAPL')
        >>> print(f"Loaded {result['records_loaded']} records")
    """
    pass
```

### Inline Comments

```python
# ✅ Good: Explain WHY, not WHAT
# Use 6 PM timestamp to ensure market has closed
timestamp = int(datetime.combine(date, time(18, 0)).timestamp())

# ❌ Bad: States the obvious
# Set timestamp variable
timestamp = int(datetime.combine(date, time(18, 0)).timestamp())
```

---

## Type Hints

### Basic Types

```python
from typing import Dict, List, Optional, Tuple, Union

def process_data(
    ticker: str,
    prices: List[float],
    metadata: Optional[Dict[str, str]] = None
) -> Tuple[float, float]:
    """Process market data"""
    pass
```

### Complex Types

```python
from typing import Callable, TypedDict

class MarketData(TypedDict):
    ticker: str
    date: str
    close: float
    volume: int

def apply_transformation(
    data: MarketData,
    transform: Callable[[float], float]
) -> MarketData:
    """Apply transformation function to close price"""
    pass
```

### Return Types

```python
# ✅ Good: Specify return type
def get_ticker() -> str:
    return "AAPL"

def calculate_indicators(data: pd.DataFrame) -> pd.DataFrame:
    return data

# ❌ Bad: Missing return type
def get_ticker():
    return "AAPL"
```

---

## Error Handling

### Exception Hierarchy

```python
# ✅ Good: Specific exceptions
try:
    data = fetch_data(ticker)
except requests.HTTPError as e:
    logger.error(f"API error: {e}")
    raise
except requests.Timeout:
    logger.warning("Request timed out, retrying...")
    retry_fetch(ticker)
except ValueError as e:
    logger.error(f"Invalid ticker: {e}")
    raise

# ❌ Bad: Catch-all exception
try:
    data = fetch_data(ticker)
except Exception:
    pass  # Silent failure!
```

### Custom Exceptions

```python
class MarketDataError(Exception):
    """Base exception for market data operations"""
    pass

class InvalidTickerError(MarketDataError):
    """Raised when ticker format is invalid"""
    pass

class APIRateLimitError(MarketDataError):
    """Raised when API rate limit is exceeded"""
    pass

# Usage
if not ticker:
    raise InvalidTickerError(f"Ticker cannot be empty")
```

### Logging Errors

```python
# ✅ Good: Log with context
try:
    result = risky_operation()
except Exception as e:
    logger.error(
        "Operation failed",
        extra={
            "error": str(e),
            "ticker": ticker,
            "attempt": retry_count
        },
        exc_info=True  # Include traceback
    )
    raise

# ❌ Bad: Generic log
except Exception as e:
    logger.error("Error")
```

---

## Testing Standards

### Test Organization

```python
# ✅ Good: Organized by class
class TestYahooFinanceClient:
    """Tests for YahooFinanceClient"""
    
    def test_fetch_market_data_success(self):
        """Test successful data fetch"""
        pass
    
    def test_fetch_market_data_with_retries(self):
        """Test retry logic on failure"""
        pass
    
    def test_fetch_market_data_invalid_ticker(self):
        """Test error handling for invalid ticker"""
        pass

# ❌ Bad: Unorganized
def test_1():
    pass

def test_2():
    pass
```

### Test Names

```python
# ✅ Good: Descriptive names
def test_validate_ticker_accepts_uppercase():
    pass

def test_validate_ticker_rejects_empty_string():
    pass

def test_calculate_sma_with_insufficient_data_returns_nan():
    pass

# ❌ Bad: Vague names
def test_ticker():
    pass

def test_sma():
    pass
```

### Assertions

```python
# ✅ Good: Clear assertions with messages
assert result['close'] == 259.57, "Close price should match API response"
assert len(data) > 0, "Should return at least one record"

# ❌ Bad: No context
assert result['close'] == 259.57
assert len(data) > 0
```

---

## Git Commit Messages

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

| Type | Usage |
|------|-------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Formatting, no code change |
| `refactor` | Code restructuring |
| `test` | Adding/updating tests |
| `chore` | Maintenance tasks |

### Examples

```bash
# ✅ Good
feat(warehouse): Add multi-environment configuration

Implement support for PostgreSQL (dev) and Redshift (staging/prod)
with automatic environment detection based on ENVIRONMENT variable.

- Add warehouse_config.py for connection management
- Implement QueuePool for PostgreSQL, NullPool for Redshift
- Add comprehensive unit tests

Closes #123

# ❌ Bad
fixed stuff
```

### Scopes

- `warehouse`: Data warehouse related
- `dag`: DAG modifications
- `api`: API client changes
- `tests`: Test updates
- `docs`: Documentation
- `ci`: CI/CD pipeline

---

## Code Review Checklist

Before submitting PR, ensure:

- [ ] Code follows PEP 8
- [ ] Formatted with Black
- [ ] Imports sorted with isort
- [ ] No flake8 warnings
- [ ] Type hints added
- [ ] Docstrings for public functions/classes
- [ ] Tests added/updated
- [ ] Test coverage > 70%
- [ ] No print() statements (use logger)
- [ ] No hardcoded values (use config)
- [ ] Error handling implemented
- [ ] Git commit messages follow format

---

## Tools Setup

### Pre-commit Hooks

Create `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.11.0
    hooks:
      - id: black
  
  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
  
  - repo: https://github.com/pycqa/flake8
    rev: 6.1.0
    hooks:
      - id: flake8
```

Install:
```bash
pip install pre-commit
pre-commit install
```

### IDE Configuration

#### VSCode (`.vscode/settings.json`)
```json
{
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "[python]": {
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    }
  }
}
```

---

## Related Documentation

- [Contributing Guide](contributing.md)
- [Testing Guide](testing.md)
- [API Reference](api-reference.md)

