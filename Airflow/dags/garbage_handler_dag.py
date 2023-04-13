import os
import logging
import datetime as dt

import requests
from requests.exceptions import HTTPError
from airflow.models import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator
from airflow.exceptions import AirflowException

from creds import *


args = {
    'owner': 'admin',
    'start_date': dt.datetime(2023, 4, 13, 10, 0, 0, 0),
    'retries': 2,
    'retry_delay': dt.timedelta(minutes=3),
    'depends_on_past': False,
}

logging.basicConfig(
    format='[%(levelname)s] %(name)s: %(message)s - %(asctime)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logging.getLogger(name='lambda').setLevel(logging.INFO)


def delete_dag(dag_name: str, dag_file_path: str) -> bool:
    """Delete dag"""

    # send delete request to Airflow API
    url = f'http://{AIRFLOW_API_URL}/api/v1/dags/{dag_name}'
    response = requests.delete(url,
                               auth=AIRFLOW_API_AUTH,
                               headers=AIRFLOW_API_HEADERS)

    # check response for successful deletion
    if response.status_code != 204:
        logging.info(f'Could not delete DAG {dag_name}: {response.text}')
        return False

    # delete file by its path
    if not os.path.exists(dag_file_path):
        logging.info(f'Could not find DAG {dag_name}: {dag_file_path}')
        return False
    else:
        os.remove(dag_file_path)
        logging.info(f'DAG {dag_name} deleted successfully')
        return True


def delete_garbage_dags(dags_to_delete: tuple[tuple[str, str]], dags_folder_path: str) -> None:
    """Delete dags cloned from the original dags by users"""

    for dag_name, dag_file_path in dags_to_delete:
        # check that dag finished execution

        # delete dag
        delete_dag(dag_name, os.path.join(dags_folder_path, dag_file_path))


with DAG(dag_id='garbage_handler_dag',
         default_args=args,
         schedule_interval='@hourly',
         catchup=False) as dag:
    t1 = EmptyOperator(
        task_id='start_task'
    )
    t2 = PythonOperator(
        task_id=f'delete_garbage_dags',
        python_callable=on_api_trigger,
        op_kwargs={
            'dags_to_delete': DAGS_TO_DELETE,
            'dags_folder': DAGS_FOLDER
        }
    )
    t3 = EmptyOperator(
        task_id='end_task'
    )

    t1 >> t2 >> t3
