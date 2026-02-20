import os

IGNORE_DIRS = {
    ".git", ".github", "tests", "test",
    "docs", "doc", "__pycache__",
    "node_modules", "venv", ".venv"
}

ALLOWED_EXTENSIONS = {
    ".py", ".js", ".ts", ".java", ".go", ".cpp", ".c"
}

def load_repository(repo_path):
    files = []

    for root, dirs, filenames in os.walk(repo_path):
        # 🔥 skip junk directories
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

        for filename in filenames:
            ext = os.path.splitext(filename)[1]

            # 🔥 skip non-code files
            if ext not in ALLOWED_EXTENSIONS:
                continue

            file_path = os.path.join(root, filename)

            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    files.append({
                        "path": file_path,
                        "content": f.read()
                    })
            except Exception:
                continue

    return files
