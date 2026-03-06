"""Embedding function that delegates to utils.embedding_loader.

This module provides backward compatibility. Use utils.embedding_loader directly
for new code.
"""

from utils.embedding_loader import embed_text

__all__ = ["embed_text"]
