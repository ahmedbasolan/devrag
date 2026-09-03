# ADR-0001: Hybrid retrieval with BM25 + ChromaDB + RRF

## Status

Accepted

## Context

DevRAG needs to find relevant code chunks given a natural-language query. Two main approaches exist:

- **Keyword search (BM25)**: Fast, exact term matching. Fails on conceptual queries ("how does error handling work" won't match `try/except` blocks).
- **Dense vector search (embeddings)**: Understands semantics. Fails on specific identifiers (`BM25Okapi` won't match a query for "BM25").

Neither alone is sufficient for code search. Code queries mix specific identifiers with conceptual intent.

## Decision

Use **both** BM25 and ChromaDB (sentence-transformers embeddings), merged via **Reciprocal Rank Fusion (RRF)** with k=60.

- BM25 via `rank_bm25` (zero infrastructure, fast for <100k chunks)
- ChromaDB for persistent vector storage with metadata filtering
- RRF combines ranked lists by position, not score magnitude — no weight tuning required

## Consequences

- Retrieval quality is significantly better than either approach alone
- Two indexes to maintain (BM25 in-memory, ChromaDB on disk)
- RRF constant k=60 is standard from the original paper; no tuning needed
- `search_rrf` is the primary search method; `search_bm25` and `search_chroma` available for debugging
