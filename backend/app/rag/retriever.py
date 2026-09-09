"""
ARGUS RAG Retriever (Phase 4 - Section 11)

Implements semantic search over the ChromaDB runbooks collection.
Returns the exact structure specified in Section 11:
- document (document title / source)
- chunk (text excerpt)
- source (filename / reference)
- relevance_score (normalized similarity score [0, 1])
- metadata (structured headers, failure_type, severity)
"""
import logging
from typing import Any, Dict, List, Optional
import chromadb

from app.rag.knowledge_base import get_runbooks_collection

logger = logging.getLogger(__name__)


def retrieve(
    query: str,
    k: int = 3,
    failure_type_filter: Optional[str] = None,
    collection: Optional[Any] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieves the top-k most relevant runbook chunks for a given diagnostic query.
    Returns:
        List of dicts containing: document, chunk, source, relevance_score, metadata.
    """
    target_collection = collection or get_runbooks_collection()

    where_filter = None
    if failure_type_filter:
        where_filter = {"failure_type": failure_type_filter}

    try:
        results = target_collection.query(
            query_texts=[query],
            n_results=k,
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )
    except Exception as e:
        logger.error("ChromaDB query failed: %s", e)
        return []

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    retrieved_items: List[Dict[str, Any]] = []

    for i in range(len(documents)):
        chunk_text = documents[i]
        meta = metadatas[i] if i < len(metadatas) else {}
        distance = distances[i] if i < len(distances) else 1.0

        # Convert distance to normalized relevance score [0.0, 1.0]
        # In Chroma, default cosine distance ranges from 0.0 (identical) to 2.0 (opposite)
        # If L2 squared, 1.0 / (1.0 + distance) is a robust smooth normalization.
        relevance_score = round(max(0.0, min(1.0, 1.0 - (distance / 2.0))), 4)

        retrieved_items.append({
            "document": meta.get("title", meta.get("source", "Unknown Document")),
            "chunk": chunk_text,
            "source": meta.get("source", "unknown"),
            "relevance_score": relevance_score,
            "metadata": meta,
        })

    return retrieved_items
