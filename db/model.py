from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from .database import Base


class Repository(Base):
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True)
    repo_url = Column(String, unique=True, index=True)

    last_commit_hash = Column(String)

    # ✅ REQUIRED CHANGE (NEW)
    commit_status = Column(String)
    # values: first_time | same_repo | updated | failed

    status = Column(String)
    progress = Column(Integer, default=0)
    indexed_at = Column(DateTime, default=datetime.utcnow)


class IngestionTask(Base):
    __tablename__ = "ingestion_tasks"

    task_id = Column(String, primary_key=True)
    repo_url = Column(String)
    status = Column(String)
    progress = Column(Integer)


class QATask(Base):
    __tablename__ = "qa_tasks"

    task_id = Column(String, primary_key=True)
    repo_url = Column(String)
    question = Column(String)
    answer = Column(String)
    source = Column(String, nullable=True)
    status = Column(String)