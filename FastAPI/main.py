from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError
import pinecone
import os
import openai
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from typing import List

import secrets

load_dotenv()
secret_key = secrets.token_hex(32)
PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")
PINECONE_ENV = os.environ.get("PINECONE_ENV")
OPEN_API_KEY = os.environ.get("OPEN_API_KEY")
openai.api_key = os.getenv('OPEN_API_KEY')
app = FastAPI()

# origins = [
#     # "http://localhost:8501",
#     # "http://localhost",
#     # "http://127.0.0.1",
#     "http://streamlit:8501"
# ]
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

class QuestionContext(BaseModel):
    question: str
    context: List[str] = []


# Database configuration
DATABASE_URL = "sqlite:///./test.db"
Base = declarative_base()
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Security and password context setup
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Your secret key and algorithm
SECRET_KEY = secret_key
ALGORITHM = "HS256"

# SQLAlchemy ORM models
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)

# Pydantic models for request and response
class UserRegister(BaseModel):
    username: str
    password: str

# Create the database tables
Base.metadata.create_all(bind=engine)

# Utility functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_user(db, username: str):
    return db.query(User).filter(User.username == username).first()

def authenticate_user(db: Session, username: str, password: str):
    user = get_user(db, username)
    if not user or not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict):
    encoded_jwt = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Routes
@app.post("/register")
def register(user: UserRegister, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_password = pwd_context.hash(user.password)
    new_user = User(username=user.username, hashed_password=hashed_password)
    
    db.add(new_user)
    try:
        db.commit()
        db.refresh(new_user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Username already registered")
    
    access_token = create_access_token(data={"sub": new_user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

# @app.post("/get_document_data")
# async def get_document_data(doc_name: str):
#     try:
#         # Authentication using Basic Authentication
#         #auth = HTTPBasicAuth('airflow', 'airflow')  # Use your actual Airflow username and password
        
#         # Construct the payload with the provided PDF link
#         #
#         # response = requests.post(AIRFLOW_API_ENDPOINT, auth=auth, json=payload)
#         # pdf_text = perform_pypdf_ocr(doc_name)

#         # if response.status_code != 200:
#         #     raise Exception(f"Failed to trigger Airflow DAG. Response: {response.text}")

#         return {"message": "Document processing started.", "status": "success"}

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

@app.post("/get-answer/")
async def get_answer(data: QuestionContext):
    print("Received Input",data.json())

    # Initialize Pinecone
    pinecone.init(api_key="5dc855d8-76cf-48f3-a00e-289d82603ea7", environment="gcp-starter")
    limit = 3750

    # Check if context is empty and set default if necessary
    if not data.context:
        data.context = ["Sec 1662", "FOCUS Report Part IIC Instructions", "Exam Brochure", "Sec 1661", "Sec 2866"]
    openai.api_key = "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"

    def retrieve(question):
        res = openai.Embedding.create(
            input=[question],
            engine= "text-embedding-ada-002"
        )
        index = pinecone.Index(index_name='openai')
        # retrieve from Pinecone
        xq = res['data'][0]['embedding']

        # get relevant contexts
        res = index.query(xq, filter={"PDF_Name": {"$in": data.context}},top_k=3, include_metadata=True)

        contexts = [
            x['metadata']['text'] for x in res['matches']
        ]

        # build our prompt with the retrieved contexts included
        prompt_start = (
            "Answer the question based on the context below.\n\n"+"\nIf answernot found in given context then give response as Enough Context not found"+
            "\nContext:\n"
        )
        prompt_end = (
            f"\n\nQuestion: {question}\nAnswer:"
        )
        # append contexts until hitting limit
        prompt = prompt_start  # Initialize 'prompt' with 'prompt_start' before the loop

        # If there are no contexts, handle the situation appropriately, e.g., by assigning a default value to 'prompt'
        if not contexts:
            prompt += "Enough Context not found" + prompt_end
        else:
            # Use the loop to build 'prompt' with context included
            for i in range(1, len(contexts) + 1):  # Changed loop condition to 'len(contexts) + 1'
                if len("\n\n---\n\n".join(contexts[:i])) + len(prompt_start) + len(prompt_end) >= limit:
                    prompt += "\n\n---\n\n".join(contexts[:i-1]) + prompt_end
                    break
                elif i == len(contexts):  # This ensures the last context is included if under the limit
                    prompt += "\n\n---\n\n".join(contexts) + prompt_end

        return prompt

    def complete(prompt):
        # query text-davinci-003
        res = openai.Completion.create(
            engine='text-davinci-003',
            prompt=prompt,
            temperature=0,
            max_tokens=400,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
            stop=None
        )
        return res['choices'][0]['text'].strip()

    query_with_contexts = retrieve(data.question)
    final_answer = complete(query_with_contexts)
    # For demonstration, I'll return a mock answer
    return {"answer": final_answer}

@app.get("/")
def read_root():
    return {"Hello": "FastAPI"}

#For Local Hosting
def main():
    import uvicorn
    uvicorn.run("main:app", port=8504)

if __name__ == "__main__":
    main()