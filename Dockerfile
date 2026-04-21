FROM python:3.11-slim

WORKDIR /app

# =========================
# SYSTEM DEPENDENCIES
# =========================
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    git \
    && rm -rf /var/lib/apt/lists/*

# =========================
# PYTHON DEPENDENCIES
# =========================
COPY requirements_backend.txt ./

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements_backend.txt

# =========================
# COPY PROJECT
# =========================
COPY . .

# =========================
# PORT
# =========================
EXPOSE 8000

# =========================
# RUN APP (RENDER FRIENDLY)
# =========================
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]