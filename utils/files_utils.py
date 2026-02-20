from urllib.parse import urlparse
from pathlib import Path

BASE_REPO_DIR = Path("data/repos").resolve()

def get_local_repo_path(repo_url: str) -> Path:
    repo_name = urlparse(repo_url).path.rstrip("/").split("/")[-1]
    return BASE_REPO_DIR / repo_name