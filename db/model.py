# db/model.py
from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Repository(Base):
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, index=True)   # ✅ ADD
    repo_url = Column(String, index=True)

    last_commit_hash = Column(String)
    commit_status = Column(String)
    status = Column(String)
    progress = Column(Integer, default=0)


class QATask(Base):
    __tablename__ = "qa_tasks"

    task_id = Column(String, primary_key=True)
    user_id = Column(Integer, index=True)   # ✅ ADD
    repo_url = Column(String)

    question = Column(String)
    answer = Column(String)
    source = Column(String)
    status = Column(String)