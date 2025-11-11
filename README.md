# Airflow 2.11 con CeleryExecutor - Docker Compose

Configuración completa de Apache Airflow 2.11 con Python 3.10 usando Docker Compose y CeleryExecutor para la ejecución distribuida de tareas.

## 📖 Descripción

Este proyecto proporciona una infraestructura lista para producción de Apache Airflow con:
- **CeleryExecutor** para ejecución paralela y escalable de tareas
- **PostgreSQL 13** como backend de metadata
- **Redis 7.2** como message broker
- Todos los componentes en contenedores Docker
- Escalabilidad horizontal de workers
- Monitoreo con Flower (opcional)

## 🏗️ Arquitectura

### Componentes Principales

| Componente | Descripción | Puerto |
|------------|-------------|--------|
| **PostgreSQL** | Base de datos para metadata de Airflow | 5432 |
| **Redis** | Message broker para Celery | 6379 |
| **Airflow Webserver** | Interfaz web de usuario | 8080 |
| **Airflow Scheduler** | Programador y orquestador de DAGs | - |
| **Airflow Worker** | Ejecutor de tareas con Celery (escalable) | - |
| **Airflow Triggerer** | Manejo de tareas asíncronas y deferibles | - |
| **Flower** (opcional) | Monitor web de Celery | 5555 |

### Flujo de Ejecución

```
DAGs → Scheduler → Redis (Queue) → Workers → Ejecución de Tareas
                       ↓
                  PostgreSQL (Metadata)
```

## 📋 Requisitos Previos

### Software Necesario
- Docker Desktop o Docker Engine (v20.10+)
- Docker Compose (v2.0+)

### Recursos Recomendados
- **RAM**: Mínimo 4GB disponible (8GB recomendado)
- **CPU**: Mínimo 2 cores (4+ recomendado)
- **Disco**: Mínimo 10GB de espacio libre
- **Sistema Operativo**: Linux, macOS, o Windows con WSL2

## 🚀 Inicio Rápido

### 1. Configurar Variables de Entorno

Copia el archivo de template y crea tu archivo `.env`:

```bash
cp env.template .env
```

Edita el archivo `.env` si necesitas cambiar las credenciales por defecto:
- Usuario: `airflow`
- Contraseña: `airflow`

### 2. Inicializar Airflow

En Linux, primero configura el AIRFLOW_UID:

```bash
echo -e "AIRFLOW_UID=$(id -u)" >> .env
```

Inicializa la base de datos y crea el usuario admin:

```bash
docker compose up airflow-init
```

### 3. Iniciar los Servicios

```bash
docker compose up -d
```

### 4. Acceder a la Interfaz Web

Abre tu navegador en: http://localhost:8080

- **Usuario**: `airflow`
- **Contraseña**: `airflow`

## 📁 Estructura del Proyecto

```
.
├── dags/               # Coloca tus DAGs aquí
├── logs/               # Logs de Airflow (generados automáticamente)
├── plugins/            # Plugins personalizados de Airflow
├── config/             # Archivos de configuración adicionales
├── docker-compose.yml  # Configuración de servicios
├── env.template        # Template de variables de entorno
├── requirements.txt    # Dependencias adicionales de Python
└── README.md          # Este archivo
```

## 🔧 Comandos Útiles

### Ver logs de un servicio

```bash
docker compose logs -f airflow-webserver
docker compose logs -f airflow-scheduler
docker compose logs -f airflow-worker
```

### Detener todos los servicios

```bash
docker compose down
```

### Detener y eliminar volúmenes (CUIDADO: borra la base de datos)

```bash
docker compose down -v
```

### Ejecutar comandos de Airflow CLI

```bash
docker compose run airflow-cli airflow dags list
docker compose run airflow-cli airflow users list
docker compose run airflow-cli airflow dags test <dag_id> <execution_date>
```

### Reiniciar un servicio específico

```bash
docker compose restart airflow-worker
docker compose restart airflow-scheduler
```

### Escalar workers (ejecutar múltiples workers)

```bash
docker compose up -d --scale airflow-worker=3
```

## 🌸 Flower - Monitor de Celery

Para habilitar Flower y monitorear tus workers de Celery:

```bash
docker compose --profile flower up -d
```

Accede a Flower en: http://localhost:5555

## 📦 Agregar Dependencias de Python

1. Edita el archivo `requirements.txt` y agrega tus paquetes
2. Opcionalmente, puedes agregar paquetes temporalmente en el archivo `.env`:

