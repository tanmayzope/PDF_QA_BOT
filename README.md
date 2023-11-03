# Assignment_03

## Links

##### Link to Codelabs: https://codelabs-preview.appspot.com/?file_id=1pfzEO4BiOmfMNl1dTbG8PM2S5FmOmJgInkq3Z08EELA#0

##### Link to Embeddings Generation Notebook: [Colab Notebook 1](https://colab.research.google.com/drive/1xm_wly8FaR08YHIZxt_a7QVNytad0_U1?usp=sharing)

##### Link to Pinecone Vector Database Connection Notebook: [Colab Notebook 2](https://colab.research.google.com/drive/1VSvT8B2XzmdYhKsVpLrBavRlg6MMrRlo?usp=sharing) 
-----------------

## Setup Instructions

Follow the steps below to get the project up and running:

#### 1. Clone the Repository
Clone this GitHub repository to your local machine.

#### 2. Navigate to the File
Open `Assignment_03 in any IDE Platform. Since this code has been dockerized it will run on all IDE platforms, just make sure to install Docker Desktop

#### 3. Open the Integrated Terminal
Within your IDE, access the integrated terminal.
* Open the integrated terminal for the folder and run the command > “docker compose up --build”
-----------------

## Project Flow Architecture
-----------------

## About Code:
-----------------
#### There are three major folders, one is the Streamlit, second is the FastAPI and third is Airflow .

## Structure:
-----------------
```
.
├── Airflow
│   ├── CSV
│   ├── Pipfile
│   ├── Pipfile.lock
│   ├── dags
│   ├── logs
│   └── plugins
├── FastAPI
│   ├── Dockerfile
│   ├── Pipfile
│   ├── Pipfile.lock
│   ├── __pycache__
│   ├── main.py
│   └── test.db
├── LICENSE
├── README.md
├── Streamlit
│   ├── Dockerfile
│   ├── Pipfile
│   ├── Pipfile.lock
│   └── app.py
├── docker-compose.yaml
└── solution_architecture.png

```

## Additional Notes:
---------------

Link to the presentation video - 

WE ATTEST THAT WE HAVEN’T USED ANY OTHER STUDENTS’ WORK IN OUR ASSIGNMENT AND ABIDE BY THE POLICIES LISTED IN THE STUDENT HANDBOOK.

| Name            | Percentage | Responsibilities                                 |
|-----------------|------------|-------------------------------------------------|
| Soham Deshpande | 33%        | Airflow Pipelines, Integration, Docker Set-up, FastAPI |
| Tanmay Zope     | 33%        | Embeddings Generation, Data Processings on Pinecone, JWT Auth, Tech Doc |
| Anvi Jain       | 33%        | Research of Pinecone & Airflow, Tech Doc |




