# retrieval/keyword.py

from db.database import SessionLocal
from db.models.code_chunk import CodeChunk
import uuid


NAMESPACE_UUID = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')


def _ensure_uuid(repo_id):
    if isinstance(repo_id, uuid.UUID):
        return repo_id

    try:
        return uuid.UUID(str(repo_id))
    except Exception:
        return uuid.uuid5(NAMESPACE_UUID, str(repo_id))


def keyword_search(repo_id, query, limit=5):
    db = SessionLocal()
    try:
        repo_uuid = _ensure_uuid(repo_id)

        results = (
            db.query(CodeChunk)
            .filter(CodeChunk.repo_id == repo_uuid)
            .filter(CodeChunk.content_tsv.match(query))
            .limit(limit)
            .all()
        )

        return results

    finally:
        db.close()