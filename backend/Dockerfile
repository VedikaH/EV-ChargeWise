# FROM python:3.11-slim

# # Set the working directory inside the container
# WORKDIR /backend

# # Copy only requirements.txt first (from backend/)
# COPY requirements.txt /backend/requirements.txt

# # Install dependencies
# RUN pip install --upgrade pip && pip install -r /backend/requirements.txt

# # Copy app source code into container
# COPY app /backend/app

# # Copy .env file for env loading (if used by scripts)
# COPY .env /backend/.env

# # Run Alembic + start Uvicorn (if used this way)
# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /backend

# Copy requirements.txt first for better caching
COPY requirements.txt /backend/requirements.txt

# Install dependencies
RUN pip install --upgrade pip && pip install -r /backend/requirements.txt

# Copy the entire project
COPY . /backend/

# Add backend to PYTHONPATH
ENV PYTHONPATH=/backend:$PYTHONPATH

# Default command (will be overridden by docker-compose)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]