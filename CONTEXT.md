# DevRAG — Domain Context

## What this project is

DevRAG is a **local Retrieval-Augmented Generation system** for developers. It ingests code repositories and markdown documentation, then answers technical questions about them in plain English. It runs entirely on your machine with zero cost.

## Core concepts

| Term | Meaning |
|------|---------|
| **Code Chunk** | A parsed unit of code or documentation — a function, class, method, module docstring, or markdown section. The atomic unit of retrieval. |
| **Hybrid Retrieval** | Combining two search strategies (BM25 keyword + dense vector) to find relevant code chunks. Neither alone is sufficient. |
| **BM25 (Sparse)** | Keyword-based search. Fast, exact term matching. Good for specific function names, error messages, imports. |
| **ChromaDB (Dense)** | Vector-based search using embeddings. Understands semantic meaning. Good for conceptual questions ("how does error handling work"). |
| **Reciprocal Rank Fusion (RRF)** | Merges results from BM25 and ChromaDB into a single ranked list. Uses rank position (not score magnitude) to combine. Constant k=60. |
| **Embedding Model** | `sentence-transformers/all-MiniLM-L6-v2` — converts text to 384-dimensional vectors. 80MB, runs on CPU. |
| **AST Parser** | Python's `ast` module extracts exact function/class boundaries from `.py` files. More reliable than regex. |
| **Markdown Parser** | Splits `.md` files on headings into context-aware chunks with structural metadata. |
| **Ingestion** | The process of reading a directory, parsing files into chunks, and indexing them into BM25 + ChromaDB. |
| **Generation** | Taking retrieved chunks + a user query, sending to Gemini Flash to produce a plain-English answer. |
| **Citation** | A source reference (`file > name (L start-end`) shown alongside answers so users can verify. |

## Architecture overview

```
User Query
    │
    ▼
┌─────────────────────┐
│  Hybrid Retrieval   │
│  ┌───────┐ ┌──────┐ │
│  │ BM25  │ │Chroma│ │
│  └───┬───┘ └──┬───┘ │
│      └───┬────┘     │
│      RRF Merge      │
└─────────┬───────────┘
          │ top-k chunks
          ▼
┌─────────────────────┐
│  Gemini Flash       │
│  (plain English)    │
└─────────┬───────────┘
          │
          ▼
      Answer + Citations
```

## Components

| File | Role |
|------|------|
| `src/parser.py` | Ingestion: AST parsing (Python) + markdown parsing → `CodeChunk` objects |
| `src/retriever.py` | Indexing + search: BM25 index, ChromaDB vector store, RRF fusion |
| `src/app.py` | Streamlit UI: sidebar indexing, chat input, answer display, source citations |
| `tests/eval_rag.py` | Evaluation: Hit Rate @5, @10, MRR against sample queries |
| `stress_test.py` | Stress testing: 22 queries including edge cases |

## Design principles

1. **Zero-cost** — no paid APIs required (Gemini free tier, local embeddings, local vector DB)
2. **Privacy-first** — everything runs locally except optional Gemini calls
3. **Simple infrastructure** — no Elasticsearch, no GPU, no complex deployment
4. **Hybrid retrieval** — neither keyword nor semantic search alone is enough for code

## User persona

A developer who wants to understand a codebase quickly — either their own or one they're evaluating. They ask questions in plain English and get answers with source citations. They may not be familiar with the specific code being queried.

## Current state

- Working prototype with Streamlit UI
- Python AST parsing + markdown parsing
- BM25 + ChromaDB + RRF retrieval
- Gemini Flash generation with fallback
- Basic evaluation suite (5 queries)
- Docker support
- No git history yet
- No tests beyond evaluation
