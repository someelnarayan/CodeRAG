from setting.settings import CHUNK_SIZEE as CHUNK_SIZE, CHUNK_OVERLAP

def chunk_texts(text):
    chunks = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunks.append(text[start:end])
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks
