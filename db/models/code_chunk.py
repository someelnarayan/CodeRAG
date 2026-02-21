import uuid
from sqlalchemy import Column, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, TSVECTOR
from sqlalchemy.sql import func
from db.database import Base


class CodeChunk(Base):
    __tablename__ = "code_chunks"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    repo_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )

    file_path = Column(
        Text,
        nullable=False
    )

    content = Column(
        Text,
        nullable=False
    )

    # 🔥 keyword search ke liye
    content_tsv = Column(
        TSVECTOR
    )

    commit_hash = Column(
        Text,
        nullable=False
    )