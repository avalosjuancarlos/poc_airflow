"""
Ejemplo de DAG para probar CeleryExecutor
Este DAG crea múltiples tareas que se ejecutarán en paralelo usando Celery Workers
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta
import time
import random

def task_sleep(task_number):
    """Simula una tarea que toma tiempo en ejecutarse"""
    sleep_time = random.randint(5, 15)
    print(f"Task {task_number} iniciando...")
    print(f"Durmiendo por {sleep_time} segundos...")
    time.sleep(sleep_time)
    print(f"Task {task_number} completada!")
    return f"Task {task_number} finished after {sleep_time} seconds"

def print_execution_info(**context):
    """Imprime información sobre la ejecución"""
    print("=" * 50)
    print("INFORMACIÓN DE EJECUCIÓN")
    print("=" * 50)
    print(f"DAG ID: {context['dag'].dag_id}")
    print(f"Task ID: {context['task'].task_id}")
    print(f"Execution Date: {context['execution_date']}")
    print(f"Try Number: {context['task_instance'].try_number}")
    print("=" * 50)
    return "Info printed successfully"

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
}

with DAG(
    'example_celery_dag',
    default_args=default_args,
    description='DAG de ejemplo para probar CeleryExecutor con tareas paralelas',
    schedule_interval=None,  # Ejecución manual
    catchup=False,
    tags=['example', 'celery', 'parallel'],
) as dag:

    # Tarea inicial
    start = BashOperator(
        task_id='start',
        bash_command='echo "Iniciando DAG con CeleryExecutor..."',
    )

    # Tarea de información
    info_task = PythonOperator(
        task_id='print_info',
        python_callable=print_execution_info,
        provide_context=True,
    )

    # Crear múltiples tareas que se ejecutarán en paralelo
    parallel_tasks = []
    for i in range(1, 6):  # 5 tareas paralelas
        task = PythonOperator(
            task_id=f'parallel_task_{i}',
            python_callable=task_sleep,
            op_args=[i],
        )
        parallel_tasks.append(task)

    # Tarea final
    end = BashOperator(
        task_id='end',
        bash_command='echo "DAG completado exitosamente!"',
    )

    # Definir el flujo de tareas
    # start -> info_task -> [parallel_tasks] -> end
    start >> info_task >> parallel_tasks >> end

