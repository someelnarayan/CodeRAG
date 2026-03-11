import os
import requests
from setting.settings import USE_OLLAMA, OLLAMA_BASE_URL, EMBED_MODEL

JINA_API_KEY = os.getenv("JINA_API_KEY")


def embed_text(text: str):

    if not text:
        return []

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

            return r.json()["embedding"]

        except Exception as e:

            print(f"Ollama embedding error: {e}")

            return []

    # -------------------------
    # PRODUCTION → JINA API
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
                "input": text
            },
            timeout=10
        )

        r.raise_for_status()

        data = r.json()

        return data["data"][0]["embedding"]

    except Exception as e:

        print(f"Jina embedding error: {e}")

        return []