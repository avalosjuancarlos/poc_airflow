# Contributing Guide

Welcome! We're excited that you're interested in contributing to the Airflow Market Data Pipeline project.

---

## Table of Contents

- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing Requirements](#testing-requirements)
- [Pull Request Process](#pull-request-process)
- [Community Guidelines](#community-guidelines)

---

## Getting Started

### Prerequisites

- **Git** installed and configured
- **Docker Desktop** (v20.10+)
- **Python 3.10** (for local development)
- **GitHub account** with SSH or HTTPS access

### Fork and Clone

```bash
# Fork the repository on GitHub first, then:

# Clone your fork
git clone git@github.com:YOUR_USERNAME/poc_airflow.git
cd poc_airflow

# Add upstream remote
git remote add upstream git@github.com:avalosjuancarlos/poc_airflow.git

# Verify remotes
git remote -v
```

### Initial Setup

```bash
# Copy environment template
cp env.template .env

# Start development environment
docker compose up -d

# Verify services
docker compose ps
```

---

## Development Workflow

### 1. Create a Feature Branch

```bash
# Update main branch
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/your-feature-name

# Examples:
# feature/add-stock-screener
# fix/api-timeout-issue
# docs/improve-warehouse-guide
```

### Branch Naming Convention

| Type | Prefix | Example |
|------|--------|---------|
| **New Feature** | `feature/` | `feature/add-ml-predictions` |
| **Bug Fix** | `fix/` | `fix/warehouse-connection-leak` |
| **Documentation** | `docs/` | `docs/add-deployment-guide` |
| **Refactoring** | `refactor/` | `refactor/simplify-api-client` |
| **Testing** | `test/` | `test/increase-coverage` |
| **Chore** | `chore/` | `chore/upgrade-dependencies` |

### 2. Make Your Changes

```bash
# Make changes to code
vim dags/market_data/operators/new_operator.py

# Add tests
vim tests/unit/test_new_operator.py

# Update documentation
vim docs/user-guide/new-feature.md
```

### 3. Run Tests Locally

```bash
# Run all tests
docker compose -f docker-compose.test.yml up test

# Run specific test file
docker compose exec airflow-webserver pytest tests/unit/test_new_operator.py -v

# Check coverage
docker compose exec airflow-webserver pytest --cov=dags/market_data --cov-report=term
```

### 4. Run Linting

```bash
# Format code
docker compose exec airflow-webserver black dags/market_data tests/

# Sort imports
docker compose exec airflow-webserver isort dags/market_data tests/

# Check linting
docker compose exec airflow-webserver flake8 dags/market_data
```

### 5. Commit Changes

```bash
# Stage changes
git add dags/market_data/operators/new_operator.py
git add tests/unit/test_new_operator.py
git add docs/user-guide/new-feature.md

# Commit with descriptive message
git commit -m "feat(operators): Add NewOperator for stock screening

Implement NewOperator to filter stocks based on technical indicators:
- Support for multiple filter criteria
- Configurable thresholds
- Comprehensive error handling

- Add unit tests with 90% coverage
- Add user guide documentation

Closes #123"
```

**Commit Message Format**: See [Code Style Guide - Git Commit Messages](code-style.md#git-commit-messages)

### 6. Push to Your Fork

```bash
# Push feature branch to your fork
git push origin feature/your-feature-name
```

### 7. Create Pull Request

1. Go to https://github.com/avalosjuancarlos/poc_airflow
2. Click **"Compare & pull request"**
3. Fill out the PR template (see below)
4. Click **"Create pull request"**

---

## Coding Standards

### Required

- ✅ **PEP 8** compliance
- ✅ **Black** formatting (88 char line length)
- ✅ **isort** import sorting
- ✅ **flake8** linting (max complexity 10)
- ✅ **Type hints** for function signatures
- ✅ **Docstrings** for public functions/classes
- ✅ **No print() statements** (use logger)

### Example

```python
from typing import Dict, List

from market_data.utils import get_logger

logger = get_logger(__name__)


def calculate_moving_average(prices: List[float], window: int) -> List[float]:
    """
    Calculate simple moving average.
    
    Args:
        prices: List of price values
        window: Window size for moving average
    
    Returns:
        List of moving average values
    
    Raises:
        ValueError: If window is larger than prices length
    """
    if window > len(prices):
        raise ValueError(f"Window ({window}) larger than data ({len(prices)})")
    
    logger.debug(f"Calculating SMA with window={window}")
    
    # Implementation
    return moving_averages
```

**Full Guide**: See [Code Style Guide](code-style.md)

---

## Testing Requirements

### Minimum Standards

- ✅ **Unit tests** for all new functions/classes
- ✅ **Integration tests** for DAG modifications
- ✅ **Test coverage ≥ 70%** for new code
- ✅ **All existing tests pass**
- ✅ **Mock external dependencies** (API calls, DB)

### Test Structure

```python
import pytest
from unittest.mock import Mock, patch

from market_data.operators import calculate_indicators


class TestCalculateIndicators:
    """Test suite for calculate_indicators function"""
    
    def test_calculates_sma_correctly(self):
        """Test SMA calculation with valid data"""
        # Arrange
        data = {"close": [100, 110, 120]}
        
        # Act
        result = calculate_indicators(data)
        
        # Assert
        assert "sma_7" in result
        assert result["sma_7"][-1] == pytest.approx(110.0)
    
    @patch("market_data.operators.YahooFinanceClient")
    def test_handles_api_failure(self, mock_client):
        """Test error handling when API fails"""
        # Arrange
        mock_client.fetch_data.side_effect = requests.HTTPError("500 Server Error")
        
        # Act & Assert
        with pytest.raises(requests.HTTPError):
            calculate_indicators(mock_client, "AAPL")
```

### Running Tests

```bash
# All tests
docker compose -f docker-compose.test.yml up test

# Specific file
docker compose exec airflow-webserver pytest tests/unit/test_operators.py -v

# With coverage
docker compose exec airflow-webserver pytest \
  --cov=dags/market_data \
  --cov-report=html \
  --cov-report=term

# View coverage report
open htmlcov/index.html
```

**Full Guide**: See [Testing Guide](testing.md)

---

## Pull Request Process

### Before Submitting

- [ ] Code follows [Code Style Guide](code-style.md)
- [ ] All tests pass locally
- [ ] Coverage ≥ 70%
- [ ] Documentation updated (if applicable)
- [ ] CHANGELOG.md updated (for significant changes)
- [ ] Commit messages follow format
- [ ] Branch is up to date with main

### PR Template

```markdown
## Description

Brief description of changes.

## Type of Change

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Motivation and Context

Why is this change required? What problem does it solve?

Related issue: #123

## How Has This Been Tested?

- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed

## Screenshots (if applicable)

## Checklist

- [ ] Code follows project style guidelines
- [ ] Self-review performed
- [ ] Code commented (particularly complex areas)
- [ ] Documentation updated
- [ ] No new warnings generated
- [ ] Tests added that prove fix/feature works
- [ ] All tests pass locally
- [ ] Dependent changes merged
```

### Review Process

1. **Automated Checks** (GitHub Actions)
   - ✅ Tests pass
   - ✅ Linting passes
   - ✅ Coverage ≥ 70%

2. **Code Review** (Maintainers)
   - Code quality
   - Architecture fit
   - Test adequacy
   - Documentation completeness

3. **Approval**
   - At least 1 maintainer approval required
   - All comments addressed

4. **Merge**
   - Squash and merge (default)
   - Merge commit (for multi-commit features)
   - Rebase and merge (for clean history)

---

## Community Guidelines

### Code of Conduct

- **Be respectful**: Treat everyone with respect
- **Be collaborative**: Work together towards common goals
- **Be inclusive**: Welcome contributors of all backgrounds
- **Be constructive**: Provide helpful, actionable feedback
- **Be patient**: Remember everyone is learning

### Communication Channels

- **GitHub Issues**: Bug reports, feature requests
- **GitHub Discussions**: Questions, ideas, general discussion
- **Pull Requests**: Code contributions

### Reporting Issues

**Good Issue Report**:
```markdown
## Bug Report

**Description**
API client fails with 429 error after 3 retries

**To Reproduce**
1. Configure DAG with ticker='AAPL'
2. Run DAG multiple times in quick succession
3. Observe 429 errors in logs

**Expected Behavior**
Should handle rate limiting with exponential backoff

**Environment**
- Airflow version: 2.11.0
- Python version: 3.10
- Docker Compose version: 2.0.1

**Logs**
```
[ERROR] requests.exceptions.HTTPError: 429 Too Many Requests
```

**Additional Context**
Seems to happen only during market hours
```

### Feature Requests

**Good Feature Request**:
```markdown
## Feature Request

**Is your feature request related to a problem?**
Currently, we can only fetch data for one ticker at a time.

**Describe the solution you'd like**
Add support for batch fetching multiple tickers in parallel.

**Describe alternatives you've considered**
- Running multiple DAG instances (inefficient)
- Using Dynamic Task Mapping (complex)

**Additional context**
This would improve performance for portfolio tracking use cases.
```

---

## Development Tips

### Local Development

```bash
# Run a single DAG for testing
docker compose exec airflow-scheduler airflow dags test get_market_data 2025-11-09

# Test a single task
docker compose exec airflow-scheduler airflow tasks test get_market_data validate_ticker 2025-11-09

# Check DAG for errors
docker compose exec airflow-scheduler airflow dags list-import-errors

# View logs
docker compose logs -f airflow-worker
```

### Debugging

```python
# Add breakpoint in code
import pdb; pdb.set_trace()

# Or use built-in breakpoint() (Python 3.7+)
breakpoint()
```

### Performance Testing

```python
import time

start = time.time()
result = your_function()
elapsed = time.time() - start

logger.info(f"Function took {elapsed:.2f}s")
```

---

## Versioning

This project follows [Semantic Versioning](https://semver.org/):

- **MAJOR**: Incompatible API changes
- **MINOR**: Backwards-compatible functionality
- **PATCH**: Backwards-compatible bug fixes

Example: `v2.11.0`

---

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (Apache License 2.0).

---

## Getting Help

- **Documentation**: Check [docs/](../../docs/)
- **Issues**: Search [existing issues](https://github.com/avalosjuancarlos/poc_airflow/issues)
- **Discussions**: Ask in [GitHub Discussions](https://github.com/avalosjuancarlos/poc_airflow/discussions)

---

## Recognition

Contributors will be recognized in:
- `CONTRIBUTORS.md` file
- Release notes (for significant contributions)
- README.md acknowledgments

---

**Thank you for contributing!** 🎉

Your efforts help make this project better for everyone.

---

## Related Documentation

- [Code Style Guide](code-style.md)
- [Testing Guide](testing.md)
- [Architecture Overview](architecture.md)

