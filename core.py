import os
import uuid
import time

# ===============================
# Ingestion imports (UNCHANGED)
# ===============================
from ingestion.cloner import clone_repository as clone_repo
from ingestion.loader import load_repository as load_repo
from ingestion.chunker import chunk_texts as chunk_text
from embeddings.embedder import embed_text
from retrieval.retriever import retrieve_chunks
from llm.llm import generate_answer
from vector.chroma import get_collection
from retrieval.hybrid import hybrid_retrieve_chunks

# ===============================
# Utils (UNCHANGED)
# ===============================
from utils.files_utils import get_local_repo_path
from utils.cache_utils import make_cache_key

# ===============================
# Redis (UNCHANGED)
# ===============================
from setting.redis_client import redis_client

REDIS_TTL = int(os.getenv("REDIS_TTL", 3600))

# ===============================
# 🔥 PostgreSQL (NEW – REQUIRED)
# ===============================
from db.database import SessionLocal
from db.models.code_chunk import CodeChunk
from sqlalchemy.sql import func


# ===============================
# Helper: Repo name (UNCHANGED)
# ===============================
def get_repo_name(repo_url: str) -> str:
    return repo_url.rstrip("/").split("/")[-1].replace(".git", "")


# ===============================
# INGESTION LOGIC (MINIMAL CHANGE)
# ===============================
def ingest_from_git(repo_url, progress_callback=None):
    print("INGESTION STARTED")  # 🔥 visibility

    repo_name = get_repo_name(repo_url)
    collection = get_collection(repo_name)

    # ⚠️ TEMP: skip disabled so fresh ingest always runs
    # if collection.count() > 0:
    #     return {
    #         "status": "already_indexed",
    #         "repo": repo_name
    #     }

    repo_path = get_local_repo_path(repo_url)

    print("CLONING REPO...")
    clone_repo(repo_url, repo_path)

    print("LOADING FILES...")
    files = load_repo(repo_path)
    print("FILES FOUND:", len(files))

    db = SessionLocal()

    total_files = len(files)
    chunk_counter = 0
    
    # Convert repo name to UUID (consistent across runs)
    NAMESPACE_UUID = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')
    repo_id_uuid = uuid.uuid5(NAMESPACE_UUID, repo_name)

    for idx, file in enumerate(files):
        print(f"\n📄 Processing: {file['path']}")
        chunks = chunk_text(file["content"])

        for chunk_idx, chunk in enumerate(chunks):
            if not chunk.strip():
                continue

            print(f"   ↳ Embedding chunk {chunk_idx + 1}/{len(chunks)}...", end="\r")
            
            embedding = embed_text(chunk)

            # ✅ Vector store (UNCHANGED BEHAVIOR)
            collection.add(
                ids=[str(uuid.uuid4())],
                documents=[chunk],
                embeddings=[embedding],
                metadatas=[{
                    "repo_id": repo_name,
                    "file_path": file["path"],
                    "commit_hash": "latest"
                }]
            )

            # 🔥 PostgreSQL keyword store (NEW)
            db.add(CodeChunk(
                repo_id=repo_id_uuid,  # ✅ FIX: Convert to UUID
                file_path=file["path"],
                content=chunk,
                content_tsv=func.to_tsvector("english", chunk),
                commit_hash="latest"
            ))

            chunk_counter += 1

        # Progress update (UNCHANGED)
        if progress_callback:
            progress = int(((idx + 1) / total_files) * 80)
            progress_callback(progress)

    print("COMMITTING TO DATABASE...")
    db.commit()
    db.close()

    print("INGESTION COMPLETE | TOTAL CHUNKS:", chunk_counter)

    if progress_callback:
        progress_callback(100)

    return {
        "status": "ingestion_complete",
        "repo": repo_name,
        "chunks_indexed": chunk_counter
    }


# ===============================
# ASK QUESTION (UNCHANGED LOGIC)
# ===============================
def ask_question(repo_url, question):
    repo_name = get_repo_name(repo_url)
    collection = get_collection(repo_name)

    # 🔴 REDIS: cache key (UNCHANGED)
    cache_key = make_cache_key(
        repo_id=repo_name,
        commit_hash="latest",
        question=question
    )

    # 🔴 REDIS: GET (unchanged)
    t0 = time.time()
    cached_answer = redis_client.get(cache_key)
    t1 = time.time()
    print(f"CACHE CHECK: hit={bool(cached_answer)} took={(t1-t0):.3f}s")
    if cached_answer:
        return {
            "answer": cached_answer,
            "source": "cache"
        }

    # 🔴 CACHE MISS → HYBRID PIPELINE (measure retrieval time)
    print("RETRIEVAL: starting hybrid_retrieve_chunks()")
    t0 = time.time()
    chunks, sources = hybrid_retrieve_chunks(
        repo_id=repo_name,
        question=question,
        collection=collection
    )
    t1 = time.time()
    print(f"RETRIEVAL: found {len(chunks)} chunks (keyword={sources.get('keyword')}, vector={sources.get('vector')}), took={(t1-t0):.3f}s")

    # 🔴 GENERATION: measure LLM latency
    print("LLM: generating answer (this may call Groq or local model)")
    t0 = time.time()
    answer = generate_answer(question, chunks)
    t1 = time.time()
    print(f"LLM: done, took={(t1-t0):.3f}s")

    # 🔴 REDIS: SET with TTL (unchanged)
    t0 = time.time()
    try:
        redis_client.setex(
            cache_key,
            REDIS_TTL,
            answer
        )
    except Exception as e:
        print("REDIS SET ERROR:", repr(e))
    t1 = time.time()
    print(f"CACHE SET: took={(t1-t0):.3f}s")

    # Decide source label: cache -> 'cache', if any keyword results -> 'hybrid',
    # else if only vector results -> 'vector'.
    if cached_answer:
        source_label = "cache"
    else:
        if sources.get("keyword", 0) > 0:
            source_label = "hybrid"
        elif sources.get("vector", 0) > 0:
            source_label = "vector"
        else:
            source_label = "hybrid"

    return {
        "answer": answer,
        "source": source_label
    }