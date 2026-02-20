import os
import subprocess
from pathlib import Path

# ✅ SINGLE SOURCE OF TRUTH
from utils.files_utils import get_local_repo_path


def clone_repository(repo_url: str, repo_path: Path | None = None):
    """
    Clone repo into a fixed local path:
    data/repos/<repo_name>

    If already exists → skip clone
    """

    # 🔹 If path not provided, derive it
    if repo_path is None:
        repo_path = get_local_repo_path(repo_url)

    repo_path = repo_path.resolve()

    # 🔹 Ensure parent directory exists
    repo_path.parent.mkdir(parents=True, exist_ok=True)

    # 🔹 Already cloned
    if repo_path.exists():
        return repo_path

    # 🔹 Clone repo
    subprocess.run(
        ["git", "clone", "--depth", "1", repo_url, str(repo_path)],
        check=True
    )

    return repo_path