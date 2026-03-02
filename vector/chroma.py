
from setting.settings import CHROMA_PATH



def get_collection(repo_name):
    import chromadb
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    return client.get_or_create_collection(name=f"repo_{repo_name}")
