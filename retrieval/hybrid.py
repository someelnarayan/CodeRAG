# retrieval/hybrid.py

from retrieval.keyword import keyword_search
from retrieval.retriever import retrieve_chunks
from setting.settings import MAX_RETRIEVAL_CHUNKS


def hybrid_retrieve_chunks(repo_id, question, collection):
    """
    Hybrid retrieval:
    1. Keyword search (Postgres)
    2. Vector search (Chroma)
    """

    keyword_chunks = keyword_search(repo_id, question)
    vector_chunks = retrieve_chunks(question, collection)

    results = []

    # Keyword results
    for k in keyword_chunks:
        if k and k.content:
            results.append(k.content)

    # Vector results
    for v in vector_chunks:
        if v:
            results.append(v)

    sources = {
        "keyword": len(keyword_chunks),
        "vector": len(vector_chunks)
    }

    return results[:MAX_RETRIEVAL_CHUNKS], sources