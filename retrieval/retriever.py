# retrieval/retriever.py

from embeddings.embedder import embed_text


def retrieve_chunks(question, collection):

    query_embedding = embed_text(question)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=5
    )

    if not results or "documents" not in results:
        return []

    docs = results["documents"]

    if not docs or not docs[0]:
        return []

    return docs[0]# retrieval/retriever.py

from embeddings.embedder import embed_text


def retrieve_chunks(question, collection):

    query_embedding = embed_text(question)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=5
    )

    if not results or "documents" not in results:
        return []

    docs = results["documents"]

    if not docs or not docs[0]:
        return []

    return docs[0]