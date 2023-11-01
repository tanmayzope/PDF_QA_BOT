import io
import os
import requests
from io import BytesIO
from PyPDF2 import PdfReader
from airflow.models import DAG, Param
from airflow.operators.python_operator import PythonOperator
from airflow.utils.dates import days_ago
from datetime import timedelta
import tiktoken
import openai
import pandas as pd
import requests
import threading



# DAG Settings
dag = DAG(
    dag_id="sandbox",
    schedule_interval="0 0 * * *",
    start_date=days_ago(0),
    catchup=False,
    dagrun_timeout=timedelta(minutes=60),
    tags=["labs", "damg7245"],
)

# def log_pdf_link(**kwargs):
#     # Extract the passed pdf_link from the configuration
#     pdf_link = kwargs["dag_run"].conf["pdf_link"]
#     print(f"Received pdf_link: {pdf_link}")

# log_pdf_link_task = PythonOperator(
#     task_id="log_pdf_link",
#     python_callable=log_pdf_link,
#     provide_context=True,
#     dag=dag
# )

pdf_urls = {
    "FOCUS Report Part IIC Instructions": "https://www.sec.gov/files/formx-17a-5_2c-instr.pdf",
    "Sec 1661": "https://www.sec.gov/files/sec1661.pdf",
    "Sec 1662": "https://www.sec.gov/files/sec1662.pdf",
    "Sec 2866": "https://www.sec.gov/files/sec2866.pdf",
    "Exam Brochure": "https://www.sec.gov/files/exam-brochure.pdf"
}

def extract_text_from_pdf_stream(pdf_stream):
    """Extract text from a PDF stream."""
    reader = PdfReader(pdf_stream)
    text = ''
    for page in reader.pages:
        text += page.extract_text()
    return text

def download_and_extract_text(url_name, url, output_dict):
    """Download PDF from URL and extract text."""
    response = requests.get(url)
    if response.status_code == 200:
        pdf_stream = BytesIO(response.content)
        output_dict[url_name] = extract_text_from_pdf_stream(pdf_stream)
    else:
        output_dict[url_name] = "Failed to download"

def extract_texts_from_urls(pdf_urls):
    """Extract texts from multiple PDF URLs."""
    extracted_text = {}
    threads = []

    for url_name, url in pdf_urls.items():
        thread = threading.Thread(target=download_and_extract_text, args=(url_name, url, extracted_text))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    return extracted_text

def split_into_many(extracted_text, tokenizer,  max_tokens = 500): 
        
    # Split the text into sentences
        sentences = extracted_text.split('. ')
    
        # Get the number of tokens for each sentence
        n_tokens = [len(tokenizer.encode(" " + sentence)) for sentence in sentences]
    
        chunks = []
        tokens_so_far = 0
        chunk = []
    
        # Loop through the sentences and tokens joined together in a tuple
        for sentence, token in zip(sentences, n_tokens):
    
            # If the number of tokens so far plus the number of tokens in the current sentence is greater
            # than the max number of tokens, then add the chunk to the list of chunks and reset
            # the chunk and tokens so far
            if tokens_so_far + token > max_tokens:
                chunks.append(". ".join(chunk) + ".")
                chunk = []
                tokens_so_far = 0
    
            # If the number of tokens in the current sentence is greater than the max number of
            # tokens, go to the next sentence
            if token > max_tokens:
                continue
    
            # Otherwise, add the sentence to the chunk and add the number of tokens to the total
            chunk.append(sentence)
            tokens_so_far += token + 1
    
        # Add the last chunk to the list of chunks
        if chunk:
            chunks.append(". ".join(chunk) + ".")
    
        return chunks

def generate_embeddings(extracted_text, **kwargs):
    # Assuming extracted_text is from a single PDF:
    pdf_name = "Default PDF Name"  # Replace with an actual name if needed.
    data = []

    # Tokenizer
    tokenizer = tiktoken.get_encoding("cl100k_base")
    n_tokens = len(tokenizer.encode(extracted_text))
    max_tokens = 500

    if n_tokens > max_tokens:
        chunks = split_into_many(extracted_text, tokenizer)
        for chunk in chunks:
            shortened_tokens = len(tokenizer.encode(chunk))
            data.append({
                'PDF Name': pdf_name,
                'text': extracted_text,
                'n_tokens': n_tokens,
                'shortened_text': chunk,
                'shortened_tokens': shortened_tokens
            })
    else:
        data.append({
            'PDF Name': pdf_name,
            'text': extracted_text,
            'n_tokens': n_tokens,
            'shortened_text': extracted_text,
            'shortened_tokens': n_tokens
        })

    df = pd.DataFrame(data)
    openai.api_key = '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'  # Ensure you securely handle this key!

    df['shortened_embeddings'] = df['shortened_text'].apply(
        lambda x: openai.Embedding.create(input=x, engine='text-embedding-ada-002')['data'][0]['embedding']
    )

    csv_file_name = dump_to_csv(df)
    
    return csv_file_name

def dump_to_csv(df, csv_file_name=None):
    
    
    if csv_file_name is None:
        # Get the directory of the current script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Assuming the script is in the 'dags' folder, go up one level to Airflow and then into CSV
        csv_dir = os.path.join(script_dir, '..', 'CSV')
        
        # If the CSV directory doesn't exist, create it
        if not os.path.exists(csv_dir):
            os.makedirs(csv_dir)
        
        # Construct the full path to the CSV file
        csv_file_name = os.path.join(csv_dir, "extracted_embeddings.csv")
    
    try:
        # Write dataframe to CSV
        # df.to_excel("output.xlsx", index=False, engine='openpyxl')
        df.to_csv(csv_file_name, index=False)
    except Exception as e:
        raise Exception(f"Error writing dataframe to CSV: {e}")

    # Return the path of the CSV file
    return csv_file_name

def extract_data_from_pdf(**kwargs):
    return extract_texts_from_urls(pdf_urls)

# Task definitions for Airflow
task1 = PythonOperator(
    task_id='extract_data_from_pdf',
    python_callable=extract_data_from_pdf,
    dag=dag
)

task2 = PythonOperator(
    task_id='generate_embeddings',
    python_callable=generate_embeddings,
    op_args=['{{ ti.xcom_pull(task_ids="extract_data_from_pdf") }}'],
    provide_context=True,
    dag=dag
)

# Task dependencies
task1 >> task2