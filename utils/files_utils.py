from urllib.parse import urlparse
from pathlib import Path

BASE_REPO_DIR = Path("data/repos").resolve()

BASE_REPO_DIR.mkdir(parents=True, exist_ok=True)


def get_local_repo_path(repo_url: str) -> Path:
    repo_name = urlparse(repo_url).path.rstrip("/").split("/")[-1].replace(".git", "")
    return BASE_REPO_DIR / repo_name