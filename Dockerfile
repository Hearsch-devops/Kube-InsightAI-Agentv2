# Use a lightweight Python image
FROM python:3.12-slim

# Prevent Python from creating .pyc files
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Application working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY app/ ./app/

# Copy LangChain RAG modules
COPY lc_demos/ ./lc_demos/

# Copy RAG vector database
COPY retrieval-augmented-generation/chroma_db/ \
     ./retrieval-augmented-generation/chroma_db/

# Copy frontend
COPY frontend/ ./frontend/

# Expose FastAPI port
EXPOSE 8000

# Start Kube-InsightAI
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
