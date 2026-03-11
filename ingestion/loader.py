# ingestion/cloner.py

import subprocess
from pathlib import Path

from utils.files_utils import get_local_repo_path


def clone_repository(repo_url: str, repo_path: Path | None = None):

    if repo_path is None:
        repo_path = get_local_repo_path(repo_url)

    repo_path = repo_path.resolve()

    repo_path.parent.mkdir(parents=True, exist_ok=True)

    if repo_path.exists():
        return repo_path

    subprocess.run(
        ["git", "clone", "--depth", "1", repo_url, str(repo_path)],
        check=True
    )

    return repo_path