import chromadb
from setting.settings import CHROMA_PATH

client = chromadb.PersistentClient(path=CHROMA_PATH)

def get_collection(repo_name):
    return client.get_or_create_collection(name=f"repo_{repo_name}")
