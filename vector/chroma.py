
from setting.settings import CHROMA_PATH
from utils.embedding_loader import get_embedding_function


def get_collection(repo_name):
    import chromadb

    client = chromadb.PersistentClient(path=CHROMA_PATH)
    embedding_func = get_embedding_function()
    
    return client.get_or_create_collection(
        name=f"repo_{repo_name}",
        embedding_function=embedding_func
    )
