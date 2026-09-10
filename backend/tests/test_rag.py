"""
Phase 4 tests — RAG Knowledge Base, Ingestion, and Semantic Retrieval.

Run with: pytest backend/tests/test_rag.py -v -s
"""
import pytest
from app.rag.knowledge_base import (
    get_runbooks_collection,
    get_historical_incidents_collection,
)
from app.rag.ingestion import ingest_runbooks
from app.rag.retriever import retrieve


@pytest.fixture(scope="module", autouse=True)
def setup_knowledge_base():
    """Ensure runbooks are ingested once for RAG tests."""
    ingest_runbooks(runbooks_dir="data/runbooks")


def test_runbooks_collection_populated():
    collection = get_runbooks_collection()
    count = collection.count()
    assert count >= 10, f"Expected at least 10 chunks in runbooks collection, found {count}"


def test_historical_incidents_empty_at_bootstrap():
    """Per Section 37.4: Historical incidents store must start empty and accumulate naturally without fake seeds."""
    incidents_col = get_historical_incidents_collection()
    count = incidents_col.count()
    if count > 0:
        data = incidents_col.get()
        for meta in data.get("metadatas", []):
            assert meta.get("source") in ["historical_incident_lifecycle", "postmortem_agent"], (
                "Per Section 37.4, historical_incidents must not contain pre-seeded fake items; "
                f"found source: {meta.get('source')}"
            )
    else:
        assert count == 0


def test_retrieval_output_schema_and_scores():
    results = retrieve("high latency and thread pool starvation", k=3)
    assert len(results) > 0

    for item in results:
        assert "document" in item
        assert "chunk" in item
        assert "source" in item
        assert "relevance_score" in item
        assert "metadata" in item

        assert isinstance(item["document"], str)
        assert isinstance(item["chunk"], str)
        assert isinstance(item["source"], str)
        assert isinstance(item["relevance_score"], float)
        assert 0.0 <= item["relevance_score"] <= 1.0
        assert isinstance(item["metadata"], dict)


@pytest.mark.parametrize(
    "query, expected_source",
    [
        (
            "model timeout and JSONDecodeError on truncated structured output",
            "RB-001_LLM_FAILURE.md",
        ),
        (
            "embedding dimension drift causing hallucinations and low similarity in RAG",
            "RB-002_RAG_DEGRADATION.md",
        ),
        (
            "HNSW index lock failure and zero results from vector store",
            "RB-003_RETRIEVAL_FAILURE.md",
        ),
        (
            "agent repeating identical tool execution in infinite circular loop",
            "RB-008_AGENT_LOOP.md",
        ),
        (
            "runaway token usage and cost explosion in prompt chain",
            "RB-007_COST_SPIKE.md",
        ),
    ],
)
def test_retrieve_known_failure_signatures(query, expected_source):
    results = retrieve(query=query, k=3)
    assert len(results) > 0

    top_sources = [r["source"] for r in results]
    assert expected_source in top_sources, (
        f"Query '{query}' failed to retrieve expected runbook '{expected_source}'. Top sources: {top_sources}"
    )

    top_match = results[0]
    print(f"\nQuery: {query}")
    print(f"Top Retrieved: {top_match['source']} (Relevance: {top_match['relevance_score']:.4f})")
    print(f"Document: {top_match['document']}")
    print(f"Excerpt: {top_match['chunk'][:150]}...")
