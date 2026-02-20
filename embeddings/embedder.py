import requests
from setting.settings import OLLAMA_BASE_URL, EMBED_MODEL

def embed_text(text):
    r = requests.post(
        f"{OLLAMA_BASE_URL}/api/embeddings",
        json={"model": EMBED_MODEL, "prompt": text}
    )
    return r.json()["embedding"]
