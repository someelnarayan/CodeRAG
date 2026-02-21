from db.database import SessionLocal
from db.models.code_chunk import CodeChunk
import uuid


NAMESPACE_UUID = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')


def _ensure_uuid(repo_id):
    # If repo_id is already a UUID object, return it
    if isinstance(repo_id, uuid.UUID):
        return repo_id

    # If it's a string that is a valid UUID, parse it
    try:
        return uuid.UUID(str(repo_id))
    except Exception:
        # Treat as repo name and generate a stable UUID using uuid5
        return uuid.uuid5(NAMESPACE_UUID, str(repo_id))


def keyword_search(repo_id, query, limit=5):
    db = SessionLocal()
    repo_uuid = _ensure_uuid(repo_id)
    return (
        db.query(CodeChunk)
        .filter(CodeChunk.repo_id == repo_uuid)
        .filter(CodeChunk.content_tsv.match(query))
        .limit(limit)
        .all()
    )