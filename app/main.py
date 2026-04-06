from fastapi import FastAPI, BackgroundTasks, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from pydantic import BaseModel, validator
from sqlalchemy.orm import Session
import uuid
from datetime import datetime
from dotenv import load_dotenv
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import traceback

load_dotenv()

from core import ingest_from_git, ask_question
from auth.auth import authenticate_user, create_access_token, get_current_user
from auth.models import Token
from utils.password_utils import hash_password

from db.database import engine, Base, SessionLocal
from sqlalchemy import text

from setting.redis_client import redis_client

from db.model import Repository, QATask, User

from utils.db_session import get_db
from utils.git_utils import get_latest_commit_hash
from utils.files_utils import get_local_repo_path

app = FastAPI()

# =========================
# RATE LIMITER
# =========================
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded"}
    )


# =========================
# DB INIT
# =========================
Base.metadata.create_all(bind=engine)


@app.on_event("startup")
def ensure_db_schema():
    try:
        with engine.begin() as conn:
            conn.execute(
                text("ALTER TABLE qa_tasks ADD COLUMN IF NOT EXISTS source VARCHAR;")
            )
    except Exception as e:
        print("DB migration error:", repr(e))


# =========================
# HEALTH
# =========================
@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        if redis_client:
            redis_client.ping()
        return {"status": "healthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


# =========================
# REQUEST MODELS
# =========================
class IngestRequest(BaseModel):
    repo_url: str

    @validator("repo_url")
    def validate_repo_url(cls, v):
        if not v:
            raise ValueError("repo_url required")
        return v.strip()


class AskRequest(BaseModel):
    repo_url: str
    question: str


# =========================
# BACKGROUND INGEST
# =========================
def ingest_with_status(repo_url: str, user_id: int):

    db = SessionLocal()
    repo = None

    try:

        repo = db.query(Repository).filter(
            Repository.repo_url == repo_url,
            Repository.user_id == user_id
        ).first()

        if not repo:
            return

        repo.status = "processing"
        repo.progress = 0
        db.commit()

        def progress_callback(progress: int):
            try:
                progress_db = SessionLocal()
                progress_db.query(Repository).filter(
                    Repository.repo_url == repo_url,
                    Repository.user_id == user_id
                ).update({"progress": progress})
                progress_db.commit()
                progress_db.close()
            except Exception:
                pass

        ingest_from_git(repo_url, progress_callback=progress_callback)

        # ✅ FIXED: only get commit hash if local repo folder actually exists
        repo_path = get_local_repo_path(repo_url)

        if repo_path.exists() and repo_path.is_dir():
            new_hash = get_latest_commit_hash(repo_path)

            if repo.last_commit_hash is None:
                repo.commit_status = "first_time"
            elif repo.last_commit_hash == new_hash:
                repo.commit_status = "same_repo"
            else:
                repo.commit_status = "updated"

            repo.last_commit_hash = new_hash
        else:
            # ✅ folder missing means it was already indexed before (stale state)
            # ingest_from_git already handled this gracefully, just mark status
            repo.commit_status = "already_indexed"

        repo.progress = 100
        repo.status = "completed"
        db.commit()

    except Exception as e:

        print("INGEST ERROR:")
        traceback.print_exc()

        if repo:
            repo.status = "failed"
            repo.commit_status = "failed"
            db.commit()

    finally:
        db.close()


# =========================
# BACKGROUND Q&A
# =========================
def process_question(task_id: str, repo_url: str, question: str, user_id: int):

    db = SessionLocal()

    try:

        task = db.query(QATask).filter(
            QATask.task_id == task_id,
            QATask.user_id == user_id
        ).first()

        if not task:
            return

        print("Processing question:", question)

        result = ask_question(repo_url, question)

        task.status = "completed"

        if isinstance(result, dict):
            task.answer = result.get("answer")
            task.source = result.get("source")
        else:
            task.answer = result

        task.completed_at = datetime.utcnow()
        db.commit()

    except Exception as e:

        print("QA ERROR:")
        traceback.print_exc()

        task.status = "failed"
        task.answer = str(e)
        db.commit()

    finally:
        db.close()


# =========================
# AUTH
# =========================
@app.post("/auth/signup")
def signup(username: str, password: str, db: Session = Depends(get_db)):

    username = username.strip().lower()

    if not username:
        raise HTTPException(status_code=400, detail="Username cannot be empty")

    if " " in username:
        raise HTTPException(status_code=400, detail="Username cannot contain spaces")

    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters long")

    existing_user = db.query(User).filter(User.username == username).first()

    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    password_hash = hash_password(password)

    new_user = User(
        username=username,
        password_hash=password_hash,
        created_at=datetime.utcnow()
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "message": "User created successfully",
        "user_id": new_user.id,
        "username": new_user.username
    }


@app.post("/auth/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):

    username = form_data.username.strip().lower()
    password = form_data.password

    if not username:
        raise HTTPException(status_code=400, detail="Username cannot be empty")

    if " " in username:
        raise HTTPException(status_code=400, detail="Username cannot contain spaces")

    user = authenticate_user(username, password)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": user["username"]})

    return {
        "access_token": token,
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
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    repo = db.query(Repository).filter(
        Repository.repo_url == req.repo_url,
        Repository.user_id == user["id"]
    ).first()

    if not repo:
        repo = Repository(
            repo_url=req.repo_url,
            user_id=user["id"],
            status="started",
            progress=0
        )
        db.add(repo)
        db.commit()

    background_tasks.add_task(
        ingest_with_status,
        req.repo_url,
        user["id"]
    )

    return {"status": "started"}


# =========================
# STATUS API
# =========================
@app.get("/status")
def get_status(
    repo_url: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    repo = db.query(Repository).filter(
        Repository.repo_url == repo_url,
        Repository.user_id == user["id"]
    ).first()

    if not repo:
        return {"status": "not_found", "progress": 0}

    return {
        "status": repo.status,
        "progress": repo.progress
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
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    repo = db.query(Repository).filter(
        Repository.repo_url == req.repo_url,
        Repository.user_id == user["id"]
    ).first()

    if not repo:
        raise HTTPException(
            status_code=400,
            detail="Repository not found. Please ingest it first."
        )

    if repo.status == "processing":
        raise HTTPException(
            status_code=400,
            detail=f"Repository is still being ingested ({repo.progress}% complete). Please wait."
        )

    if repo.status == "failed":
        raise HTTPException(
            status_code=400,
            detail="Repository ingestion failed. Please re-ingest."
        )

    if repo.status != "completed":
        raise HTTPException(
            status_code=400,
            detail="Repository is not ready yet. Please wait for ingestion to complete."
        )

    task_id = str(uuid.uuid4())

    task = QATask(
        task_id=task_id,
        user_id=user["id"],
        repo_url=req.repo_url,
        question=req.question,
        status="processing"
    )

    db.add(task)
    db.commit()

    background_tasks.add_task(
        process_question,
        task_id,
        req.repo_url,
        req.question,
        user["id"]
    )

    return {"task_id": task_id, "status": "processing"}


# =========================
# RESULT API
# =========================
@app.get("/result/{task_id}")
def get_result(
    task_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    task = db.query(QATask).filter(
        QATask.task_id == task_id,
        QATask.user_id == user["id"]
    ).first()

    if not task:
        return {"status": "not_found"}

    return {
        "status": task.status,
        "message": (
            "Generating response..." if task.status == "processing"
            else "Response generated successfully." if task.status == "completed"
            else "Request failed."
        ),
        "answer": task.answer,
        "source": task.source
    }