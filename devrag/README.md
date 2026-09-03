# :gear: DevRAG

A developer-focused local RAG system that ingests code repositories and markdown docs to answer technical queries. Zero-cost, privacy-first, runs entirely on your machine.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DevRAG                                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐    ┌──────────────────────────────────────────┐   │
│  │  Streamlit   │    │          Hybrid Retrieval Engine         │   │
│  │    (UI)      │    │                                          │   │
│  │              │    │  ┌────────────┐    ┌─────────────────┐   │   │
│  │  Search Bar  │───>│  │   BM25     │    │   ChromaDB      │   │   │
│  │  Results     │<───│  │ (Sparse)   │    │   + Embeddings  │   │   │
│  │  Citations   │    │  │            │    │   (Dense)       │   │   │
│  └──────┬───────┘    │  └─────┬──────┘    └───────┬─────────┘   │   │
│         │            │        │                    │             │   │
│         │            │        └────────┬───────────┘             │   │
│         │            │                 │                         │   │
│         │            │        ┌────────▼────────┐               │   │
│         │            │        │  Reciprocal     │               │   │
│         │            │        │  Rank Fusion    │               │   │
│         │            │        │  (RRF Merge)    │               │   │
│         │            │        └────────┬────────┘               │   │
│         │            │                 │                         │   │
│         │            │        ┌────────▼────────┐               │   │
│         │            │        │  Gemini Flash   │               │   │
│         │            │        │  (Generation)   │               │   │
│         │            │        └─────────────────┘               │   │
│         │            └──────────────────────────────────────────┘   │
│         │                                                           │
│  ┌──────▼───────────────────────────────────────────────────────┐   │
│  │                   Data Ingestion Layer                        │   │
│  │                                                               │   │
│  │  ┌─────────────────┐    ┌─────────────────┐                  │   │
│  │  │   AST Parser    │    │  Markdown Parser │                  │   │
│  │  │   (Python)      │    │  (Structural)    │                  │   │
│  │  └────────┬────────┘    └────────┬─────────┘                  │   │
│  │           │                      │                           │   │
│  │           └──────────┬───────────┘                           │   │
│  │                      │                                       │   │
│  │              ┌───────▼────────┐                              │   │
│  │              │  Code Chunks   │                              │   │
│  │              │  (Structured)  │                              │   │
│  │              └────────────────┘                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                   Evaluation Layer                            │   │
│  │                                                               │   │
│  │  Hit Rate @5 │ Hit Rate @10 │ MRR │ 5 Sample Queries        │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Quickstart

### 1. Clone & Install

```bash
git clone <your-repo-url>
cd devrag
pip install -r requirements.txt
```

### 2. Configure (optional)

```bash
cp .env.example .env
# Edit .env with your Gemini API key (free tier works)
```

### 3. Run

```bash
streamlit run src/app.py
```

Open http://localhost:8501. Paste any local repo path in the sidebar, click **Index Directory**, then ask questions.

### 4. Docker (alternative)

```bash
docker compose up app
```

## Evaluation

Run the built-in evaluation suite:

```bash
python tests/eval_rag.py --repo-path /path/to/your/repo
```

Output includes Hit Rate @5, Hit Rate @10, and MRR across 5 sample queries.

## Project Structure

```
devrag/
├── src/
│   ├── parser.py       # AST + Markdown parsing
│   ├── retriever.py    # BM25 + ChromaDB + RRF
│   └── app.py          # Streamlit UI + Gemini generation
├── tests/
│   └── eval_rag.py     # RAG evaluation metrics
├── docs/
├── .chroma/            # Persisted vector DB
├── requirements.txt
├── docker-compose.yml
├── Dockerfile
├── .env.example
└── .gitignore
```

## Design Trade-offs

| Decision | Rationale |
|----------|-----------|
| **AST over regex** | Python's `ast` module produces exact function/class boundaries. Regex-based parsing breaks on nested definitions and decorators. |
| **rank_bm25 over Elasticsearch** | Zero infrastructure. BM25Okapi is fast enough for local repos (<100k chunks). Elasticsearch would add complexity for marginal gains. |
| **ChromaDB over FAISS** | ChromaDB provides persistent storage and metadata filtering out-of-the-box. FAISS is faster but requires custom persistence. |
| **Reciprocal Rank Fusion** | Simple to implement, no training required. Combines sparse/dense signals without learning a weighting function. k=60 is the standard constant from the original RRF paper. |
| **Gemini over local LLMs** | Gemini 2.0 Flash free tier is sufficient for code Q&A. Local LLMs require GPU and add deployment complexity. Falls back gracefully without API key. |
| **sentence-transformers/all-MiniLM-L6-v2** | 80MB model, fast inference, strong code understanding. No GPU required. |
| **Streamlit over Gradio** | Better for multi-page apps with session state. Chat input API is cleaner for conversational RAG. |

## Dependencies

All zero-cost:

- `sentence-transformers` - Local embeddings (all-MiniLM-L6-v2)
- `chromadb` - Persistent vector store
- `rank_bm25` - BM25 sparse retrieval
- `streamlit` - Web UI
- `google-generativeai` - Gemini API (free tier)
- Python stdlib `ast` - Code parsing

## License

MIT
