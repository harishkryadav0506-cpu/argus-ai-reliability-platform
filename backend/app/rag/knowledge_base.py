"""
ARGUS Vector Knowledge Base (Phase 4 - Sections 11, 25 & 37.4)

Manages ChromaDB persistent vector storage collections:
1. `runbooks`: Curated runbooks and troubleshooting documentation
2. `historical_incidents`: Real resolved incidents accumulated over time (empty at bootstrap)
"""
import os
import logging
from typing import Optional
import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import get_settings
from app.rag.embeddings import get_embedding_function

logger = logging.getLogger(__name__)
settings = get_settings()

RUNBOOKS_COLLECTION_NAME = "runbooks"
HISTORICAL_INCIDENTS_COLLECTION_NAME = "historical_incidents"

_client: Optional[chromadb.ClientAPI] = None


def get_chroma_client(persist_directory: Optional[str] = None) -> chromadb.ClientAPI:
    """
    Returns a singleton Chroma persistent client.
    """
    global _client
    target_path = persist_directory or settings.VECTOR_DB_PATH
    os.makedirs(target_path, exist_ok=True)

    if _client is None:
        logger.info("Initializing ChromaDB PersistentClient at %s", target_path)
        _client = chromadb.PersistentClient(
            path=target_path,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _client


def get_runbooks_collection(client: Optional[chromadb.ClientAPI] = None):
    """
    Returns the runbooks collection configured with local embeddings.
    """
    c = client or get_chroma_client()
    embedding_fn = get_embedding_function()
    return c.get_or_create_collection(
        name=RUNBOOKS_COLLECTION_NAME,
        embedding_function=embedding_fn,
        metadata={"description": "Operational troubleshooting runbooks for AI failures"},
    )


def get_historical_incidents_collection(client: Optional[chromadb.ClientAPI] = None):
    """
    Returns the historical incidents collection.
    Starts empty per Section 37.4 and bootstraps from resolved incidents.
    """
    c = client or get_chroma_client()
    embedding_fn = get_embedding_function()
    return c.get_or_create_collection(
        name=HISTORICAL_INCIDENTS_COLLECTION_NAME,
        embedding_function=embedding_fn,
        metadata={"description": "Real historical incidents resolved by ARGUS"},
    )