```bash
_PIP_ADDITIONAL_REQUIREMENTS=pandas==2.1.0 requests==2.31.0
```

3. Reinicia los servicios:

```bash
docker compose down
docker compose up -d
```

## 🎯 Crear tu Primer DAG

### Estructura Básica

Crea un archivo Python en la carpeta `dags/`, por ejemplo `dags/mi_primer_dag.py`:

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

# Argumentos por defecto para todas las tareas
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Definir funciones para tareas Python
def procesar_datos():
    print("Procesando datos...")
    # Tu lógica aquí
    return "Datos procesados exitosamente"

def enviar_notificacion():
    print("Enviando notificación...")
    # Tu lógica aquí
    return "Notificación enviada"

# Definir el DAG
with DAG(
    dag_id='mi_primer_dag',
    default_args=default_args,
    description='Mi primer DAG en Airflow',
    schedule_interval='@daily',  # O usa cron: '0 0 * * *'
    catchup=False,
    tags=['tutorial', 'ejemplo'],
) as dag:

    # Tarea 1: Bash
    inicio = BashOperator(
        task_id='inicio',
        bash_command='echo "Iniciando pipeline..."',
    )

    # Tarea 2: Python
    procesar = PythonOperator(
        task_id='procesar_datos',
        python_callable=procesar_datos,
    )

    # Tarea 3: Python
    notificar = PythonOperator(
        task_id='enviar_notificacion',
        python_callable=enviar_notificacion,
    )

    # Tarea 4: Bash
    fin = BashOperator(
        task_id='fin',
        bash_command='echo "Pipeline completado!"',
    )

    # Definir el orden de ejecución
    inicio >> procesar >> notificar >> fin
```

### Activación del DAG

1. El DAG aparecerá automáticamente en la interfaz web después de unos segundos
2. Por defecto, los nuevos DAGs se crean en estado **pausado**
3. Haz clic en el toggle para activarlo
4. Puedes ejecutarlo manualmente con el botón "Trigger DAG" o esperar al schedule

### Tipos de Operators Comunes

```python
# PythonOperator - Ejecutar funciones Python
from airflow.operators.python import PythonOperator

# BashOperator - Ejecutar comandos bash
from airflow.operators.bash import BashOperator

# EmailOperator - Enviar emails
from airflow.operators.email import EmailOperator

# PostgresOperator - Ejecutar queries SQL en PostgreSQL
from airflow.providers.postgres.operators.postgres import PostgresOperator

# HTTPOperator - Hacer peticiones HTTP
from airflow.providers.http.operators.http import SimpleHttpOperator
```

### Patrones de Dependencias

```python
# Secuencial
tarea1 >> tarea2 >> tarea3

# Paralelo
tarea1 >> [tarea2, tarea3, tarea4] >> tarea5

# Múltiples dependencias
[tarea1, tarea2] >> tarea3 >> [tarea4, tarea5]
```

## 🔒 Seguridad

⚠️ **Importante**: Este setup es para desarrollo. Para producción:

1. Cambia todas las contraseñas por defecto
2. Genera una Fernet Key segura:
   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```
3. Configura `AIRFLOW__WEBSERVER__SECRET_KEY` con un valor aleatorio seguro
4. Usa variables de entorno secretas o un gestor de secretos
5. Configura SSL/TLS para las conexiones
6. Revisa las mejores prácticas de seguridad de Airflow

## 🐛 Solución de Problemas

### Los servicios no inician

```bash
# Verifica los logs
docker compose logs

# Verifica el estado de los contenedores
docker compose ps
```

### El webserver no es accesible

1. Verifica que el puerto 8080 no esté en uso
2. Espera 30-60 segundos después de `docker compose up` para que el servicio esté listo
3. Revisa los logs: `docker compose logs airflow-webserver`

### Los DAGs no aparecen

1. Verifica que el archivo esté en la carpeta `dags/`
2. Revisa que no haya errores de sintaxis
3. Chequea los logs del scheduler: `docker compose logs airflow-scheduler`
4. Refresca la página web

### Problemas de permisos en Linux

```bash
# Ajusta los permisos de las carpetas
sudo chown -R $(id -u):$(id -g) dags logs plugins config
```

## ⚙️ Configuración Avanzada

### Variables de Entorno Importantes

Edita el archivo `.env` para personalizar tu instalación:

