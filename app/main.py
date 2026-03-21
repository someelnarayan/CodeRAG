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


@app.get("/health/groq")
def test_groq_connection():
    """Test if Groq API key is valid and working"""
    try:
        from llm.llm import groq_client, GROQ_API_KEY
        
        if not groq_client:
            return {
                "status": "error",
                "message": "Groq client not initialized",
                "api_key": "MISSING" if not GROQ_API_KEY else f"{GROQ_API_KEY[:20]}..."
            }
        
        # Try a simple API call to test the key
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": "Say 'OK'"}],
            max_tokens=10,
            timeout=5
        )
        
        return {
            "status": "ok",
            "message": "Groq API is working",
            "api_key": f"{GROQ_API_KEY[:20]}...{GROQ_API_KEY[-4:]}",
            "response": response.choices[0].message.content
        }
    
    except Exception as e:
        error_msg = str(e)
        return {
            "status": "error",
            "message": error_msg,
            "api_key": f"{GROQ_API_KEY[:20]}...{GROQ_API_KEY[-4:]}" if GROQ_API_KEY else "MISSING",
            "suggestion": "Get a new key from https://console.groq.com" if "401" in error_msg or "invalid" in error_msg.lower() else None
        }


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

    try:

        repo = db.query(Repository).filter(
            Repository.repo_url == repo_url,
            Repository.user_id == user_id
        ).first()

        if not repo:
            return

        repo.status = "processing"
        repo.progress = 50
        db.commit()

        ingest_from_git(repo_url)

        repo_path = get_local_repo_path(repo_url)
        new_hash = get_latest_commit_hash(repo_path)

        if repo.last_commit_hash is None:
            repo.commit_status = "first_time"

        elif repo.last_commit_hash == new_hash:
            repo.commit_status = "same_repo"

        else:
            repo.commit_status = "updated"

        repo.last_commit_hash = new_hash
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
        "answer": task.answer,
        "source": task.source
    }


# =========================
# ADMIN - CACHE MANAGEMENT
# =========================
@app.delete("/cache/clear")
def clear_all_cache(user: dict = Depends(get_current_user)):
    """Clear all cached answers. Useful for debugging."""
    if not redis_client:
        return {"status": "redis_not_configured"}
    
    try:
        redis_client.flushdb()
        return {"status": "success", "message": "All cache cleared"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.delete("/cache/clear/{repo_url}")
def clear_repo_cache(repo_url: str, user: dict = Depends(get_current_user)):
    """Clear cached answers for a specific repo."""
    if not redis_client:
        return {"status": "redis_not_configured"}
    
    try:
        from utils.files_utils import get_local_repo_path
        repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
        
        # Delete all keys matching this repo
        pattern = f"cache:*:{repo_name}:*"
        keys = redis_client.keys(pattern)
        
        if keys:
            redis_client.delete(*keys)
            return {"status": "success", "message": f"Cleared {len(keys)} cached entries for {repo_name}"}
        else:
            return {"status": "success", "message": f"No cache entries found for {repo_name}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}