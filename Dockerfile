FROM python:3.11-slim

WORKDIR /app

# Install system deps for bcrypt
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirement.txt ./
RUN pip install --no-cache-dir -r requirement.txt

COPY . .

EXPOSE 8000

# use shell form so environment variable is expanded; Render sets $PORT
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
