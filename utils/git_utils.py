import subprocess
from pathlib import Path

def get_latest_commit_hash(repo_path: Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_path
    ).decode().strip()