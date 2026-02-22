from fastapi import FastAPI, BackgroundTasks, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from pydantic import BaseModel, validator
from sqlalchemy.orm import Session
import uuid
import time
from datetime import datetime
from dotenv import load_dotenv
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Load environment variables from .env file at startup
load_dotenv()

from core import ingest_from_git, ask_question
from auth.auth import authenticate_user, create_access_token, get_current_user
from auth.models import Token

from db.database import engine, Base, SessionLocal
from sqlalchemy import text

# Redis client (used by health check and cache operations)
from setting.redis_client import redis_client

# 🔥 REQUIRED FIX #1: correct import path
from db.model import Repository, QATask

from utils.db_session import get_db
from utils.git_utils import get_latest_commit_hash
from utils.files_utils import get_local_repo_path

app = FastAPI()

# ✅ Setup Rate Limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Max 10 requests per minute."}
    )

# =========================
# DB INIT
# =========================
Base.metadata.create_all(bind=engine)


@app.on_event("startup")
def ensure_db_schema():
    """Ensure optional columns exist (safe to run multiple times).
    Adds `source` column to `qa_tasks` if missing to avoid runtime errors.
    """
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE qa_tasks ADD COLUMN IF NOT EXISTS source VARCHAR;"))
        print("DB: ensured qa_tasks.source column exists")
    except Exception as e:
        print("DB migration error:", repr(e))

