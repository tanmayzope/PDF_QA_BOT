from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from datetime import timedelta
from airflow.utils.dates import days_ago
from datetime import datetime
import pandas as pd
import pinecone
import os
import warnings
from ast import literal_eval

warnings.filterwarnings(action="ignore", message="unclosed", category=ResourceWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Constants and Configuration
PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")
PINECONE_ENV = os.environ.get("PINECONE_ENV")

pinecone.init(api_key="5dc855d8-76cf-48f3-a00e-289d82603ea7", environment="gcp-starter")

# Function to check and read CSV and return data
def read_csv():
    df = pd.read_csv('/opt/airflow/CSV/extracted_embeddings.csv')
    # Pushes to XCom by returning data
    return df.to_json(date_format='iso', orient='split')

def create_index():
    index_name = 'openai'

    if index_name in pinecone.list_indexes():
            pinecone.delete_index(index_name)
    pinecone.create_index(name=index_name, dimension=1536)
    print("Index created successfully!")
    # Return index name for further tasks if needed
    return index_name

def upsert_vectors(index_name, **kwargs):
    ti = kwargs['ti']
    df_json = ti.xcom_pull(task_ids='read_csv')
    df = pd.read_json(df_json, orient='split')
    
    index = pinecone.Index(index_name)
    
    # Function to convert embeddings from string to list
    df['shortened_embeddings'] = df['shortened_embeddings'].apply(literal_eval)

    # Function to batch DataFrame
    def df_batcher(df, batch_size):
        """Yield successive n-sized chunks from df."""
        for i in range(0, len(df), batch_size):
            yield df.iloc[i:i + batch_size]

    # Upsert in batches
    batch_size = 100
    for batch_df in df_batcher(df, batch_size):
        # Assign vector_id if it doesn't exist in df
        if 'vector_id' not in df.columns:
            batch_df['vector_id'] = [str(i) for i in range(1, len(batch_df) + 1)]

        # Prepare the vectors and metadata for upserting
        vectors_and_metadata = [
            (row['vector_id'], row['shortened_embeddings'], {"PDF_Name": row['PDF_Name'], "text": row['shortened_text']})
            for _, row in batch_df.iterrows()
        ]
        
        
        # vectors_and_metadata = [
        #     (row['vector_id'], row['shortened_embeddings'], {"other_info": row['PDF Name'], "text": row['text']})
        #     for _, row in batch_df.iterrows()
        # ]

        # Upsert the batch of vectors with metadata to the index
        index.upsert(vectors=vectors_and_metadata)

    print("Upsert operation completed successfully.")


def verify_records(index_name):
    index = pinecone.Index(name=index_name)
    stats = index.describe_index_stats()
    num_vectors = stats["vector_count"]
    df = pd.read_csv('/opt/airflow/CSV/extracted_embeddings.csv')
    num_records = len(df)
    assert num_vectors == num_records, f"Expected {num_records} vectors, but found {num_vectors} in Pinecone."
    print(f"Successfully verified {num_vectors} records in Pinecone.")

# # DAG definition
# dag = DAG(
#     'vector_db_pipeline',
#     default_args={
#         'owner': 'you',
#         'start_date': datetime(2023, 11, 1),
#     },
#     description='Pipeline to populate vector DB and verify insertion',
#     schedule_interval=None,
#     catchup=False,
# )

dag = DAG(
    "vector_db_pipeline",
    default_args={
        'owner': 'you',
        # 'start_date' is now set using days_ago to set it to the current date when the DAG is parsed
    },
    description='Pipeline to populate vector DB and verify insertion',
    # This schedule_interval is set to run the DAG once every day at midnight
    schedule_interval="0 0 * * *",
    start_date=days_ago(0),
    catchup=False,  # This ensures that the DAG doesn't run for dates before the current date
    dagrun_timeout=timedelta(minutes=60),  # Sets a timeout for each DAG run
    tags=["labs", "damg7245"],  # Tags for better organization and filtering in the Airflow UI
)


# Task definitions
read_csv_task = PythonOperator(
    task_id='read_csv',
    python_callable=read_csv,
    dag=dag
)

create_index_task = PythonOperator(
    task_id='create_index',
    python_callable=create_index,
    provide_context=True,
    dag=dag
)

upsert_vectors_task = PythonOperator(
    task_id='upsert_vectors',
    python_callable=upsert_vectors,
    provide_context=True,
    op_kwargs={'index_name': '{{ task_instance.xcom_pull(task_ids="create_index") }}'},
    dag=dag
)

# verify_records_task = PythonOperator(
#     task_id='verify_records',
#     python_callable=verify_records,
#     provide_context=True,
#     op_kwargs={'index_name': '{{ task_instance.xcom_pull(task_ids="create_index") }}'},
#     dag=dag
# )

# Setting task dependencies
read_csv_task >> create_index_task >> upsert_vectors_task 
#>> verify_records_task
