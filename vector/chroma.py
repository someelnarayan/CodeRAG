# vector/chroma.py

import chromadb
from setting.settings import CHROMA_PATH

# Persistent Chroma client
client = chromadb.PersistentClient(path=CHROMA_PATH)


def get_collection(repo_name: str):
    """
    Get or create a Chroma collection for a repository.
    Uses repo-specific collection name to avoid embedding conflicts.
    """

    collection_name = f"repo_{repo_name}"

    try:
        collection = client.get_collection(name=collection_name)
    except Exception:
        collection = client.create_collection(name=collection_name)

    return collection