# Airflow 2.11 con CeleryExecutor - Docker Compose

Este proyecto configura Apache Airflow 2.11 con Python 3.10 usando Docker Compose y CeleryExecutor para la ejecución distribuida de tareas.

## 🏗️ Arquitectura

El proyecto utiliza los siguientes servicios:

- **PostgreSQL**: Base de datos para metadata de Airflow
- **Redis**: Message broker para Celery
- **Airflow Webserver**: Interfaz web (puerto 8080)
- **Airflow Scheduler**: Programador de tareas
- **Airflow Worker**: Ejecutor de tareas con Celery
- **Airflow Triggerer**: Manejo de tareas asíncronas
- **Flower** (opcional): Monitor de Celery (puerto 5555)

## 📋 Requisitos Previos

- Docker Desktop o Docker Engine (v20.10+)
- Docker Compose (v2.0+)
- Al menos 4GB de RAM disponible
- Al menos 10GB de espacio en disco

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

Crea un archivo Python en la carpeta `dags/`, por ejemplo `dags/hello_world.py`:

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

def print_hello():
    print("Hello from Airflow!")
    return "Hello World!"

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'hello_world',
    default_args=default_args,
    description='A simple hello world DAG',
    schedule_interval=timedelta(days=1),
    catchup=False,
    tags=['example'],
) as dag:

    hello_task = PythonOperator(
        task_id='print_hello',
        python_callable=print_hello,
    )
```

El DAG aparecerá automáticamente en la interfaz web después de unos segundos.

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

## 📚 Recursos

- [Documentación oficial de Airflow](https://airflow.apache.org/docs/apache-airflow/stable/)
- [Airflow con Docker Compose](https://airflow.apache.org/docs/apache-airflow/stable/howto/docker-compose/index.html)
- [CeleryExecutor](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/executor/celery.html)
- [Best Practices](https://airflow.apache.org/docs/apache-airflow/stable/best-practices.html)

## 📝 Notas

- Los DAGs de ejemplo están **desactivados** por defecto (`AIRFLOW__CORE__LOAD_EXAMPLES: 'false'`)
- Los DAGs nuevos se crean en estado **pausado** por defecto
- Los logs se persisten en la carpeta `logs/`
- La base de datos PostgreSQL se persiste en un volumen Docker

---

**¡Feliz orquestación de datos! 🚀**

