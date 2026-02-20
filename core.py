from ingestion.cloner import clone_repository as clone_repo
from ingestion.loader import load_repository as load_repo
from ingestion.chunker import chunk_texts as chunk_text
from embeddings.embedder import embed_text
from retrieval.retriever import retrieve_chunks
from llm.llm import generate_answer
from vector.chroma import get_collection

# ✅ NEW IMPORT (SINGLE SOURCE OF TRUTH)
from utils.files_utils import get_local_repo_path


# 🔹 Repo name extract (same)
def get_repo_name(repo_url):
    return repo_url.rstrip("/").split("/")[-1].replace(".git", "")


# 🔹 SMART INGESTION (FIXED PATH)
def ingest_from_git(repo_url, progress_callback=None):
    repo_name = get_repo_name(repo_url)
    collection = get_collection(repo_name)

    # 🔁 Skip if already indexed in Chroma
    if collection.count() > 0:
        return {
            "status": "already_indexed",
            "repo": repo_name
        }

    # ✅ FIX: FORCE CLONE PATH
    repo_path = get_local_repo_path(repo_url)

    # clone_repo MUST respect this path
    clone_repo(repo_url, repo_path)

    files = load_repo(repo_path)

    total_files = len(files)
    all_chunks, all_embeddings = [], []

    for idx, file in enumerate(files):
        chunks = chunk_text(file["content"])
        embeddings = [embed_text(chunk) for chunk in chunks]

        all_chunks.extend(chunks)
        all_embeddings.extend(embeddings)

        # 🔥 Progress (0–80%)
        if progress_callback:
            progress = int(((idx + 1) / total_files) * 80)
            progress_callback(progress)

    collection.add(
        ids=[f"id_{i}" for i in range(len(all_chunks))],
        documents=all_chunks,
        embeddings=all_embeddings
    )

    # 🔥 Final update
    if progress_callback:
        progress_callback(100)

    return {
        "status": "ingestion_complete",
        "repo": repo_name,
        "chunks_indexed": len(all_chunks)
    }


# 🔹 CHAT LOGIC (unchanged)
def ask_question(repo_url, question):
    repo_name = get_repo_name(repo_url)
    collection = get_collection(repo_name)

    chunks = retrieve_chunks(question, collection)
    answer = generate_answer(question, chunks)
    return answer
from ingestion.cloner import clone_repository as clone_repo
from ingestion.loader import load_repository as load_repo
from ingestion.chunker import chunk_texts as chunk_text
from embeddings.embedder import embed_text
from retrieval.retriever import retrieve_chunks
from llm.llm import generate_answer
from vector.chroma import get_collection

# ✅ NEW IMPORT (SINGLE SOURCE OF TRUTH)
from utils.files_utils import get_local_repo_path


# 🔹 Repo name extract (same)
def get_repo_name(repo_url):
    return repo_url.rstrip("/").split("/")[-1].replace(".git", "")


# 🔹 SMART INGESTION (FIXED PATH)
def ingest_from_git(repo_url, progress_callback=None):
    repo_name = get_repo_name(repo_url)
    collection = get_collection(repo_name)

    # 🔁 Skip if already indexed in Chroma
    if collection.count() > 0:
        return {
            "status": "already_indexed",
            "repo": repo_name
        }

    # ✅ FIX: FORCE CLONE PATH
    repo_path = get_local_repo_path(repo_url)

    # clone_repo MUST respect this path
    clone_repo(repo_url, repo_path)

    files = load_repo(repo_path)

    total_files = len(files)
    all_chunks, all_embeddings = [], []

    for idx, file in enumerate(files):
        chunks = chunk_text(file["content"])
        embeddings = [embed_text(chunk) for chunk in chunks]

        all_chunks.extend(chunks)
        all_embeddings.extend(embeddings)

        # 🔥 Progress (0–80%)
        if progress_callback:
            progress = int(((idx + 1) / total_files) * 80)
            progress_callback(progress)

    collection.add(
        ids=[f"id_{i}" for i in range(len(all_chunks))],
        documents=all_chunks,
        embeddings=all_embeddings
    )

    # 🔥 Final update
    if progress_callback:
        progress_callback(100)

    return {
        "status": "ingestion_complete",
        "repo": repo_name,
        "chunks_indexed": len(all_chunks)
    }


# 🔹 CHAT LOGIC (unchanged)
def ask_question(repo_url, question):
    repo_name = get_repo_name(repo_url)
    collection = get_collection(repo_name)

    chunks = retrieve_chunks(question, collection)
    answer = generate_answer(question, chunks)
    return answer