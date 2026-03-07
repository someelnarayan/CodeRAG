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

# Copy project files
COPY . .

USER appuser

# Render dynamic port
EXPOSE 10000

# Production embedding mode
ENV USE_OLLAMA=false

# Start FastAPI server
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]