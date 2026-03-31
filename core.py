import os
import uuid
import time
import hashlib

from ingestion.cloner import clone_repository as clone_repo
from ingestion.loader import load_repository as load_repo
from ingestion.chunker import chunk_texts as chunk_text
from embeddings.embedder import embed_text, embed_texts_batch
from retrieval.retriever import retrieve_chunks
from llm.llm import generate_answer
from vector.chroma import get_collection
from retrieval.hybrid import hybrid_retrieve_chunks

from utils.files_utils import get_local_repo_path
from utils.cache_utils import make_cache_key

from setting.redis_client import redis_client
REDIS_TTL = int(os.getenv("REDIS_TTL", 3600))

from sqlalchemy import insert, bindparam
from db.database import SessionLocal
from db.models.code_chunk import CodeChunk
from sqlalchemy.sql import func

from setting.settings import CHROMA_PATH


def get_repo_name(repo_url: str) -> str:
    return repo_url.rstrip("/").split("/")[-1].replace(".git", "")


def ingest_from_git(repo_url, progress_callback=None):
    """Clone a repo, split code into chunks, embed them, and store in database."""
    print(f"Ingesting {repo_url}...")

    repo_name = get_repo_name(repo_url)
    collection = get_collection(repo_name)

    if collection.count() > 0:
        print(f"Repository '{repo_name}' already indexed ({collection.count()} chunks)")
        print("Skipping re-ingestion. Delete collection if you want to re-ingest.")
        if progress_callback:
            progress_callback(100)
        return {
            "status": "already_indexed",
            "repo": repo_name,
            "chunks_count": collection.count()
        }

    repo_path = get_local_repo_path(repo_url)

    print("CLONING REPO...")
    clone_repo(repo_url, repo_path)
    if progress_callback:
        progress_callback(5)

    print("LOADING FILES...")
    files = load_repo(repo_path)
    print("FILES FOUND:", len(files))
    if progress_callback:
        progress_callback(10)

    db = SessionLocal()

    chunk_counter = 0
    file_hashes_seen = set()

    NAMESPACE_UUID = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')
    repo_id_uuid = uuid.uuid5(NAMESPACE_UUID, repo_name)

    BATCH_SIZE = 1000
    EMBED_BATCH_SIZE = 64

    pending_chunks = []
    pending_vectors = {"ids": [], "documents": [], "embeddings": [], "metadatas": []}
    all_chunks_to_embed = []

    for idx, file in enumerate(files):
        file_hash = hashlib.md5(file["content"].encode()).hexdigest()
        if file_hash in file_hashes_seen:
            continue
        file_hashes_seen.add(file_hash)

        chunks = chunk_text(file["content"])
        for chunk in chunks:
            if chunk.strip():
                all_chunks_to_embed.append((chunk, file["path"]))

    print(f"Total chunks to embed: {len(all_chunks_to_embed)}")

    total_batches = (len(all_chunks_to_embed) + EMBED_BATCH_SIZE - 1) // EMBED_BATCH_SIZE

    for batch_idx in range(0, len(all_chunks_to_embed), EMBED_BATCH_SIZE):
        batch = all_chunks_to_embed[batch_idx: batch_idx + EMBED_BATCH_SIZE]
        batch_texts = [c[0] for c in batch]
        batch_paths = [c[1] for c in batch]

        current_batch_num = (batch_idx // EMBED_BATCH_SIZE) + 1
        print(f"Embedding batch {current_batch_num}/{total_batches} ({len(batch)} chunks)...", end="\r")

        embeddings = embed_texts_batch(batch_texts)

        for chunk, file_path, embedding in zip(batch_texts, batch_paths, embeddings):
            if embedding is None:
                continue

            chunk_uuid = uuid.uuid4()

            pending_vectors["ids"].append(str(chunk_uuid))
            pending_vectors["documents"].append(chunk)
            pending_vectors["embeddings"].append(embedding)
            pending_vectors["metadatas"].append({
                "repo_id": repo_name,
                "file_path": file_path,
                "commit_hash": "latest"
            })

            pending_chunks.append({
                "id": chunk_uuid,
                "repo_id": repo_id_uuid,
                "file_path": file_path,
                "content": chunk,
                "commit_hash": "latest",
            })

            chunk_counter += 1

        if len(pending_chunks) >= BATCH_SIZE:
            print(f"\nSaving {len(pending_chunks)} chunks...")
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

            if pending_vectors["ids"]:
                collection.add(**pending_vectors)
                pending_vectors = {"ids": [], "documents": [], "embeddings": [], "metadatas": []}

        # progress runs from 10% to 95% during embedding
        if progress_callback:
            progress = 10 + int((current_batch_num / total_batches) * 85)
            progress_callback(min(progress, 95))

    if pending_chunks:
        print(f"\nFlushing final {len(pending_chunks)} chunks to DB...")
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
        print(f"\nFlushing final {len(pending_vectors['ids'])} vectors...")
        collection.add(**pending_vectors)

    db.close()

    print(f"\nINGESTION COMPLETE | TOTAL CHUNKS: {chunk_counter}")

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

    print(f"Collection: '{collection.name}' | Chunks: {collection.count()} | Path: {CHROMA_PATH}")

    cache_key = make_cache_key(
        repo_id=repo_name,
        commit_hash="latest",
        question=question
    )

    t0 = time.time()
    cached_answer = redis_client.get(cache_key) if redis_client else None
    t1 = time.time()
    if cached_answer:
        print(f"Cache hit ({(t1-t0)*1000:.1f}ms)")
        return {
            "answer": cached_answer,
            "source": "cache"
        }
    print(f"Cache miss ({(t1-t0)*1000:.1f}ms)")

    print("Searching code...")
    t0 = time.time()
    chunks, sources = hybrid_retrieve_chunks(
        repo_id=repo_name,
        question=question,
        collection=collection
    )
    t1 = time.time()
    print(f"Found {len(chunks)} chunks ({sources.get('keyword', 0)} keyword, {sources.get('vector', 0)} vector) in {(t1-t0):.2f}s")

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

    t0 = time.time()
    answer = generate_answer(question, trimmed_chunks)
    t1 = time.time()
    print(f"Answer generated in {(t1-t0):.2f}s")

    if redis_client and answer and not answer.startswith("Sorry,"):
        try:
            redis_client.setex(cache_key, REDIS_TTL, answer)
            print(f"Cached in {(time.time()-t0)*1000:.1f}ms")
        except Exception as e:
            print(f"Cache save failed: {e}")

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