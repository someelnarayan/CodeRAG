from pathlib import Path
import git
from utils.files_utils import get_local_repo_path


def clone_repository(repo_url: str, repo_path: Path | None = None):
    """
    Clone a repository if it doesn't exist locally.
    Uses gitpython instead of subprocess git command.
    """

    if repo_path is None:
        repo_path = get_local_repo_path(repo_url)

    repo_path = repo_path.resolve()

    repo_path.parent.mkdir(parents=True, exist_ok=True)

    # Already cloned
    if repo_path.exists():
        print(f"Repo already exists at {repo_path}, skipping clone.")
        return repo_path

    print(f"Cloning {repo_url} into {repo_path}...")

    git.Repo.clone_from(
        repo_url,
        str(repo_path),
        depth=1  # shallow clone, same as before
    )

    return repo_path