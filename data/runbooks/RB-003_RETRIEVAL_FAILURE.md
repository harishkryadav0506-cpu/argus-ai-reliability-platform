# Runbook: Vector Store Retrieval Outage and HNSW Index Failure

- **Failure Type**: `RETRIEVAL_FAILURE`
- **Severity**: High
- **Reference Incident / Source**: ChromaDB Issue #1240 "HNSW Index Read Lock Timeout Under Concurrency"; Vector DB Post-Mortem "Silent Zero-Result Queries on Segment Corruption"

## Incident Description
The vector retrieval component fails completely to return documents or throws connection/timeout errors. Unlike `RAG_DEGRADATION` where chunks are returned with low similarity, `RETRIEVAL_FAILURE` represents total unavailability or silent empty result sets from the vector database.

## Symptoms
- `retrieval_score` drops to 0.0 or near 0.30.
- Vector query latency exceeds timeout threshold (> 5.0s) or raises `ConnectionRefusedError` / `DatabaseLockedError`.
- System logs report `IndexNotFoundError`, `HNSW index segment corrupted`, or empty chunk arrays.
- Downstream diagnosis and recovery agents operate completely blind without historical runbooks.

## Root Cause
1. Vector database process crash or out-of-memory termination.
2. File lock contention in local vector store (e.g. SQLite read/write lock contention in ChromaDB).
3. HNSW graph segment corruption following an abrupt system reboot or ungraceful shutdown.

## Recommended Recovery
1. **Restart Vector Service**: Call `restart_service(service_name="vector_db")` to release dead locks and reset connections.
2. **Rebuild Index from Persistent Store**: Trigger `reindex_vector_store` from the source markdown documents in `data/runbooks/`.
3. **Fallback to In-Memory Cache**: Switch retriever to in-memory cached runbooks and rule-based emergency dictionary while index is rebuilt.
