# Runbook: Ingestion Data Quality Drift and Encoding Corruption

- **Failure Type**: `DATA_QUALITY`
- **Severity**: Medium
- **Reference Incident / Source**: LlamaIndex Ingestion Post-Mortem "Binary Extraction Noise and PDF Encoding Artifacts"; DataOps Vector Store Quality Drift Case Study

## Incident Description
Ingested knowledge base documents contain corrupted text, malformed character encodings, OCR noise, or duplicate chunks. While system infrastructure remains functional, answer synthesis quality degrades due to dirty reference data.

## Symptoms
- Retrieved document text contains unexpected unicode replacement characters (`\ufffd`, ``), raw HTML tags, or unparsed markdown tables.
- `retrieval_score` shows mild drift (0.65–0.78), while `hallucination_score` rises moderately (0.10–0.25).
- Model outputs reference gibberish terms or hallucinated explanations based on corrupted textual fragments.
- Multiple identical chunks appear in top-k retrieval results due to deduplication failure.

## Root Cause
1. Faulty document parser processing un-normalized PDF, DOCX, or HTML sources with non-standard character encodings.
2. Ingestion pipeline missing document deduplication, leading to multiple embeddings of identical historical texts.
3. Outdated documentation that contradicts newer system versions co-existing in the vector index.

## Recommended Recovery
1. **Document Deduplication & Sanitization**: Execute text cleaner pass stripping binary artifacts, normalizing unicode to UTF-8, and hashing document contents to discard duplicates.
2. **Re-ingest Cleaned Corpus**: Re-run `scripts/ingest_knowledge.py` with the sanitized markdown files.
3. **Chunk Quality Filter**: Discard chunks with high special character ratios (> 15% non-alphanumeric) during ingestion.
