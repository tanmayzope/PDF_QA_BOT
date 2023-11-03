from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError

import secrets
secret_key = secrets.token_hex(32)
print(secret_key)


app = FastAPI()

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

@app.post("/get_document_data")
async def get_document_data(doc_name: str):
    try:
        # Authentication using Basic Authentication
        #auth = HTTPBasicAuth('airflow', 'airflow')  # Use your actual Airflow username and password
        
        # Construct the payload with the provided PDF link
        #
        # response = requests.post(AIRFLOW_API_ENDPOINT, auth=auth, json=payload)
        # pdf_text = perform_pypdf_ocr(doc_name)

        # if response.status_code != 200:
        #     raise Exception(f"Failed to trigger Airflow DAG. Response: {response.text}")

        return {"message": "Document processing started.", "status": "success"}

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