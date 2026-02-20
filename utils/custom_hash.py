import hashlib
import os

IGNORE_DIRS = {".git", "venv", "__pycache__", "node_modules"}

def get_code_file(repo_path):
    code_files = []
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for f in files:
            if f.endswith((".py", ".js", ".ts", ".java", ".cpp", ".go")):
                code_files.append(os.path.join(root, f))
    return code_files



def hash_repo(repo_path):
    hasher = hashlib.md5()
    for root, _, files in os.walk(repo_path):
        for f in files:
            path = os.path.join(root, f)
            with open(path, "rb") as file:
                hasher.update(file.read())
    return hasher.hexdigest()
