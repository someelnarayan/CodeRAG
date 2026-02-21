from fastapi import FastAPI, BackgroundTasks, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session
import uuid
import time
from datetime import datetime

from core import ingest_from_git, ask_question
from auth.auth import authenticate_user, create_access_token, get_current_user
from auth.models import Token

from db.database import engine, Base, SessionLocal
from sqlalchemy import text

# 🔥 REQUIRED FIX #1: correct import path
from db.model import Repository, QATask

from utils.db_session import get_db
from utils.git_utils import get_latest_commit_hash
from utils.files_utils import get_local_repo_path

app = FastAPI()

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

# =========================
# REQUEST MODELS
# =========================

class IngestRequest(BaseModel):
    repo_url: str


class AskRequest(BaseModel):
    repo_url: str
    question: str

# =========================
# BACKGROUND INGESTION
# =========================

def ingest_with_status(repo_url: str):
    print("BACKGROUND INGEST TASK STARTED:", repo_url)  # 🔥 REQUIRED FIX #2

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
            repo.commit_status = "same_as_before"
        else:
            repo.commit_status = "updated"

        old_hash = repo.last_commit_hash
        new_hash = get_latest_commit_hash(repo_path)

        if old_hash is None:
            repo.commit_status = "first_time"
        elif old_hash == new_hash:
            repo.commit_status = "same_as_before"
        else:
            repo.commit_status = "updated"

        repo.last_commit_hash = new_hash
        repo.progress = 100
        repo.status = "completed"
        db.commit()

        print("BACKGROUND INGEST TASK COMPLETED:", repo_url)  # 🔥 REQUIRED FIX #3

    except Exception as e:
        print("INGEST ERROR:", e)
        if repo:
            repo.status = "failed"
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
def ingest(
    req: IngestRequest,
    background_tasks: BackgroundTasks,
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

    if repo_path.exists() and repo.last_commit_hash:
        latest_hash = get_latest_commit_hash(repo_path)
        if repo.last_commit_hash == latest_hash and repo.status == "completed":
            return {
                "status": "skipped",
                "message": "Repo already indexed, no code changes detected"
            }

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
def ask(
    req: AskRequest,
    background_tasks: BackgroundTasks,
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
#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

