import os
import time
import requests
from setting.settings import USE_OLLAMA, OLLAMA_BASE_URL, EMBED_MODEL

JINA_API_KEY = os.getenv("JINA_API_KEY")

JINA_BATCH_SIZE = 64   # Jina supports up to 128, 64 is safe
MAX_RETRIES = 3
RETRY_DELAY = 2        # seconds between retries


def embed_text(text: str):
    """Embed a single text. Used for query embedding at search time."""
    if not text:
        return None

    if USE_OLLAMA:
        try:
            r = requests.post(
                f"{OLLAMA_BASE_URL}/api/embeddings",
                json={"model": EMBED_MODEL, "prompt": text},
                timeout=10
            )
            r.raise_for_status()
            data = r.json()
            if "embedding" not in data:
                return None
            return data["embedding"]
        except Exception as e:
            print(f"Ollama embedding error: {e}")
            return None

    # Jina single text (reuse batch function)
    results = embed_texts_batch([text])
    return results[0] if results else None


def embed_texts_batch(texts: list[str]) -> list:
    """
    Embed a list of texts in one API call.
    Returns list of embeddings (None for failed items).
    """
    if not texts:
        return []

    if USE_OLLAMA:
        # Ollama has no batch endpoint — run sequentially but fast (local, no timeout)
        embeddings = []
        for text in texts:
            embeddings.append(embed_text(text))
        return embeddings

    # -------------------------
    # JINA BATCH
    # -------------------------
    for attempt in range(MAX_RETRIES):
        try:
            r = requests.post(
                "https://api.jina.ai/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {JINA_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "jina-embeddings-v2-base-en",
                    "input": texts      # ✅ send whole batch at once
                },
                timeout=30              # ✅ longer timeout for batches
            )
            r.raise_for_status()
            data = r.json()
            # Jina returns results in order
            return [item["embedding"] for item in data["data"]]

        except Exception as e:
            print(f"Jina batch embedding error (attempt {attempt+1}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)

    # All retries failed — return None for each text
    print(f"❌ All retries failed for batch of {len(texts)} texts")
    return [None] * len(texts)