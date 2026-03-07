"""
Centralized embedding loader that switches between Ollama (local) and SentenceTransformer (production).

- Local development: set USE_OLLAMA=true to use Ollama embeddings (nomic-embed-text).
- Production (Render): set USE_OLLAMA=false to use SentenceTransformer (all-MiniLM-L6-v2).
"""

import os

USE_OLLAMA = os.getenv("USE_OLLAMA", "false").lower() == "true"


class EmbeddingLoader:
    """Lazily load and cache embedding model."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self.embedding_model = None   # ✅ CHANGE 1 (lazy loading)
        self.is_ollama = USE_OLLAMA

        if USE_OLLAMA:
            print("[EMBEDDING] Using Ollama embeddings (nomic-embed-text)...")
        else:
            print("[EMBEDDING] Using SentenceTransformer embeddings (all-MiniLM-L6-v2)...")

    @staticmethod
    def _create_ollama_embedder():
        """Create a callable Ollama embedder using requests."""
        from setting.settings import OLLAMA_BASE_URL, EMBED_MODEL

        def embed_text(text: str):
            import requests

            r = requests.post(
                f"{OLLAMA_BASE_URL}/api/embeddings",
                json={"model": EMBED_MODEL, "prompt": text},
                timeout=30,
            )
            r.raise_for_status()
            return r.json()["embedding"]

        return embed_text

    @staticmethod
    def _create_sentence_transformer():
        """Create a SentenceTransformer embedder."""
        from sentence_transformers import SentenceTransformer

        # ✅ CHANGE 2 (CPU optimized + low memory)
        model = SentenceTransformer(
            "sentence-transformers/all-MiniLM-L6-v2",
            device="cpu"
        )

        def embed_text(text: str):
            embedding = model.encode(text, convert_to_tensor=False)
            return embedding.tolist()

        return embed_text

    def embed(self, text: str):
        """Embed text using the configured model."""

        # ✅ CHANGE 3 (lazy load here instead of startup)
        if self.embedding_model is None:
            if self.is_ollama:
                self.embedding_model = self._create_ollama_embedder()
            else:
                self.embedding_model = self._create_sentence_transformer()

        return self.embedding_model(text)

    def get_chroma_embedding_function(self):
        """Get a ChromaDB-compatible embedding function."""

        # ✅ CHANGE 4 (avoid double model loading)
        from chromadb.utils import embedding_functions

        if self.is_ollama:
            from setting.settings import EMBED_MODEL, OLLAMA_BASE_URL

            return embedding_functions.OllamaEmbeddingFunction(
                url=OLLAMA_BASE_URL, model_name=EMBED_MODEL
            )
        else:

            class CustomEmbeddingFunction:
                name = "custom_sentence_transformer"
                def __call__(self, texts):
                    return [embed_text(t) for t in texts]

            return CustomEmbeddingFunction()


# Singleton instance
_loader = EmbeddingLoader()


def embed_text(text: str):
    """Embed text using the configured model."""
    return _loader.embed(text)


def get_embedding_function():
    """Get ChromaDB-compatible embedding function."""
    return _loader.get_chroma_embedding_function()