```bash
# Versión de Airflow
AIRFLOW_IMAGE_NAME=apache/airflow:2.11.0-python3.10

# Usuario del sistema (importante en Linux)
AIRFLOW_UID=50000

# Credenciales del admin
_AIRFLOW_WWW_USER_USERNAME=airflow
_AIRFLOW_WWW_USER_PASSWORD=airflow

# Paquetes adicionales de Python
_PIP_ADDITIONAL_REQUIREMENTS=pandas==2.1.0 boto3==1.28.0
```

### Escalabilidad de Workers

El CeleryExecutor permite escalar horizontalmente los workers:

```bash
# Escalar a 5 workers
docker compose up -d --scale airflow-worker=5

# Verificar workers activos
docker compose exec airflow-worker celery -A airflow.providers.celery.executors.celery_executor.app inspect active
```

### Configuración de Conexiones

Las conexiones se pueden configurar desde:
1. **Interfaz Web**: Admin → Connections
2. **Variables de Entorno**: En el archivo `.env`
3. **Airflow CLI**: Usando comandos de conexión

Ejemplo de conexión PostgreSQL:
```bash
docker compose exec airflow-scheduler airflow connections add 'my_postgres' \
    --conn-type 'postgres' \
    --conn-host 'postgres-server' \
    --conn-schema 'my_database' \
    --conn-login 'user' \
    --conn-password 'password' \
    --conn-port 5432
```

### Variables Personalizadas

Crear variables globales accesibles desde los DAGs:

```bash
# Desde CLI
docker compose exec airflow-scheduler airflow variables set my_variable "valor"

# Desde Python en tu DAG
from airflow.models import Variable
mi_valor = Variable.get("my_variable")
```

## 💡 Mejores Prácticas

### 1. Estructura de DAGs

```python
# ✅ BUENO: Usar context manager
with DAG('mi_dag', ...) as dag:
    tarea1 = PythonOperator(...)

# ❌ MALO: Crear DAG sin context manager
dag = DAG('mi_dag', ...)
tarea1 = PythonOperator(dag=dag, ...)
```

### 2. Manejo de Errores

```python
def mi_tarea(**context):
    try:
        # Tu código aquí
        result = procesar_datos()
        return result
    except Exception as e:
        # Log del error
        print(f"Error: {str(e)}")
        # Re-lanzar excepción para que Airflow lo marque como fallido
        raise
```

### 3. Uso de XCom

```python
# Tarea que produce datos
def producir_datos(**context):
    datos = {"resultado": 123}
    # Push a XCom
    context['task_instance'].xcom_push(key='mi_dato', value=datos)
    return datos

# Tarea que consume datos
def consumir_datos(**context):
    # Pull desde XCom
    datos = context['task_instance'].xcom_pull(
        task_ids='producir_datos',
        key='mi_dato'
    )
    print(f"Datos recibidos: {datos}")
```

### 4. Idempotencia

Asegúrate de que tus tareas sean idempotentes (mismo resultado al ejecutarse múltiples veces):

```python
# ✅ BUENO: Idempotente
def cargar_datos():
    # Eliminar datos existentes primero
    delete_existing_data()
    # Luego insertar
    insert_new_data()

# ❌ MALO: No idempotente
def cargar_datos():
    # Siempre inserta, creando duplicados
    insert_new_data()
```

### 5. Testing de DAGs

Verifica tu DAG antes de desplegarlo:

```bash
# Test de sintaxis
docker compose exec airflow-scheduler python /opt/airflow/dags/mi_dag.py

# Test de DAG completo
docker compose exec airflow-scheduler airflow dags test mi_dag 2025-11-11

# Test de tarea específica
docker compose exec airflow-scheduler airflow tasks test mi_dag tarea1 2025-11-11
```

## 📊 Monitoreo y Observabilidad

### Métricas con Flower

Flower proporciona una interfaz web para monitorear workers de Celery:

```bash
# Activar Flower
docker compose --profile flower up -d

# Acceder a http://localhost:5555
```

En Flower puedes ver:
- Workers activos
- Tareas en ejecución
- Historial de tareas
- Estadísticas de rendimiento
- Pool de workers

### Logs de Airflow

Los logs están disponibles en:
- **Interfaz Web**: Haz clic en cualquier tarea → View Log
- **Sistema de archivos**: Carpeta `logs/` (persistente)
- **Docker logs**: `docker compose logs -f [servicio]`

