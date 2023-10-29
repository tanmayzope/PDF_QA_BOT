# FastAPI/Dockerfile

# Use an official Python runtime as the parent image
FROM python:3.10-slim

# Set the working directory in the container to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install pipenv and application dependencies
RUN pip install pipenv && pipenv install --deploy --ignore-pipfile

# Specify the command to run on container start
CMD ["pipenv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8504", "--reload"]
