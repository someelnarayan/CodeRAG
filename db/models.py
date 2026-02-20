from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from .database import Base

from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime

class Repository(Base):
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True)
    repo_url = Column(String, unique=True, index=True)
    last_commit_hash = Column(String)
    status = Column(String)
    progress = Column(Integer, default=0)   # ✅ ADD THIS
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
    status = Column(String)