### Health Checks

Verifica el estado de los servicios:

```bash
# Health check general
curl http://localhost:8080/health | python -m json.tool

# Estado de workers
docker compose exec airflow-worker celery -A airflow.providers.celery.executors.celery_executor.app inspect stats
```

## 🔄 Backup y Recuperación

### Backup de la Base de Datos

```bash
# Crear backup
docker compose exec postgres pg_dump -U airflow airflow > backup_$(date +%Y%m%d_%H%M%S).sql

# Restaurar backup
docker compose exec -T postgres psql -U airflow airflow < backup_20251111_120000.sql
```

### Backup de DAGs

Los DAGs deben estar en un sistema de control de versiones (Git):

```bash
# Asegúrate de que tus DAGs estén en Git
git add dags/
git commit -m "Actualizar DAGs"
git push
```

## 🚨 Troubleshooting Avanzado

### Worker no procesa tareas

```bash
# 1. Verificar que el worker esté online
docker compose exec airflow-worker celery -A airflow.providers.celery.executors.celery_executor.app inspect active

# 2. Verificar conexión con Redis
docker compose exec redis redis-cli ping

# 3. Reiniciar worker
docker compose restart airflow-worker
```

### DAG no se actualiza

```bash
# 1. Verificar errores de sintaxis
docker compose exec airflow-scheduler python /opt/airflow/dags/tu_dag.py

# 2. Forzar refresco del scheduler
docker compose restart airflow-scheduler

# 3. Verificar logs del scheduler
docker compose logs -f airflow-scheduler | grep "tu_dag"
```

### Problemas de memoria

```bash
# Ver uso de recursos
docker stats

# Aumentar límites en docker-compose.yml
services:
  airflow-worker:
    deploy:
      resources:
        limits:
          memory: 4G
```

## 📚 Recursos y Referencias

### Documentación Oficial
- [Apache Airflow Documentation](https://airflow.apache.org/docs/apache-airflow/stable/)
- [Airflow con Docker Compose](https://airflow.apache.org/docs/apache-airflow/stable/howto/docker-compose/index.html)
- [CeleryExecutor Guide](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/executor/celery.html)
- [Best Practices](https://airflow.apache.org/docs/apache-airflow/stable/best-practices.html)

### Operadores Útiles
- [Core Operators](https://airflow.apache.org/docs/apache-airflow/stable/_api/airflow/operators/index.html)
- [Postgres Provider](https://airflow.apache.org/docs/apache-airflow-providers-postgres/stable/)
- [AWS Provider](https://airflow.apache.org/docs/apache-airflow-providers-amazon/stable/)
- [HTTP Provider](https://airflow.apache.org/docs/apache-airflow-providers-http/stable/)

### Tutoriales
- [Writing a DAG](https://airflow.apache.org/docs/apache-airflow/stable/tutorial/fundamentals.html)
- [Working with Tasks](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/tasks.html)
- [Using the CLI](https://airflow.apache.org/docs/apache-airflow/stable/cli-and-env-variables-ref.html)

## 📝 Notas y Consideraciones

### Configuración Actual
- ✅ DAGs de ejemplo **desactivados** (`AIRFLOW__CORE__LOAD_EXAMPLES: 'false'`)
- ✅ Nuevos DAGs se crean en estado **pausado** por defecto
- ✅ Logs persistentes en carpeta `logs/`
- ✅ Base de datos PostgreSQL con volumen persistente
- ✅ CeleryExecutor configurado y listo para escalar

### Limitaciones en Desarrollo
- Credenciales por defecto (cambiar para producción)
- Sin SSL/TLS configurado
- Sin backup automático
- Sin monitoreo de alertas

### Próximos Pasos Sugeridos
1. Configurar alertas por email o Slack
2. Implementar CI/CD para deployment de DAGs
3. Configurar backup automático de la base de datos
4. Añadir autenticación OAuth/LDAP
5. Implementar secrets management (HashiCorp Vault, AWS Secrets Manager)

---

## 🤝 Contribución

Para contribuir al proyecto:
1. Crea una rama para tu feature
2. Testea tus cambios localmente
3. Crea un Pull Request con descripción detallada

## 📄 Licencia

Este proyecto utiliza Apache Airflow que está licenciado bajo Apache License 2.0.

---

**¡Feliz orquestación de datos! 🚀**

Para preguntas o soporte, consulta la documentación oficial de Apache Airflow.

