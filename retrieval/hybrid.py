from retrieval.keyword import keyword_search
from retrieval.retriever import retrieve_chunks


def hybrid_retrieve_chunks(repo_id, question, collection):
    """Return (results, sources) where results is a list of chunk texts
    and sources is a dict with counts for 'keyword' and 'vector'.
    """
    keyword_chunks = keyword_search(repo_id, question)
    vector_chunks = retrieve_chunks(question, collection)

    results = [k.content for k in keyword_chunks]
    results.extend(vector_chunks)

    sources = {
        "keyword": len(keyword_chunks),
        "vector": len(vector_chunks)
    }

    return results[:6], sources