# Code Ragg — Codebase Q&A Service

Brief: Code Ragg is a FastAPI service that ingests repositories, embeds code chunks into a vector store, and provides a RAG (retrieval-augmented generation) Q&A API over codebases. It supports local LLMs (Ollama) or a cloud LLM (Groq), caching with Redis, and stores metadata in PostgreSQL.

Tech stack
- FastAPI (HTTP API)
- SQLAlchemy (Postgres ORM)
- Chroma (vector store)
- Redis (optional caching)
- Ollama / Groq (LLM backends)
- Docker / docker-compose for containerization

Repository layout (key files)
- `app/main.py`: FastAPI application and API endpoints.
- `auth/`: authentication helpers and Pydantic models.
- `db/`: SQLAlchemy database & models (`db/database.py`, `db/model.py`).
- `core.py`: ingestion and ask/answer orchestration.
- `ingestion/`, `embeddings/`, `llm/`, `retrieval/`, `vector/`: pipeline components.
- `setting/`: configuration and `redis_client.py`.
- `Dockerfile`, `docker-compose.yml`: container definitions for local/dev runs.
- `requirement.txt`: pinned Python dependencies for reproducible installs.
- `.env.example`: example environment variables for deployment.
- `alembic/`: migration scaffold (use Alembic for schema changes).

Quick start (development)
1. Copy environment file and set secrets:
   - Copy `.env.example` to `.env` and fill values for `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`.
2. Create and activate a venv, then install deps:
   ```powershell
   & 'D:\hp\Desktop\pro1\venv\Scripts\python.exe' -m pip install -r requirement.txt
   ```
3. Run the app locally:
   ```powershell
   $env:SECRET_KEY='your_secret'; $env:DATABASE_URL='postgresql://...'; & 'D:\hp\Desktop\pro1\venv\Scripts\python.exe' -m uvicorn app.main:app --reload
   ```

Docker (recommended for deploy)
- Build image: `docker build -t code-ragg .`
- Run with compose (starts services like Ollama if enabled): `docker compose up --build`
- Use `.dockerignore` to keep images small (large example repos are excluded).

> **Port configuration**
>
> When deploying on Render (or any platform providing a dynamic port), the
> service listens on the port specified by the `PORT` environment variable. The
> Dockerfile uses a shell command (`uvicorn ... --port ${PORT:-8000}`) so the
> variable is expanded at runtime and defaults to `8000` locally. Make sure the
> deployment environment sets `PORT` (Render does this automatically).

Deploy notes (production checklist)
- Secrets: store `SECRET_KEY`, DB credentials, and `REDIS_URL` in a secrets manager (do not hard-code).
- Database migrations: use Alembic (generate with `alembic revision --autogenerate -m "initial"` and apply with `alembic upgrade head`).
- Passwords: the app uses `passlib` (bcrypt) for hashing; ensure existing users are migrated if you previously stored plaintext.
- Caching: Redis is optional — when `REDIS_URL` is unset the service runs without caching.
- Vector store: Chroma currently uses local files — for high availability use a managed vector DB or persistent storage volume.
- Background tasks: ingestion is implemented using FastAPI background tasks — consider moving to a worker queue (Celery/RQ) for scale.
- Monitoring & logging: add structured logs, health/readiness probes, and an error reporting service (e.g., Sentry).
- Pin dependency versions (`requirement.txt`) and add CI to run tests and linters.

Testing & CI
- Tests: `pytest` is configured but the repo does not include application tests by default; add unit/integration tests under `tests/`.
- CI: add a workflow that installs pinned deps, runs `pytest`, runs linters (`ruff`/`mypy`), and builds the Docker image.

Files you should review before deploying
- `auth/auth.py` — ensure `SECRET_KEY` comes from environment and password hashing is enabled.
- `db/database.py` & `alembic/env.py` — point Alembic `sqlalchemy.url` to your production DB before running migrations.
- `docker-compose.yml` and `Dockerfile` — verify which services (Ollama, Postgres, Redis) you want Render/Kubernetes to run.

Next steps I can take for you
- Generate and apply an Alembic initial migration.
- Create a GitHub Actions CI workflow (tests, lint, build and publish image).
- Add a Render/GCP/AWS deployment manifest and secrets guide.

If you want me to proceed with any of the next steps above, tell me which one and I'll implement it.

***
Generated on project scan — edit as needed before sharing.
