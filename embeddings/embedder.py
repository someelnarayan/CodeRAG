import os
import requests
from setting.settings import USE_OLLAMA, OLLAMA_BASE_URL, EMBED_MODEL

JINA_API_KEY = os.getenv("JINA_API_KEY")


def embed_text(text: str):

    if not text:
        return None

    # -------------------------
    # LOCAL → OLLAMA
    # -------------------------
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

            data = r.json()

            if "embedding" not in data:
                return None

            return data["embedding"]

        except Exception as e:

            print(f"Ollama embedding error: {e}")

            return None

    # -------------------------
    # PRODUCTION → JINA
    # -------------------------

    try:

        r = requests.post(
            "https://api.jina.ai/v1/embeddings",
            headers={
                "Authorization": f"Bearer {JINA_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "jina-embeddings-v2-base-en",
                "input": [text]     # FIX: list input required
            },
            timeout=10
        )

        r.raise_for_status()

        data = r.json()

        return data["data"][0]["embedding"]

    except Exception as e:

        print(f"Jina embedding error: {e}")

        return None