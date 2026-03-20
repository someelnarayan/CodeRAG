import os

IGNORE_DIRS = {
    ".git",
    ".github",
    "tests",
    "test",
    "docs",
    "doc",
    "__pycache__",
    "node_modules",
    "venv",
    ".venv",
}

ALLOWED_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".java",
    ".go",
    ".cpp",
    ".c",
}


def load_repository(repo_path):
    """
    Load all supported code files from the repository.
    Returns a list of {path, content}
    """

    files = []

    for root, dirs, filenames in os.walk(repo_path):

        # remove ignored directories
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

        for filename in filenames:

            ext = os.path.splitext(filename)[1]

            if ext not in ALLOWED_EXTENSIONS:
                continue

            file_path = os.path.join(root, filename)

            try:

                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:

                    content = f.read()

                    files.append({
                        "path": file_path,
                        "content": content
                    })

            except Exception as e:

                print(f"Skipped file {file_path}: {e}")

    print(f"Loaded {len(files)} files")

    return files