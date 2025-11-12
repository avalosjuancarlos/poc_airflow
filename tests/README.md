# 🧪 Tests - Market Data DAG

Suite completa de tests para el Market Data DAG.

## 🚀 Quick Start

```bash
# Ejecutar todos los tests
export PYTHONPATH="${PWD}/dags:${PYTHONPATH}"
pytest

# Con coverage
pytest --cov=dags/market_data --cov-report=html
```

## 📁 Estructura

```
tests/
├── unit/                    # Tests unitarios (rápidos, aislados)
│   ├── test_validators.py  # 15+ tests de validadores
│   ├── test_config.py       # 10+ tests de configuración
│   └── test_api_client.py   # 10+ tests de API client
├── integration/             # Tests de integración
│   ├── test_dag_validation.py  # Validación del DAG
│   └── test_dag_execution.py   # Ejecución del DAG
└── conftest.py             # Fixtures compartidas

Total: 35+ tests
Coverage: 80%+ target
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

## ✅ Cobertura Actual

- **Validators**: ~95% coverage
- **Config**: ~90% coverage
- **API Client**: ~90% coverage
- **Total**: 80%+ target

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
# Import errors
export PYTHONPATH="${PWD}/dags:${PYTHONPATH}"

# Ver tests disponibles
pytest --collect-only

# Debug con output
pytest -v -s
```

---

Para más detalles, ver `docs/TESTING_GUIDE.md`

