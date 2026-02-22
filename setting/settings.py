import os

# AI Models
LLM_MODEL = "llama3.1"
EMBED_MODEL = "nomic-embed-text"
OLLAMA_BASE_URL = "http://localhost:11434"

# Which LLM to use: Groq (cloud) or Ollama (local)
USE_GROQ = os.getenv("USE_GROQ", "true").lower() in ("1", "true", "yes")

# Vector database
CHROMA_PATH = "./data/chroma_db"
COLLECTION_NAME = "codebase_chunks"

# How to split code into chunks
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100

# Store file hashes to avoid re-processing same files
HASH_DIR = "./data/repo_hashes"

# Limit context size sent to LLM
# Most models work best with 2k-4k tokens
MAX_CONTEXT_TOKENS = int(os.getenv("MAX_CONTEXT_TOKENS", 2000))
MAX_CONTEXT_CHARS = MAX_CONTEXT_TOKENS * 4  # rough estimate

# How many code chunks to pass to LLM
# Too many = slow + confused answers
# Too few = missing context
MAX_RETRIEVAL_CHUNKS = int(os.getenv("MAX_RETRIEVAL_CHUNKS", 5))

# Ollama health check URL
OLLAMA_HEALTH_URL = os.getenv("OLLAMA_HEALTH_URL", f"{OLLAMA_BASE_URL}/api/tags")

# If Ollama takes longer than this, switch to Groq
OLLAMA_TIMEOUT_SECONDS = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", 5))

# General API timeouts
REQUEST_TIMEOUT_SECONDS = int(os.getenv("REQUEST_TIMEOUT_SECONDS", 30))
INGESTION_TIMEOUT_MINUTES = int(os.getenv("INGESTION_TIMEOUT_MINUTES", 60))
