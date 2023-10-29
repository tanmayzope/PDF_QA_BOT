import os
import requests
from io import BytesIO
import PyPDF2
import csv
from airflow.models import DAG, Param
from airflow.operators.python_operator import PythonOperator
from airflow.utils.dates import days_ago
from datetime import timedelta

# Define DAG parameters and settings
dag = DAG(
    dag_id="sandbox",
    schedule_interval="0 0 * * *",
    start_date=days_ago(0),
    catchup=False,
    dagrun_timeout=timedelta(minutes=60),
    tags=["labs", "damg7245"],
    params={
        "datasource_url": Param(default="https://sample.pdf", type='string', minLength=5, maxLength=255),
    },
)

# Define the tasks and their logic
def print_keys(**kwargs):
    print(f"Data source URL: {kwargs['params']['datasource_url']}")

def extract_data_from_pdf(pdf_link, **kwargs):
    try:
        response = requests.get(pdf_link)
        response.raise_for_status()
        with BytesIO(response.content) as pdf_file:
            pdf_reader = PyPDF2.PdfFileReader(pdf_file)
            text = "".join([pdf_reader.getPage(page_num).extractText() for page_num in range(pdf_reader.numPages)])
        return text
    except Exception as e:
        raise Exception(f"Error extracting data from PDF: {e}")

def validate_data(text_content, **kwargs):
    if len(text_content) < 10:
        raise Exception(f"Data validation failed. Content too short: {text_content}")

def generate_embeddings(**kwargs):
    # Placeholder logic for generating embeddings
    pass

def dump_to_csv(text_content, csv_file_name="output.csv"):
    try:
        # Check if the file already exists
        file_exists = os.path.isfile(csv_file_name)

        with open(csv_file_name, mode='a', newline='') as file:
            writer = csv.writer(file)

            # If the file didn't exist, write the header
            if not file_exists:
                writer.writerow(["id", "content"])

            # For the ID, count the existing rows (excluding header) and add one
            current_id = sum(1 for row in open(csv_file_name)) if file_exists else 0
            writer.writerow([current_id, text_content])

    except Exception as e:
        raise Exception(f"Error writing to CSV: {e}")

# Create tasks using PythonOperator
task1 = PythonOperator(
    task_id='extract_data_from_pdf',
    python_callable=extract_data_from_pdf,
    op_args=['{{ dag_run.conf["pdf_link"] if dag_run and dag_run.conf and "pdf_link" in dag_run.conf else params.datasource_url }}'],
    provide_context=True,
    dag=dag
)

task_validate = PythonOperator(
    task_id='validate_data',
    python_callable=validate_data,
    op_args=['{{ ti.xcom_pull(task_ids="extract_data_from_pdf") }}'],
    provide_context=True,
    dag=dag
)

task2 = PythonOperator(
    task_id='generate_embeddings',
    python_callable=generate_embeddings,
    provide_context=True,
    dag=dag
)

task3 = PythonOperator(
    task_id='dump_to_csv',
    python_callable=dump_to_csv,
    op_args=['{{ ti.xcom_pull(task_ids="extract_data_from_pdf") }}'],
    provide_context=True,
    dag=dag
)

# Set task dependencies
task1 >> task_validate >> task2 >> task3
