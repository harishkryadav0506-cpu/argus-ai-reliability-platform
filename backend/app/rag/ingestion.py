"""
ARGUS Knowledge Ingestion (Phase 4 - Section 11 & Section 37.2-37.3)

Parses reviewed markdown runbooks, chunks them with structural metadata preservation,
and upserts them into ChromaDB using the local embedding model.
"""
import glob
import logging
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional
import chromadb

from app.rag.knowledge_base import get_runbooks_collection

logger = logging.getLogger(__name__)


def parse_runbook_markdown(filepath: str) -> Dict[str, Any]:
    """
    Parses a runbook markdown document and extracts structured headers and body sections.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    filename = os.path.basename(filepath)

    # Extract title
    title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else filename

    # Extract Failure Type
    ft_match = re.search(r"\*\*Failure Type\*\*:\s*`?([A-Z_]+)`?", content)
    failure_type = ft_match.group(1).strip() if ft_match else "UNKNOWN"

    # Extract Severity
    sev_match = re.search(r"\*\*Severity\*\*:\s*([A-Za-z]+)", content)
    severity = sev_match.group(1).strip() if sev_match else "Medium"

    # Extract Reference Incident / Source
    ref_match = re.search(r"\*\*Reference Incident / Source\*\*:\s*(.+)$", content, re.MULTILINE)
    reference = ref_match.group(1).strip() if ref_match else ""

    # Split into logical sections based on markdown headers '## '
    raw_sections = re.split(r"\n(?=##\s+)", content)
    sections = []

    # First chunk is the header summary
    header_chunk = raw_sections[0].strip()
    if header_chunk:
        sections.append({
            "section": "Overview",
            "text": header_chunk,
        })

    # Remaining sections
    for sec in raw_sections[1:]:
        sec = sec.strip()
        if not sec:
            continue
        header_line = sec.split("\n", 1)[0].replace("##", "").strip()
        sections.append({
            "section": header_line,
            "text": sec,
        })

    return {
        "filename": filename,
        "title": title,
        "failure_type": failure_type,
        "severity": severity,
        "reference": reference,
        "sections": sections,
        "full_text": content,
    }


def ingest_runbooks(
    runbooks_dir: Optional[str] = None,
    collection: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Ingests all reviewed markdown runbooks from runbooks_dir into ChromaDB.
    """
    target_collection = collection or get_runbooks_collection()

    candidates: List[str] = []
    env_dir = os.getenv("RUNBOOKS_DIR")
    if env_dir:
        candidates.append(env_dir)
    if runbooks_dir and runbooks_dir not in candidates and runbooks_dir != "data/runbooks":
        candidates.append(runbooks_dir)
    for p in ["data/runbooks", "../data/runbooks", "backend/data/runbooks"]:
        if p not in candidates:
            candidates.append(p)
    try:
        repo_root_cand = None
        for parent in Path(__file__).resolve().parents:
            cand = parent / "data" / "runbooks"
            if cand.is_dir():
                repo_root_cand = str(cand)
                break
        if not repo_root_cand and len(Path(__file__).resolve().parents) > 3:
            repo_root_cand = str(Path(__file__).resolve().parents[3] / "data" / "runbooks")
        if repo_root_cand and repo_root_cand not in candidates:
            candidates.append(repo_root_cand)
    except Exception:
        pass

    resolved_dir: Optional[str] = None
    files: List[str] = []
    for cand in candidates:
        if cand and os.path.exists(cand):
            md_files = glob.glob(os.path.join(cand, "*.md"))
            if md_files:
                resolved_dir = cand
                files = md_files
                break

    if not files:
        logger.warning(
            "No markdown runbooks found in %s (tried: %s)",
            runbooks_dir or "data/runbooks",
            ", ".join(candidates),
        )
        return {"documents_ingested": 0, "chunks_created": 0}

    all_ids: List[str] = []
    all_documents: List[str] = []
    all_metadatas: List[Dict[str, Any]] = []

    for filepath in files:
        doc = parse_runbook_markdown(filepath)
        doc_id = os.path.splitext(doc["filename"])[0]

        # 1. Full contextual document chunk (high overview relevance)
        summary_text = (
            f"Runbook: {doc['title']}\n"
            f"Failure Type: {doc['failure_type']} (Severity: {doc['severity']})\n"
            f"Reference: {doc['reference']}\n\n"
            f"{doc['full_text']}"
        )
        all_ids.append(f"{doc_id}_full")
        all_documents.append(summary_text)
        all_metadatas.append({
            "source": doc["filename"],
            "title": doc["title"],
            "failure_type": doc["failure_type"],
            "severity": doc["severity"],
            "section": "Full Document",
        })

        # 2. Granular section chunks (Symptoms, Root Cause, Recovery)
        for idx, sec in enumerate(doc["sections"]):
            chunk_text = (
                f"Runbook: {doc['title']} [{doc['failure_type']}]\n"
                f"Section: {sec['section']}\n\n"
                f"{sec['text']}"
            )
            all_ids.append(f"{doc_id}_sec_{idx}")
            all_documents.append(chunk_text)
            all_metadatas.append({
                "source": doc["filename"],
                "title": doc["title"],
                "failure_type": doc["failure_type"],
                "severity": doc["severity"],
                "section": sec["section"],
            })

    # Batch upsert into ChromaDB
    target_collection.upsert(
        ids=all_ids,
        documents=all_documents,
        metadatas=all_metadatas,
    )

    logger.info(
        "Successfully ingested %d runbooks (%d chunks) into ChromaDB.",
        len(files),
        len(all_ids),
    )

    return {
        "documents_ingested": len(files),
        "chunks_created": len(all_ids),
        "filenames": [os.path.basename(f) for f in files],
    }
