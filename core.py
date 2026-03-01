import os
import uuid
import time
import hashlib

# Basic imports for cloning repos, chunking, embeddings
from ingestion.cloner import clone_repository as clone_repo
from ingestion.loader import load_repository as load_repo
from ingestion.chunker import chunk_texts as chunk_text
from embeddings.embedder import embed_text
from retrieval.retriever import retrieve_chunks
from llm.llm import generate_answer
from vector.chroma import get_collection
from retrieval.hybrid import hybrid_retrieve_chunks

# Helpers for caching and file paths
from utils.files_utils import get_local_repo_path
from utils.cache_utils import make_cache_key

# Redis cache
from setting.redis_client import redis_client
REDIS_TTL = int(os.getenv("REDIS_TTL", 3600))

# Database for storing chunks
from sqlalchemy import insert, bindparam
from db.database import SessionLocal
from db.models.code_chunk import CodeChunk
from sqlalchemy.sql import func


def get_repo_name(repo_url: str) -> str:
    """Extract repo name from URL (e.g., 'my-repo' from github.com/user/my-repo.git)"""
    return repo_url.rstrip("/").split("/")[-1].replace(".git", "")


def ingest_from_git(repo_url, progress_callback=None):
    """Clone a repo, split code into chunks, embed them, and store in database."""
    print(f"Ingesting {repo_url}...")

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
    file_hashes_seen = set()  # Don't process same file twice
    
    # Convert repo name to UUID for consistent repo ID
    NAMESPACE_UUID = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')
    repo_id_uuid = uuid.uuid5(NAMESPACE_UUID, repo_name)
    
    # Process in batches to avoid slow one-by-one inserts
    BATCH_SIZE = 500
    pending_chunks = []
    pending_vectors = {"ids": [], "documents": [], "embeddings": [], "metadatas": []}

    for idx, file in enumerate(files):
        # Skip files we've already seen (same content)
        file_hash = hashlib.md5(file["content"].encode()).hexdigest()
        if file_hash in file_hashes_seen:
            print(f"\nSkipped (already have): {file['path']}")
            continue
        file_hashes_seen.add(file_hash)

        print(f"\nProcessing: {file['path']}")
        chunks = chunk_text(file["content"])

        for chunk_idx, chunk in enumerate(chunks):
            if not chunk.strip():
                continue

            print(f"  Embedding chunk {chunk_idx + 1}/{len(chunks)}...", end="\r")
            
            # Create vector embedding
            embedding = embed_text(chunk)
            chunk_uuid = uuid.uuid4()

            # Add to vector batch (Chroma expects string ids)
            pending_vectors["ids"].append(str(chunk_uuid))
            pending_vectors["documents"].append(chunk)
            pending_vectors["embeddings"].append(embedding)
            pending_vectors["metadatas"].append({
                "repo_id": repo_name,
                "file_path": file["path"],
                "commit_hash": "latest"
            })

            # Add to database batch as plain Python mappings; compute tsvector in SQL
            pending_chunks.append({
                "id": chunk_uuid,
                "repo_id": repo_id_uuid,
                "file_path": file["path"],
                "content": chunk,
                "commit_hash": "latest",
            })

            chunk_counter += 1

            # Save when batch is full (500 chunks)
            if len(pending_chunks) >= BATCH_SIZE:
                print(f"\n  Saving {len(pending_chunks)} chunks...")
                stmt = insert(CodeChunk.__table__).values(
                    id=bindparam('id'),
                    repo_id=bindparam('repo_id'),
                    file_path=bindparam('file_path'),
                    content=bindparam('content'),
                    content_tsv=func.to_tsvector('english', bindparam('content')),
                    commit_hash=bindparam('commit_hash'),
                )
                db.execute(stmt, pending_chunks)
                db.commit()
                pending_chunks = []
                
                # Also flush vectors in same batch
                if pending_vectors["ids"]:
                    collection.add(**pending_vectors)
                    pending_vectors = {"ids": [], "documents": [], "embeddings": [], "metadatas": []}

        # Progress update (UNCHANGED)
        if progress_callback:
            progress = int(((idx + 1) / total_files) * 80)
            progress_callback(progress)

    # ✅ Flush remaining items
    if pending_chunks:
        print(f"\n   💾 Flushing final {len(pending_chunks)} chunks to DB...")
        stmt = insert(CodeChunk.__table__).values(
            id=bindparam('id'),
            repo_id=bindparam('repo_id'),
            file_path=bindparam('file_path'),
            content=bindparam('content'),
            content_tsv=func.to_tsvector('english', bindparam('content')),
            commit_hash=bindparam('commit_hash'),
        )
        db.execute(stmt, pending_chunks)
        db.commit()
    
    if pending_vectors["ids"]:
        print(f"\n   💾 Flushing final {len(pending_vectors['ids'])} vectors...")
        collection.add(**pending_vectors)

    db.close()

    print("INGESTION COMPLETE | TOTAL CHUNKS:", chunk_counter)

    if progress_callback:
        progress_callback(100)

    return {
        "status": "ingestion_complete",
        "repo": repo_name,
        "chunks_indexed": chunk_counter
    }

def ask_question(repo_url, question):
    """Answer a question about a codebase using RAG pipeline."""
    repo_name = get_repo_name(repo_url)
    collection = get_collection(repo_name)

    # Try to get from cache first (if Redis configured)
    cache_key = make_cache_key(
        repo_id=repo_name,
        commit_hash="latest",
        question=question
    )

    # Cache hit? Return instantly
    t0 = time.time()
    cached_answer = redis_client.get(cache_key) if redis_client else None
    t1 = time.time()
    if cached_answer:
        elapsed_ms = (t1-t0)*1000
        print(f"Cache hit ({elapsed_ms:.1f}ms)")
        return {
            "answer": cached_answer,
            "source": "cache"
        }
    elapsed_ms = (t1-t0)*1000
    print(f"Cache miss ({elapsed_ms:.1f}ms)")

    # Find relevant code chunks
    print("Searching code...")
    t0 = time.time()
    chunks, sources = hybrid_retrieve_chunks(
        repo_id=repo_name,
        question=question,
        collection=collection
    )
    t1 = time.time()
    keyword_count = sources.get('keyword', 0)
    vector_count = sources.get('vector', 0)
    print(f"Found {len(chunks)} chunks ({keyword_count} keyword, {vector_count} vector) in {(t1-t0):.2f}s")

    # Trim context to prevent token overflow
    from setting.settings import MAX_CONTEXT_CHARS
    cumulative_chars = 0
    trimmed_chunks = []
    for chunk in chunks:
        if cumulative_chars + len(chunk) > MAX_CONTEXT_CHARS:
            print(f"Context limit reached - using {len(trimmed_chunks)} of {len(chunks)} chunks")
            break
        trimmed_chunks.append(chunk)
        cumulative_chars += len(chunk)
    trimmed_chunks = trimmed_chunks if trimmed_chunks else chunks[:1]

    # Generate answer using LLM
    t0 = time.time()
    answer = generate_answer(question, trimmed_chunks)
    t1 = time.time()
    print(f"Answer generated in {(t1-t0):.2f}s")
    
    # Save to cache for next time
    t0 = time.time()
    if redis_client:
        try:
            redis_client.setex(
                cache_key,
                REDIS_TTL,
                answer
            )
            elapsed_ms = (time.time()-t0)*1000
            print(f"Cached in {elapsed_ms:.1f}ms")
        except Exception as e:
            print(f"Cache save failed: {e}")

    # Determine which sources were used
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