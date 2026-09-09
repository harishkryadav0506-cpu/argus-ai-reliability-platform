"""
ARGUS CLI — Ingest Knowledge Base (Phase 4)

CLI command to parse reviewed markdown runbooks from data/runbooks/
and populate the ChromaDB vector database with local embeddings.

Usage:
    python scripts/ingest_knowledge.py
"""
import os
import sys

# Ensure backend root is on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.rag.ingestion import ingest_runbooks
from app.rag.knowledge_base import get_runbooks_collection


def main():
    print("=" * 60)
    print("ARGUS — Knowledge Base Ingestion")
    print("=" * 60)

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    runbooks_dir = os.path.join(repo_root, "data", "runbooks")

    print(f"Loading reviewed runbooks from: {runbooks_dir}")
    collection = get_runbooks_collection()
    stats = ingest_runbooks(runbooks_dir=runbooks_dir, collection=collection)

    print("\n--- Ingestion Results ---")
    print(f"Documents Ingested: {stats['documents_ingested']}")
    print(f"Chunks Created:     {stats['chunks_created']}")
    print("\nRunbook Files:")
    for fname in stats.get("filenames", []):
        print(f"  - {fname}")

    print("\n[OK] Knowledge Base successfully ingested and ready for retrieval.")


if __name__ == "__main__":
    main()
