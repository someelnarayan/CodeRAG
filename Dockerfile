FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system build deps required for some Python packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        libpq-dev \
        libssl-dev \
        libffi-dev \
        ca-certificates \
        curl && \
    rm -rf /var/lib/apt/lists/*

# Copy pinned requirements and install
COPY requirements.txt ./requirements.txt
RUN python -m pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Create a non-root user and ensure user owns app dir
RUN useradd -m appuser && chown -R appuser /app

# Copy project files (uses .dockerignore to avoid large examples)
COPY . .

USER appuser

# Render provides a dynamic port via the $PORT env variable.
EXPOSE 8000

# Set embedding mode to production (SentenceTransformer) unless overridden
ENV USE_OLLAMA=false

# Run uvicorn binding to the provided PORT (defaults to 8000 locally)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
