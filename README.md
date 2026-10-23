# ⚡ DevRAG

Ask questions about any codebase. Get answers with source citations.

DevRAG is a local RAG system that ingests Python code and markdown docs, then answers technical questions in plain English. Zero-cost, privacy-first, runs entirely on your machine.

## Example Questions

Here's what you can ask DevRAG about its own codebase:

| Question | What You Learn |
|----------|----------------|
| *How does user authentication work?* | JWT token flow, login/register endpoints, password hashing |
| *What is the cache invalidation strategy?* | TTL-based with event-driven invalidation, per-entity clearing |
| *How are database migrations handled?* | MigrationManager with up/down SQL, JSON state tracking |
| *How does the rate limiting work?* | Per-IP sliding window decorator, 100 req/min default |
| *What payment gateways are supported?* | Stripe and PayPal via PaymentService abstraction |
| *How does the product search work?* | Full-text search across name, description, category |

DevRAG explains **what** the code does and **why** it matters — not how every line works.

## Quickstart

### 1. Clone & Install

```bash
git clone https://github.com/ahmedbasolan/devrag.git
cd devrag/devrag
pip install -r requirements.txt
```

### 2. Run

```bash
streamlit run src/app.py
```

Open [http://localhost:8501](http://localhost:8501). On first run the app indexes its own source code (takes a few seconds), so you can start asking questions immediately.

### 3. Index Your Own Code

Enter any Python project path in the sidebar and click **Index**. Ask questions about your own codebase.

### 4. Docker (alternative)

```bash
docker compose up app
```

### 5. Smart Answers (optional)

For AI-powered explanations instead of raw code snippets, choose your provider:

**Option A: Enter your API key in the UI (Recommended)**
- Select your provider (Gemini, Groq, or OpenAI)
- Enter your API key — your key stays in your browser only

| Provider | Cost | Get Key |
|----------|------|---------|
| **Gemini** | Free tier | [Google AI Studio](https://aistudio.google.com/apikey) |
| **Groq** | Free tier | [Groq Console](https://console.groq.com/keys) |
| **OpenAI** | Pay per use | [OpenAI Platform](https://platform.openai.com/api-keys) |

**Option B: Use a .env file**
```bash
cp .env.example .env
# Add your API key for your chosen provider
```

## How It Works

```
Your Question
     │
     ▼
┌─────────────┐   ┌─────────────┐
│    BM25     │   │  ChromaDB   │
│  (keyword)  │   │  (semantic) │
└──────┬──────┘   └──────┬──────┘
       └────────┬────────┘
                │
         Reciprocal Rank Fusion
                │
                ▼
        Top Source Chunks
                │
                ▼
     Gemini Flash (optional)
                │
                ▼
     Plain English Answer
        + Citations
```

**Hybrid retrieval** combines keyword search (fast, exact) with semantic search (understands meaning). Results from both are merged using Reciprocal Rank Fusion — no training required.

## Evaluation

```bash
python tests/eval_rag.py --repo-path /path/to/your/repo
```

Built-in evaluation suite with 21 queries covering functional, cross-file, and design decision questions. Metrics: Hit Rate @5, Hit Rate @10, MRR.

## Project Structure

```
devrag/
├── src/
│   ├── parser.py       # AST + Markdown parsing → CodeChunk objects
│   ├── retriever.py    # BM25 + ChromaDB + RRF hybrid search
│   └── app.py          # Streamlit UI + Gemini generation
├── tests/
│   └── eval_rag.py     # 21-query evaluation suite
├── mock_data/          # Sample codebase for demos
├── .chroma/            # Pre-built index (ships ready to use)
├── requirements.txt
├── docker-compose.yml
└── Dockerfile
```

## Design Decisions

| Choice | Why |
|--------|-----|
| **AST parsing** | Exact function/class boundaries. Regex breaks on decorators and nesting. |
| **BM25 + ChromaDB** | Keyword search catches exact names; semantic search catches concepts. Neither alone is enough. |
| **Reciprocal Rank Fusion** | Simple, no training, combines sparse/dense signals. k=60 from the original paper. |
| **Gemini Flash** | Free tier sufficient for code Q&A. Falls back gracefully without API key. |
| **Local embeddings** | 80MB model, no GPU, no API calls. Privacy-first. |

## License

MIT
