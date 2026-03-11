import re
import hashlib


def normalize_question(question: str) -> str:
    q = question.lower()
    q = re.sub(r"[^a-z0-9]+", "_", q)
    return q.strip("_")


def make_cache_key(repo_id: str, commit_hash: str, question: str) -> str:

    normalized = normalize_question(question)

    # avoid very long redis keys
    hashed = hashlib.md5(normalized.encode()).hexdigest()

    return f"{repo_id}:{commit_hash}:{hashed}"