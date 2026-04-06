import subprocess
from pathlib import Path


def get_latest_commit_hash(repo_path: Path) -> str:
    repo_path = Path(repo_path).resolve()

    if not repo_path.exists():
        raise FileNotFoundError(f"Repo path does not exist: {repo_path}")

    if not repo_path.is_dir():
        raise NotADirectoryError(f"Repo path is not a directory: {repo_path}")

    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=str(repo_path)
    ).decode().strip()