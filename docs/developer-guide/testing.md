## 🧪 Guía de Testing - Market Data DAG

Esta guía explica la estrategia de testing, cómo ejecutar tests y cómo contribuir con nuevos tests.

## 📋 Tabla de Contenidos

- [Arquitectura de Testing](#arquitectura-de-testing)
- [Tipos de Tests](#tipos-de-tests)
- [Ejecutar Tests](#ejecutar-tests)
- [Escribir Tests](#escribir-tests)
- [CI/CD](#cicd)
- [Coverage](#coverage)

---

## 🏗️ Arquitectura de Testing

### Estructura de Directorios

```
tests/
├── __init__.py
├── conftest.py                 # Fixtures compartidas
├── unit/                       # Tests unitarios
│   ├── __init__.py
│   ├── test_validators.py      # Tests de validadores
│   ├── test_config.py          # Tests de configuración
│   └── test_api_client.py      # Tests del API client
└── integration/                # Tests de integración
    ├── __init__.py
    ├── test_dag_validation.py  # Validación del DAG
    └── test_dag_execution.py   # Ejecución del DAG
```

### Dependencias de Testing

```
pytest==7.4.3           # Framework de testing
pytest-cov==4.1.0       # Coverage reporting
pytest-mock==3.12.0     # Mocking utilities
requests-mock==1.11.0   # HTTP request mocking
freezegun==1.4.0        # Time/date mocking
```

> Todas las dependencias productivas viven en `requirements.txt`, mientras que `requirements-dev.txt` extiende ese archivo con paquetes de testing y linting. Los servicios definidos en `docker-compose.test.yml` instalan automáticamente `requirements-dev.txt`.

---

## 🎯 Tipos de Tests

### 1. Tests Unitarios (`tests/unit/`)

**Objetivo**: Probar funciones individuales de forma aislada

**Características**:
- ✅ Rápidos (< 1 segundo cada uno)
- ✅ Sin dependencias externas
- ✅ Sin conexión a red/base de datos
- ✅ Usan mocks para dependencias

**Alcance**:
- Validadores (`test_validators.py`)
- Configuración (`test_config.py`)
- API Client (`test_api_client.py`)

**Ejemplo**:
```python
def test_validate_ticker_uppercase():
    result = validate_ticker_format('AAPL')
    assert result == 'AAPL'
```

### 2. Tests de Integración (`tests/integration/`)

**Objetivo**: Probar el DAG completo y la integración entre componentes

**Características**:
- ✅ Prueban el flujo completo
- ✅ Validan estructura del DAG
- ✅ Verifican dependencias entre tareas
- ✅ Validan configuración de Airflow

**Alcance**:
- Validación del DAG (`test_dag_validation.py`)
- Ejecución del DAG (`test_dag_execution.py`)

**Ejemplo**:
```python
def test_dag_loaded(dagbag):
    assert 'get_market_data' in dagbag.dags
    assert len(dagbag.import_errors) == 0
```

---

## 🚀 Ejecutar Tests

### Todos los Tests (Docker Compose recomendado)

```bash
docker compose -f docker-compose.test.yml up test
# o
make test
```

### Tests locales (sin Docker)

```bash
# Desde la raíz del proyecto
export PYTHONPATH="${PWD}/dags:${PYTHONPATH}"
pytest

# Con coverage
pytest --cov=dags/market_data --cov-report=html
```

### Solo Tests Unitarios

```bash
# Docker Compose
docker compose -f docker-compose.test.yml up test-unit-only

# Local (sin Docker)
pytest tests/unit -v
pytest -m "unit" -v
```

### Solo Tests de Integración

```bash
# Docker Compose
docker compose -f docker-compose.test.yml up test-integration-only

# Local (sin Docker)
pytest tests/integration -v
pytest -m "integration" -v
```

### Test Específico

```bash
# Archivo específico
pytest tests/unit/test_validators.py -v

# Clase específica
pytest tests/unit/test_validators.py::TestValidateTickerFormat -v

# Test específico
pytest tests/unit/test_validators.py::TestValidateTickerFormat::test_valid_ticker_uppercase -v
```

### Con Output Detallado

```bash
# Verbose output
pytest -v -s

# Mostrar solo fallos
pytest --tb=short

# Detener en primer fallo
pytest -x
```

---

## 🐳 Ejecutar Tests en Docker

### Opción 1: En el contenedor de Airflow

```bash
# Entrar al contenedor
docker compose exec airflow-scheduler bash

# Instalar dependencias de testing/linting
pip install --quiet --no-cache-dir -r requirements-dev.txt

# Ejecutar tests
cd /opt/airflow
export PYTHONPATH="/opt/airflow/dags:${PYTHONPATH}"
pytest tests/ -v
```

### Opción 2: Contenedor dedicado para tests (docker-compose.test.yml)

El repositorio ya incluye `docker-compose.test.yml` con todos los servicios de testing/linting:

- `test`, `test-unit-only`, `test-integration-only`, `test-coverage`
- `lint` (flake8 + black + isort, con dependencias de `requirements-dev.txt`)

```bash
# Ejecutar test suite completa
docker compose -f docker-compose.test.yml up test

# Solo linters
docker compose -f docker-compose.test.yml up lint
```

---

## ✍️ Escribir Nuevos Tests

### Estructura de un Test Unitario

```python
import pytest
import sys
import os

# Add dags to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../dags'))

from market_data.utils.validators import validate_ticker_format


class TestMyFeature:
    """Tests for my feature"""
    
    def test_basic_functionality(self):
        """Test basic functionality"""
        result = my_function('input')
        assert result == 'expected'
    
    def test_edge_case(self):
        """Test edge case"""
        with pytest.raises(ValueError, match="error message"):
            my_function('invalid')
    
    @pytest.fixture
    def sample_data(self):
        """Fixture for test data"""
        return {'key': 'value'}
    
    def test_with_fixture(self, sample_data):
        """Test using fixture"""
        result = my_function(sample_data)
        assert result is not None
```

### Uso de Mocks

```python
from unittest.mock import patch, Mock

@patch('market_data.utils.api_client.requests.get')
def test_api_call(mock_get):
    """Test API call with mock"""
    # Setup mock
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'data': 'test'}
    mock_get.return_value = mock_response
    
    # Execute
    result = fetch_data()
    
    # Assert
    assert result == {'data': 'test'}
    mock_get.assert_called_once()
```

### Fixtures Compartidas

Usa fixtures en `tests/conftest.py`:

```python
@pytest.fixture
def mock_context():
    """Shared Airflow context for tests"""
    return {
        'dag_run': Mock(conf={'ticker': 'AAPL'}),
        'task_instance': Mock(),
        'execution_date': datetime(2023, 11, 9)
    }
```

---

## 📊 Coverage

### Generar Reporte de Coverage

```bash
# Ejecutar con coverage
pytest --cov=dags/market_data --cov-report=html

# Ver reporte en navegador
open htmlcov/index.html
```

### Coverage Report

El proyecto está configurado para:
- **Mínimo 80% de coverage** (`--cov-fail-under=80`)
- Reportes en HTML y terminal
- Exclusión de archivos de configuración

### Ver Coverage por Archivo

```bash
pytest --cov=dags/market_data --cov-report=term-missing
```

Output:
```
Name                                          Stmts   Miss  Cover   Missing
---------------------------------------------------------------------------
dags/market_data/config/settings.py              45      3    93%   23-25
dags/market_data/utils/api_client.py             67      5    93%   45, 78-81
dags/market_data/utils/validators.py             18      1    94%   42
dags/market_data/operators/market_data_ops.py    52      4    92%   67-70
---------------------------------------------------------------------------
TOTAL                                           182     13    93%
```

---

## 🤖 CI/CD con GitHub Actions

### Workflows Configurados

#### 1. CI Workflow (`.github/workflows/ci.yml`)

**Triggers**:
- Push a branches: `main`, `develop`, `test-*`
- Pull requests a: `main`, `develop`

**Jobs**:

**a) Test Job**
```yaml
- Install dependencies
- Run unit tests with coverage
- Run integration tests
- Upload coverage to Codecov
```

**b) Lint Job**
```yaml
- Run flake8
- Check formatting with black
- Check import sorting with isort
```

**c) DAG Validation Job**
```yaml
- Validate DAG syntax
- Check for import errors
- Verify DAG structure
```

#### 2. Deploy Workflow (`.github/workflows/deploy.yml`)

**Triggers**:
- Push to `main` → Deploy to Development
- Tag `v*` → Deploy to Production

**Jobs**:
- Deploy to Development
- Deploy to Production (on tags)
- Create GitHub Release

### Ver Resultados de CI

1. Ve a tu repositorio en GitHub
2. Click en la pestaña "Actions"
3. Verás todos los workflow runs
4. Click en un run para ver detalles

### Status Badges

Agregar al README.md:

```markdown
![CI](https://github.com/avalosjuancarlos/poc_airflow/actions/workflows/ci.yml/badge.svg)
![Coverage](https://codecov.io/gh/avalosjuancarlos/poc_airflow/branch/main/graph/badge.svg)
```

---

## 🔍 Debugging Tests

### Ver Output Detallado

```bash
# Verbose + output no capturado
pytest -v -s

# Mostrar variables locales en errores
pytest -l

# Full traceback
pytest --tb=long
```

### Ejecutar Test Específico en Debug

```bash
# Con breakpoint
pytest tests/unit/test_validators.py::TestValidateTickerFormat::test_valid_ticker_uppercase -v -s

# Con pdb (Python debugger)
pytest --pdb
```

### Ver Solo Errores

```bash
# Mostrar solo test que fallan
pytest --failed-first

# Rerrun solo los que fallaron
pytest --lf
```

---

## 📝 Best Practices

### 1. Nomenclatura de Tests

✅ **Bueno**:
```python
def test_validate_ticker_uppercase()
def test_fetch_data_with_rate_limit()
def test_sensor_returns_false_on_timeout()
```

❌ **Malo**:
```python
def test1()
def test_function()
def test_stuff()
```

### 2. Organización

```python
class TestFeature:
    """Group related tests together"""
    
    def test_basic_case(self):
        """Test description"""
        pass
    
    def test_edge_case(self):
        """Test edge case"""
        pass
```

### 3. Assertions Claras

✅ **Bueno**:
```python
assert result == 'AAPL', f"Expected AAPL but got {result}"
assert len(data) > 0, "Data should not be empty"
```

❌ **Malo**:
```python
assert result
assert data
```

### 4. Usar Fixtures

```python
@pytest.fixture
def client():
    """Reusable test data"""
    return YahooFinanceClient(...)

def test_something(client):
    """Use fixture"""
    result = client.fetch_data(...)
```

### 5. Marcar Tests

```python
@pytest.mark.unit
def test_unit_function():
    pass

@pytest.mark.integration
def test_integration_flow():
    pass

@pytest.mark.slow
def test_slow_operation():
    pass
```

Ejecutar por marker:
```bash
pytest -m "unit"
pytest -m "integration"
pytest -m "not slow"
```

---

## 📊 Métricas de Calidad

### Objetivos

| Métrica | Objetivo | Actual |
|---------|----------|--------|
| **Coverage** | ≥ 80% | TBD |
| **Tests Unitarios** | > 30 | 25+ |
| **Tests de Integración** | > 10 | 10+ |
| **Tiempo de Ejecución** | < 2 min | TBD |

### Verificar Métricas

```bash
# Coverage total
pytest --cov=dags/market_data --cov-report=term

# Número de tests
pytest --collect-only | grep "test session starts" -A 1

# Tiempo de ejecución
pytest --durations=10
```

---

## 🚨 Troubleshooting

### Import Errors

**Problema**: `ModuleNotFoundError: No module named 'market_data'`

**Solución**:
```bash
export PYTHONPATH="${PWD}/dags:${PYTHONPATH}"
pytest
```

### Airflow Not Found

**Problema**: `ModuleNotFoundError: No module named 'airflow'`

**Solución**:
```bash
pip install apache-airflow==2.11.0
```

### Test Discovery Issues

**Problema**: Pytest no encuentra los tests

**Solución**:
```bash
# Verificar que pytest.ini existe
cat pytest.ini

# Ejecutar con discovery explícita
pytest --collect-only
```

### Mock Issues

**Problema**: Mocks no funcionan correctamente

**Solución**:
```python
# Usar patch con path completo
@patch('market_data.utils.api_client.requests.get')  # ✅
# No usar:
@patch('requests.get')  # ❌
```

---

## 🔄 Workflow de Desarrollo con Tests

### 1. Desarrollar Feature

```bash
# Crear branch
git checkout -b feature/nueva-funcionalidad

# Escribir código
vim dags/market_data/utils/nueva_funcion.py
```

### 2. Escribir Tests

```bash
# Escribir tests primero (TDD) o después
vim tests/unit/test_nueva_funcion.py
```

### 3. Ejecutar Tests Localmente

```bash
# Ejecutar tests
pytest tests/unit/test_nueva_funcion.py -v

# Verificar coverage
pytest --cov=dags/market_data tests/unit/test_nueva_funcion.py
```

### 4. Verificar CI Pasa

```bash
# Commit y push
git add .
git commit -m "feat: Add nueva funcionalidad"
git push origin feature/nueva-funcionalidad

# Verificar en GitHub Actions
# https://github.com/avalosjuancarlos/poc_airflow/actions
```

### 5. Crear PR

```bash
gh pr create --base main --head feature/nueva-funcionalidad
```

---

## 📈 Comandos Útiles

### Ejecución de Tests

```bash
# Todos los tests
pytest

# Solo unit tests
pytest tests/unit -v

# Solo integration tests
pytest tests/integration -v

# Con coverage
pytest --cov=dags/market_data --cov-report=html

# Tests que fallaron la última vez
pytest --lf

# Detener en primer fallo
pytest -x

# Ejecutar en paralelo (con pytest-xdist)
pytest -n auto
```

### Debugging

```bash
# Verbose con print statements
pytest -v -s

# Con debugger
pytest --pdb

# Ver locals en fallo
pytest -l

# Full traceback
pytest --tb=long
```

### Coverage

```bash
# Coverage simple
pytest --cov=dags/market_data

# Coverage con missing lines
pytest --cov=dags/market_data --cov-report=term-missing

# Coverage HTML
pytest --cov=dags/market_data --cov-report=html
open htmlcov/index.html

# Coverage XML (para CI)
pytest --cov=dags/market_data --cov-report=xml
```

---

## 📚 Fixtures Disponibles

### En `conftest.py`

```python
# Mock DAG run
mock_dag_run  # Returns Mock with conf={'ticker': 'AAPL', 'date': '2023-11-09'}

# Mock task instance
mock_task_instance  # Returns Mock with xcom_push/pull methods

# Mock Airflow context
mock_context  # Returns complete Airflow context dict

# Sample market data
sample_market_data  # Returns sample market data structure

# Yahoo API response
yahoo_api_response  # Returns formatted API response
```

### Uso en Tests

```python
def test_my_function(mock_context, sample_market_data):
    """Test using shared fixtures"""
    result = my_function(sample_market_data, **mock_context)
    assert result is not None
```

---

## 🎨 Ejemplo de Test Completo

```python
"""
Test example showing best practices
"""

import pytest
from unittest.mock import patch, Mock


class TestMarketDataFetcher:
    """Tests for market data fetching"""
    
    @pytest.fixture
    def api_client(self):
        """Create API client for tests"""
        from market_data.utils.api_client import YahooFinanceClient
        return YahooFinanceClient(
            base_url='https://api.test.com',
            headers={'User-Agent': 'Test'},
            timeout=10
        )
    
    @pytest.mark.unit
    @patch('market_data.utils.api_client.requests.get')
    def test_successful_fetch(self, mock_get, api_client):
        """Test successful data fetch"""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'chart': {
                'result': [{'meta': {...}, 'indicators': {...}}],
                'error': None
            }
        }
        mock_get.return_value = mock_response
        
        # Act
        result = api_client.fetch_market_data('AAPL', '2023-11-09')
        
        # Assert
        assert result['ticker'] == 'AAPL'
        assert result['currency'] == 'USD'
        mock_get.assert_called_once()
    
    @pytest.mark.unit
    def test_invalid_ticker(self, api_client):
        """Test invalid ticker raises error"""
        # Expect ValueError for invalid ticker
        with pytest.raises(ValueError, match="Invalid"):
            api_client.fetch_market_data('', '2023-11-09')
```

---

## 🎯 Checklist de Testing

Antes de hacer commit:

- [ ] Todos los tests pasan (`pytest`)
- [ ] Coverage > 80% (`pytest --cov`)
- [ ] No hay import errors en DAGs
- [ ] Flake8 pasa sin errores
- [ ] Black formatting aplicado
- [ ] Isort ejecutado
- [ ] Tests nuevos para nueva funcionalidad
- [ ] Documentación actualizada

---

## 🔗 Referencias

- [Pytest Documentation](https://docs.pytest.org/)
- [Airflow Testing Documentation](https://airflow.apache.org/docs/apache-airflow/stable/best-practices.html#testing-a-dag)
- [Testing Best Practices](https://docs.pytest.org/en/stable/goodpractices.html)
- [Mocking Guide](https://docs.python.org/3/library/unittest.mock.html)

---

## 📞 Soporte

Si encuentras problemas con los tests:

1. Revisa esta documentación
2. Verifica los logs de CI en GitHub Actions
3. Ejecuta tests localmente con `-v -s` para más detalles
4. Consulta los fixtures en `conftest.py`

---

**Última actualización**: Noviembre 2025
**Versión de Testing**: 1.0.0

