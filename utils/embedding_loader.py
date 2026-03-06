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

        if USE_OLLAMA:
            print("[EMBEDDING] Using Ollama embeddings (nomic-embed-text)...")
            try:
                import requests
                from setting.settings import OLLAMA_BASE_URL

                # Test connection to Ollama
                health_url = f"{OLLAMA_BASE_URL}/api/tags"
                try:
                    requests.get(health_url, timeout=2)
                    print(f"[EMBEDDING] Ollama is available at {OLLAMA_BASE_URL}")
                except Exception as e:
                    print(
                        f"[EMBEDDING] WARNING: Ollama not available at {OLLAMA_BASE_URL}: {e}"
                    )

                # Use simple requests-based embedder for Ollama
                self.embedding_model = self._create_ollama_embedder()
                self.is_ollama = True

            except Exception as e:
                print(f"[EMBEDDING] Failed to load Ollama embeddings: {e}")
                print("[EMBEDDING] Falling back to SentenceTransformer...")
                self.embedding_model = self._create_sentence_transformer()
                self.is_ollama = False
        else:
            print("[EMBEDDING] Using SentenceTransformer embeddings (all-MiniLM-L6-v2)...")
            self.embedding_model = self._create_sentence_transformer()
            self.is_ollama = False

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
        try:
            from sentence_transformers import SentenceTransformer

            model = SentenceTransformer("all-MiniLM-L6-v2")

            def embed_text(text: str):
                embedding = model.encode(text, convert_to_tensor=False)
                return embedding.tolist()

            return embed_text

        except ImportError:
            raise ImportError(
                "SentenceTransformer not installed. Install with: "
                "pip install sentence-transformers"
            )

    def embed(self, text: str):
        """Embed text using the configured model."""
        return self.embedding_model(text)

    def get_chroma_embedding_function(self):
        """Get a ChromaDB-compatible embedding function."""
        if self.is_ollama:
            # For Ollama, ChronaDB will call the embedder with default settings
            from chromadb.utils import embedding_functions

            from setting.settings import EMBED_MODEL, OLLAMA_BASE_URL

            return embedding_functions.OllamaEmbeddingFunction(
                url=OLLAMA_BASE_URL, model_name=EMBED_MODEL
            )
        else:
            # For SentenceTransformer
            from chromadb.utils import embedding_functions

            return embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2"
            )


# Singleton instance
_loader = EmbeddingLoader()


def embed_text(text: str):
    """Embed text using the configured model."""
    return _loader.embed(text)


def get_embedding_function():
    """Get ChromaDB-compatible embedding function."""
    return _loader.get_chroma_embedding_function()
