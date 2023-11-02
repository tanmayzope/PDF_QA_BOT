from requests.auth import HTTPBasicAuth
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from typing import Optional, List, Dict
from fastapi.middleware.cors import CORSMiddleware
import logging
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
import os
import PyPDF2
from PyPDF2 import PdfReader
import time
import requests
import io
from io import BytesIO

app = FastAPI()

origins = [
    # "http://localhost:8501",
    # "http://localhost",
    # "http://127.0.0.1",
    "http://streamlit:8501"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#AIRFLOW_API_ENDPOINT = "http://127.0.0.1:8080/api/v1/dags/sandbox/dagRuns"

AIRFLOW_API_ENDPOINT = os.getenv("AIRFLOW_API_ENDPOINT", "http://localhost:8080/api/v1/dags/sandbox/dagRuns")

DATABASE_URL = "sqlite:///./test.db"
Base = declarative_base()
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, index=True, unique=True)
    hashed_password = Column(String)

Base.metadata.create_all(bind=engine)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None


# class UserInDB(User):
#     hashed_password: str

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def get_user(db, username: str):
    return db.query(User).filter(User.username == username).first()

def create_user(db, username: str, password: str):
    hashed_password = get_password_hash(password)
    db_user = User(username=username, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    db = SessionLocal()
    user = get_user(db, form_data.username)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username")
    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect password")
    return {"access_token": user.username, "token_type": "bearer"}

@app.post("/register")
async def register(username: str, password: str):
    with SessionLocal() as db:
        # Check if the user already exists
        user = get_user(db, username)
        if user:
            raise HTTPException(status_code=400, detail="Username already exists")
        
        # Try to create the user
        # try:
        #     user = create_user(db, username, password)
        #     if not user:
        #         raise HTTPException(status_code=500, detail="Failed to create user for unknown reasons.")
        # except IntegrityError:
        #     db.rollback()  # Rollback the session to a clean state in case of integrity errors
        #     raise HTTPException(status_code=400, detail="Username already exists (from integrity check).")
        # except Exception as e:
        #     db.rollback()  # Rollback the session in case of other errors
        #     raise HTTPException(status_code=500, detail=f"An error occurred: {e}")
    
    return {"status": "success"}

# def update_yaml_with_pdf_link(pdf_link):
#     """
#     Update the config.yaml file with the new pdf_link.
#     """
#     # Load the current configuration
#     with open("Airflow/config/config.yaml", 'r') as stream:
#         config = yaml.safe_load(stream)

#     # Update the datasource_url in the configuration
#     config["datasource_url"] = pdf_link

#     # Write the updated configuration back to the file
#     with open("Airflow/config/config.yaml", 'w') as stream:
#         yaml.safe_dump(config, stream)

def perform_pypdf_ocr(pdf_file):
    start_time = time.time()
    pdf_text = []
   
    response = requests.get(pdf_file)
    pdf_content = response.content
    
    # with open(pdf_content, 'rb') as file:
    #     pdf_reader = PdfReader(file)
    #     initial_page_count = len(pdf_reader.pages)

    pdf_reader = PdfReader(io.BytesIO(pdf_content))
    initial_page_count = len(pdf_reader.pages)

    for page_num in range(initial_page_count):
        page = pdf_reader.pages[page_num]
        page_text = page.extract_text()
        pdf_text.append(f"Page {page_num + 1}:\n{page_text}\n")

    extracted_text = '\n'.join(pdf_text)
    end_time = time.time()
    elapsed_time = end_time - start_time

    # Create a summary of the operation
    summary = {
        'Time_Taken_seconds': elapsed_time,
        'characters_sent': len(pdf_file),
        'characters_received': len(extracted_text),
        'initial_page_count': initial_page_count,
        'processed_page_count': initial_page_count  # assuming all pages are processed
    }

    return extracted_text


@app.post("/get_document_data")
async def get_document_data(doc_name: str):
    try:
        # Authentication using Basic Authentication
        auth = HTTPBasicAuth('airflow', 'airflow')  # Use your actual Airflow username and password
        
        # Construct the payload with the provided PDF link
        payload = {
            "conf": {
                "pdf_link": doc_name
            }
        }
        response = requests.post(AIRFLOW_API_ENDPOINT, auth=auth, json=payload)
        pdf_text = perform_pypdf_ocr(doc_name)

        if response.status_code != 200:
            raise Exception(f"Failed to trigger Airflow DAG. Response: {response.text}")

        return {"message": "Document processing started.", "status": "success", "pdf_text": pdf_text}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/get-answer/")
async def get_answer(question: str, context: str):
    # Implement your Q/A logic here using the provided question and context
    # For demonstration, I'll return a mock answer
    return {"answer": "This is a mock answer to your question."}

@app.get("/")
def read_root():
    return {"Hello": "FastAPI"}

#For Local Hosting
def main():
    import uvicorn
    uvicorn.run("main:app", port=8504)

if __name__ == "__main__":
    main()