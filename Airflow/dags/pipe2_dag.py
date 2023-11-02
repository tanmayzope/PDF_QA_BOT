from airflow import DAG
from airflow.operators.python_operator import PythonOperator
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

pinecone.init(api_key=PINECONE_API_KEY, environment=PINECONE_ENV)

# Function to check and read CSV and return data
def read_csv():
    df = pd.read_csv('/opt/airflow/CSV/Embeddings_Pypdf_openAI.csv')
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
    
    # Assuming the correct way to instantiate an Index is without keyword argument 'name'
    index = pinecone.Index(index_name)
    df['vector_id'] = range(1, len(df) + 1)
    # Function to batch DataFrame
    df['shortened_embeddings'] = df.shortened_embeddings.apply(literal_eval)
    # Set vector_id to be a string
    df['vector_id'] = df.vector_id.apply(str)
    
    def df_batcher(df, batch_size):
        """Yield successive n-sized chunks from df."""
        for i in range(0, len(df), batch_size):
            yield df.iloc[i:i + batch_size]

        # Read vectors from strings back into a list
    

    # Upsert in batches
    batch_size = 100
    for batch_df in df_batcher(df, batch_size):
    # Ensure that 'vector_id' and 'shortened_embeddings' are in batch_df
        if 'vector_id' not in batch_df or 'shortened_embeddings' not in batch_df:
            raise ValueError("The batch DataFrame does not contain the required columns.")

        # Zipping the 'vector_id' and 'shortened_embeddings' columns from the batch
        vectors = zip(batch_df['vector_id'], batch_df['shortened_embeddings'])

        # Upsert the batch of vectors to the index
        index.upsert(vectors)

    print("Upsert operation completed successfully.")

def verify_records(index_name):
    index = pinecone.Index(name=index_name)
    stats = index.describe_index_stats()
    num_vectors = stats["vector_count"]
    df = pd.read_csv('/opt/airflow/CSV/extracted_embeddings.csv')
    num_records = len(df)
    assert num_vectors == num_records, f"Expected {num_records} vectors, but found {num_vectors} in Pinecone."
    print(f"Successfully verified {num_vectors} records in Pinecone.")

# DAG definition
dag = DAG(
    'vector_db_pipeline',
    default_args={
        'owner': 'you',
        'start_date': datetime(2023, 11, 1),
    },
    description='Pipeline to populate vector DB and verify insertion',
    schedule_interval=None,
    catchup=False,
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
