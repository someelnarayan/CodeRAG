import os

# ==============================
# AI Models
# ==============================

LLM_MODEL = "llama3.1:8b-instruct-q4_K_M"
EMBED_MODEL = "nomic-embed-text"

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# ==============================
# LLM STRATEGY
# ==============================

# Production mode: Groq only
USE_GROQ = os.getenv("USE_GROQ", "true").lower() in ("1","true","yes")
USE_OLLAMA = os.getenv("USE_OLLAMA", "false").lower() in ("1","true","yes")

# ==============================
# Vector database
# ==============================

CHROMA_PATH = "./data/chroma_db"
COLLECTION_NAME = "codebase_chunks"

# ==============================
# Chunking configuration
# ==============================

CHUNK_SIZE = 800
CHUNK_OVERLAP = 100

# ==============================
# File hash storage
# ==============================

HASH_DIR = "./data/repo_hashes"

# ==============================
# Context limits
# ==============================

MAX_CONTEXT_TOKENS = int(os.getenv("MAX_CONTEXT_TOKENS", 2000))

# rough char estimate
MAX_CONTEXT_CHARS = MAX_CONTEXT_TOKENS * 4

# ==============================
# Retrieval configuration
# ==============================

MAX_RETRIEVAL_CHUNKS = int(os.getenv("MAX_RETRIEVAL_CHUNKS", 5))

# ==============================
# Ollama health
# ==============================

OLLAMA_HEALTH_URL = os.getenv(
    "OLLAMA_HEALTH_URL",
    f"{OLLAMA_BASE_URL}/api/tags"
)

# ==============================
# Timeouts
# ==============================

OLLAMA_TIMEOUT_SECONDS = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", 5))

REQUEST_TIMEOUT_SECONDS = int(os.getenv("REQUEST_TIMEOUT_SECONDS", 30))

INGESTION_TIMEOUT_MINUTES = int(os.getenv("INGESTION_TIMEOUT_MINUTES", 60))