# Health check for monitoring
@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Simple health check - used by load balancers and monitoring."""
    try:
        # Can we reach the database?
        db.execute(text("SELECT 1"))
        db_status = "ok"
        
        # Can we reach Redis?
        try:
            redis_client.ping()
            redis_status = "ok"
        except:
            redis_status = "down"
        
        # Is Ollama running? (only check if we're using it)
        from setting.settings import USE_GROQ, OLLAMA_HEALTH_URL
        if USE_GROQ:
            ollama_status = "not_used"
        else:
            try:
                import requests
                requests.get(OLLAMA_HEALTH_URL, timeout=2)
                ollama_status = "ok"
            except:
                ollama_status = "down"
        
        return {
            "status": "healthy",
            "services": {
                "database": db_status,
                "redis": redis_status,
                "ollama": ollama_status
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

class IngestRequest(BaseModel):
    repo_url: str
    
    @validator('repo_url')
    def validate_repo_url(cls, v):
        v = v.strip() if v else ""
        if not v:
            raise ValueError("please provide a repo URL")
        if len(v) > 500:
            raise ValueError("repo URL is too long")
        if not (v.startswith("http://") or v.startswith("https://") or v.startswith("git@")):
            raise ValueError("use a valid git URL (http://, https://, or git@)")
        return v


class AskRequest(BaseModel):
    repo_url: str
    question: str
    
    @validator('repo_url')
    def validate_repo_url(cls, v):
        v = v.strip() if v else ""
        if not v:
            raise ValueError("please provide a repo URL")
        if len(v) > 500:
            raise ValueError("repo URL is too long")
        if not (v.startswith("http://") or v.startswith("https://") or v.startswith("git@")):
            raise ValueError("use a valid git URL (http://, https://, or git@)")
        return v
    
    @validator('question')
    def validate_question(cls, v):
        v = v.strip() if v else ""
        if not v:
            raise ValueError("please ask a question")
        if len(v) < 3:
            raise ValueError("your question is too short (at least 3 characters)")
        if len(v) > 2000:
            raise ValueError("your question is too long (max 2000 characters)")
        return v

# =========================
# BACKGROUND INGESTION
# =========================

# Run ingestion in the background
def ingest_with_status(repo_url: str):
    print(f"Starting ingestion for: {repo_url}")

    db = SessionLocal()
    repo = None

    try:
        repo = db.query(Repository).filter(
            Repository.repo_url == repo_url
        ).first()

        if not repo:
            return

        repo.status = "processing"
        repo.progress = 10
        db.commit()
        time.sleep(1)

        repo.progress = 30
        db.commit()
        time.sleep(1)

        repo.progress = 50
        db.commit()

        ingest_from_git(repo_url)

        repo.progress = 70
        db.commit()
        time.sleep(1)

        repo_path = get_local_repo_path(repo_url)
        if not repo_path.exists():
            raise Exception("Repo path does not exist")

        old_hash = repo.last_commit_hash
        new_hash = get_latest_commit_hash(repo_path)

        if old_hash is None:
            repo.commit_status = "first_time"
        elif old_hash == new_hash:
            repo.commit_status = "same_repo"
        else:
            repo.commit_status = "updated"

        repo.last_commit_hash = new_hash
        repo.progress = 100
        repo.status = "completed"
        db.commit()

        print(f"Done! Indexed {repo_url}")

    except Exception as e:
        print("INGEST ERROR:", e)
        if repo:
            repo.status = "failed"
            repo.commit_status = "failed"   # ✅ REQUIRED FIX
            db.commit()

    finally:
        db.close()

# =========================
# BACKGROUND Q&A
# =========================

def process_question(task_id: str, repo_url: str, question: str):
    db = SessionLocal()

    try:
        # Load the task record first so we can update status on failure
        task = db.query(QATask).filter(
            QATask.task_id == task_id
        ).first()

        if not task:
            print(f"Q&A TASK NOT FOUND: {task_id}")
            return

        # Ensure task marked processing (in case worker restarted)
        task.status = "processing"
        db.commit()

        # Run the actual QA pipeline
        result = ask_question(repo_url, question)

        task.status = "completed"
        if isinstance(result, dict):
            task.answer = result.get("answer")
            task.source = result.get("source")
        else:
            task.answer = result
            task.source = None
        task.completed_at = datetime.utcnow()
        db.commit()

    except Exception as e:
        print("Q&A ERROR:", repr(e))
        try:
            if 'task' in locals() and task:
                task.status = "failed"
                task.answer = f"Error: {str(e)}"
                task.completed_at = datetime.utcnow()
                db.commit()
        except Exception as db_e:
            print("Failed to update task status:", repr(db_e))

    finally:
        db.close()

# =========================
# AUTH
# =========================

@app.post("/auth/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(
        data={"sub": user["username"]}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

# =========================
# INGEST API
# =========================

@app.post("/ingest")
@limiter.limit("3/minute")
def ingest(
    req: IngestRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    repo = db.query(Repository).filter(
        Repository.repo_url == req.repo_url
    ).first()

    if not repo:
        repo = Repository(
            repo_url=req.repo_url,
            status="started",
            progress=0,
            last_commit_hash=None
        )
        db.add(repo)
        db.commit()
        db.refresh(repo)

    repo_path = get_local_repo_path(req.repo_url)

    # 🔥 REQUIRED FIX STARTS HERE
    if repo_path.exists() and repo.last_commit_hash:
        latest_hash = get_latest_commit_hash(repo_path)

        if repo.last_commit_hash == latest_hash and repo.status == "completed":
            # ✅ UPDATE COMMIT STATUS EVEN ON SKIP
            repo.commit_status = "same_repo"
            db.commit()

            return {
                "status": "skipped",
                "message": "Repo already indexed, no code changes detected"
            }
    # 🔥 REQUIRED FIX ENDS HERE

    repo.status = "processing"
    repo.progress = 0
    db.commit()

    background_tasks.add_task(
        ingest_with_status,
        req.repo_url
    )

    return {
        "status": "started",
        "message": "Ingestion started"
    }

# =========================
# ASK API
# =========================

@app.post("/ask")
@limiter.limit("10/minute")
def ask(
    req: AskRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task_id = str(uuid.uuid4())

    task = QATask(
        task_id=task_id,
        repo_url=req.repo_url,
        question=req.question,
        status="processing"
    )

    db.add(task)
    db.commit()
    db.refresh(task)

    background_tasks.add_task(
        process_question,
        task_id,
        req.repo_url,
        req.question
    )

    return {
        "task_id": task_id,
        "status": "processing"
    }

# =========================
# RESULT API
# =========================

@app.get("/result/{task_id}")
def get_result(
    task_id: str,
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task = db.query(QATask).filter(
        QATask.task_id == task_id
    ).first()

    if not task:
        return {"status": "not_found"}

    return {
        "status": task.status,
        "answer": task.answer,
        "source": getattr(task, "source", None)
    }
