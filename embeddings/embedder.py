# embeddings/embedder.py

import requests
from sentence_transformers import SentenceTransformer

from setting.settings import OLLAMA_BASE_URL, EMBED_MODEL, USE_OLLAMA


_sentence_model = None


def embed_text(text: str):

    if not text:
        return []

    # =============================
    # LOCAL → OLLAMA
    # =============================
    if USE_OLLAMA:

        try:

            r = requests.post(
                f"{OLLAMA_BASE_URL}/api/embeddings",
                json={
                    "model": EMBED_MODEL,
                    "prompt": text
                },
                timeout=10
            )

            r.raise_for_status()

            return r.json()["embedding"]

        except Exception as e:

            print(f"Ollama embedding error: {e}")
            return []

    # =============================
    # PRODUCTION → SENTENCE TRANSFORMER
    # =============================

    global _sentence_model

    if _sentence_model is None:

        print("Loading embedding model (all-MiniLM-L6-v2)...")

        _sentence_model = SentenceTransformer("all-MiniLM-L6-v2")

    embedding = _sentence_model.encode(text, normalize_embeddings=True)

    return embedding.tolist()