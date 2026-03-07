def retrieve_chunks(question, collection):
    results = collection.query(
        query_texts=[question],
        n_results=5
    )
    return results["documents"][0]
