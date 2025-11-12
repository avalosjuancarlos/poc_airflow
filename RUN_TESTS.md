# 🧪 Cómo Ejecutar los Tests

Guía rápida para ejecutar la suite de tests del proyecto.

## 🚀 Quick Start

```bash
# 1. Configurar Python path
export PYTHONPATH="${PWD}/dags:${PYTHONPATH}"

# 2. Instalar dependencias de testing
pip install -r requirements.txt

# 3. Ejecutar todos los tests
pytest

# 4. Con coverage
pytest --cov=dags/market_data --cov-report=html
```

## 📊 Ejecutar Tests Específicos

### Todos los Tests
```bash
pytest -v
```

### Solo Tests Unitarios
```bash
pytest tests/unit -v
```

### Solo Tests de Integración
```bash
pytest tests/integration -v
```

### Test Específico
```bash
# Por archivo
pytest tests/unit/test_validators.py -v

# Por clase
pytest tests/unit/test_validators.py::TestValidateTickerFormat -v

# Por función
pytest tests/unit/test_validators.py::TestValidateTickerFormat::test_valid_ticker_uppercase -v
```

## 📈 Coverage Report

```bash
# Con reporte en terminal
pytest --cov=dags/market_data --cov-report=term-missing

# Con reporte HTML
pytest --cov=dags/market_data --cov-report=html

# Ver reporte
open htmlcov/index.html
```

## 🐳 Ejecutar en Docker

```bash
# Opción 1: En contenedor existente
docker compose exec airflow-scheduler bash
cd /opt/airflow
export PYTHONPATH="/opt/airflow/dags:${PYTHONPATH}"
pytest

# Opción 2: Contenedor dedicado (crear docker-compose.test.yml)
docker compose -f docker-compose.test.yml up test
```

## 🔧 Opciones Útiles

```bash
# Verbose + mostrar prints
pytest -v -s

# Detener en primer fallo
pytest -x

# Ejecutar solo tests que fallaron
pytest --lf

# Ver duración de tests
pytest --durations=10

# Con debugger
pytest --pdb
```

## ✅ Verificar Todo Funciona

```bash
# Ejecutar todo
pytest -v --cov=dags/market_data --cov-report=term-missing

# Debe mostrar:
# - 35+ tests passed
# - Coverage > 80%
# - No errors
```

## 📚 Más Información

Ver `docs/TESTING_GUIDE.md` para documentación completa.

---

**¿Problemas?** Ver sección Troubleshooting en `docs/TESTING_GUIDE.md`

