# 🧪 Tests - Market Data DAG

Comprehensive test suite for the Market Data DAG.

## 🚀 Quick Start

```bash
# Run all tests using Docker Compose (recommended)
docker compose -f docker-compose.test.yml run --rm test

# Or using Make
make test

# With coverage report
docker compose -f docker-compose.test.yml run --rm test-coverage
```

## 📁 Structure

```
tests/
├── unit/                    # Unit tests (fast, isolated)
│   ├── test_validators.py  # 30+ validator tests
│   ├── test_config.py       # 10+ configuration tests
│   ├── test_api_client.py   # 20+ API client tests
│   ├── test_warehouse_loader.py  # 20+ warehouse loader tests
│   ├── test_warehouse_config.py  # 15+ warehouse config tests
│   └── ...                  # Additional unit tests
├── integration/             # Integration tests
│   └── test_dag_execution.py   # 10 DAG execution tests
└── conftest.py             # Shared fixtures

Total: 197 tests (187 unit + 10 integration)
Coverage: 91.84%
```

## 📊 Ejecutar Tests

### Por Tipo

```bash
# Solo unitarios
pytest tests/unit -v

# Solo integración
pytest tests/integration -v

# Con marker
pytest -m "unit" -v
pytest -m "integration" -v
```

### Por Archivo

```bash
pytest tests/unit/test_validators.py -v
pytest tests/unit/test_api_client.py -v
```

### Con Coverage

```bash
pytest --cov=dags/market_data --cov-report=term-missing
```

## ✅ Current Coverage

- **Validators**: 100% coverage
- **Config**: 100% coverage (warehouse_config)
- **API Client**: 85% coverage
- **Warehouse Loader**: 98% coverage
- **Warehouse Config**: 100% coverage
- **Total**: 91.84% coverage

## 🤖 CI/CD

Los tests se ejecutan automáticamente en:
- Cada push a branches `main`, `develop`, `test-*`
- Cada Pull Request

Ver: `.github/workflows/ci.yml`

## 📚 Documentación

Ver documentación completa en: `docs/TESTING_GUIDE.md`

## 🎯 Tests Importantes

### Validadores
- ✅ Ticker válido uppercase/lowercase
- ✅ Ticker con caracteres especiales (., -, ^)
- ✅ Validación de fecha YYYY-MM-DD
- ✅ Manejo de errores

### API Client
- ✅ Fetch exitoso
- ✅ Manejo de reintentos
- ✅ Rate limiting (429)
- ✅ Errores de servidor (5xx)
- ✅ Timeouts

### DAG
- ✅ DAG carga sin errores
- ✅ Estructura correcta
- ✅ Dependencias entre tareas
- ✅ Configuración válida

## 🐛 Troubleshooting

```bash
# Import errors - pytest.ini handles pythonpath automatically
# No need to set PYTHONPATH manually

# View available tests
pytest --collect-only

# Debug with output
pytest -v -s
```

## 📊 Test Statistics

- **Unit Tests**: 187 tests covering all modules
- **Integration Tests**: 10 tests for DAG execution
- **Total Coverage**: 91.84%
- **Key Modules**:
  - `validators.py`: 100% coverage
  - `warehouse_config.py`: 100% coverage
  - `warehouse_loader.py`: 98% coverage
  - `api_client.py`: 85% coverage

---

For more details, see `docs/developer-guide/testing.md`

