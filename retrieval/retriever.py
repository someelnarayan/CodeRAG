from embeddings.embedder import embed_text

def retrieve_chunks(question, collection):
    query_embedding = embed_text(question)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=5
    )
    return results["documents"][0]
