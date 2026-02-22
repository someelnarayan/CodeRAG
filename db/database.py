import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Load environment variables from .env file
load_dotenv()

# Read database URL from environment, fallback to localhost if not set
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@127.0.0.1:5432/code_ragg_db"
)

engine = create_engine(DATABASE_URL, echo=True)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)

Base = declarative_base()
