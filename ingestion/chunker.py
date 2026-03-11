# ingestion/chunker.py

from setting.settings import CHUNK_SIZE, CHUNK_OVERLAP


def chunk_texts(text):

    if not text:
        return []

    chunks = []

    start = 0
    text_length = len(text)

    while start < text_length:

        end = start + CHUNK_SIZE
        chunk = text[start:end]

        chunks.append(chunk)

        start += CHUNK_SIZE - CHUNK_OVERLAP

        if start <= 0:
            break

    return chunks