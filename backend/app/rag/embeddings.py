"""
ARGUS RAG Embeddings (Phase 4 - Section 11 & Section 37.1)

Provides a local, zero-marginal-cost embedding function using Chroma's
bundled all-MiniLM-L6-v2 ONNX model (384-dimensional dense vectors).
"""
import logging
from typing import List
from chromadb.utils import embedding_functions

logger = logging.getLogger(__name__)

# Shared local embedding function instance
_embedding_function = None


def get_embedding_function():
    """
    Returns a persistent local embedding function instance.
    Uses local ONNX execution to eliminate third-party API costs and latency.
    """
    global _embedding_function
    if _embedding_function is None:
        logger.info("Initializing local ONNX embedding model (all-MiniLM-L6-v2)...")
        _embedding_function = embedding_functions.DefaultEmbeddingFunction()
    return _embedding_function


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Embeds a list of texts into 384-dimensional dense vectors.
    """
    fn = get_embedding_function()
    return fn(texts)
