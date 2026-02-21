import re

def normalize_question(question: str) -> str:
    q = question.lower()
    q = re.sub(r"[^a-z0-9]+", "_", q)
    return q.strip("_")

def make_cache_key(repo_id: str, commit_hash: str, question: str) -> str:
    return f"{repo_id}:{commit_hash}:{normalize_question(question)}"