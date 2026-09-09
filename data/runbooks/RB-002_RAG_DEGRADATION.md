# Runbook: RAG Retrieval Quality Degradation and Context Hallucination

- **Failure Type**: `RAG_DEGRADATION`
- **Severity**: High
- **Reference Incident / Source**: LlamaIndex Issue #7829 "Top-K Context Fragmentation Causing Answer Hallucinations"; Vector DB Case Study "Embedding Model Drift & Semantic Degradation in Production RAG"

## Incident Description
The RAG pipeline continues returning chunks, but the retrieved chunks exhibit poor semantic alignment with the user/system query. As a result, answer relevance plummets, hallucination metrics surge, and context token stuffing inflates cost.

## Symptoms
- `retrieval_score` collapses below 0.60 (baseline: 0.92).
- `hallucination_score` climbs above 0.35 (baseline: 0.03).
- `token_usage` expands by 150%–250% as the agent requests higher top-k chunks to compensate for low similarity.
- Qualitative evaluation detects fabricated facts unsupported by reference documentation.

## Root Cause
1. Query embedding generated using a model version incompatible with documents stored in the index (embedding model mismatch or dimension drift).
2. Poor chunk boundary splitting that broke apart critical relational context (e.g. splitting a code block or table across chunk limits).
3. Index pollution with uncleaned or redundant boilerplate text that saturates cosine similarity rankings.

## Recommended Recovery
1. **Reindex Vector Store**: Trigger `reindex_vector_store` tool to regenerate embeddings with the standard embedding model (`all-MiniLM-L6-v2`).
2. **Dynamic Similarity Filter**: Enforce a minimum cosine similarity threshold (e.g., score >= 0.70); discard chunks below this score rather than passing noise to the generator.
3. **Switch to Hybrid Search**: Blend dense vector similarity with sparse BM25 keyword matching to preserve exact token hits when semantic embeddings drift.
