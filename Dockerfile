# Use a lightweight Python image
FROM python:3.12-slim

# Prevent Python from creating .pyc files
# and ensure logs are immediately visible
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Application working directory
WORKDIR /app

# Install Python dependencies first
# This improves Docker layer caching
COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY app/ ./app/

# Copy frontend
COPY frontend/ ./frontend/

# Expose FastAPI port
EXPOSE 8000

# Start CalcCast application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

