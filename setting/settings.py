import os

LLM_MODEL = "llama3.1"
EMBED_MODEL = "nomic-embed-text"
OLLAMA_BASE_URL = "http://localhost:11434"

# Use GROQ by default; can be overridden with environment variable USE_GROQ=false
USE_GROQ = os.getenv("USE_GROQ", "true").lower() in ("1", "true", "yes")

CHROMA_PATH = "./data/chroma_db"
COLLECTION_NAME = "codebase_chunks"

CHUNK_SIZEE = 800
CHUNK_OVERLAP = 100

HASH_DIR = "./data/repo_hashes"

