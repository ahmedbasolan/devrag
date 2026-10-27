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

A question counts as a hit when the file that answers it is in the top 5 (Hit@5) or top 10 (Hit@10); MRR rewards ranking it first.

**On codebases DevRAG was not built against** (`tests/eval_external.py`). These are the numbers that test "any codebase": two other repositories pinned to a commit, indexed exactly as the app indexes your folder (Python and Markdown, tests included), with each answer file picked from the code by hand. A README ranking first counts as a miss.

| Set | Questions | Before | After |
|-----|----------:|--------|-------|
| [motor-claims-triage](https://github.com/ahmedbasolan/motor-claims-triage) @036d5b5, **held-out** | 14 | Hit@5 0.14 · Hit@10 0.43 · MRR 0.08 | **Hit@5 0.71 · Hit@10 0.86 · MRR 0.23** |
| [dubai-property-bot](https://github.com/ahmedbasolan/dubai-property-bot) @5580c90, dev | 12 | Hit@5 0.25 · Hit@10 0.42 · MRR 0.17 | Hit@5 0.58 · Hit@10 0.83 · MRR 0.53 |

The held-out questions were committed before any retrieval change and run once after it; the dev set was used while making the change, so its numbers are optimistic. Both sets are small: one question moves Hit@5 by 0.07–0.08.

```bash
git clone https://github.com/ahmedbasolan/motor-claims-triage ../motor-claims-triage
git -C ../motor-claims-triage checkout 036d5b5
python tests/eval_external.py tests/external/motor_claims_triage.json --repo-path ../motor-claims-triage
```

**What changed.** Docs used to win questions about code. A README chunk sits mid-table in both the keyword and the semantic ranking, Reciprocal Rank Fusion sums the two, and a file-frequency boost then multiplied every chunk of any file split into many chunks. On the dev set the semantic search alone ranked the answering file 1st or 2nd for 7 of 12 questions, and the merged result put it 4th to 17th. Now:

- Markdown counts half as much in the merge, except for "why / decision" questions, where design records are the answer. Taking this out drops dev MRR from 0.52 to 0.32 in the same run; it is the one change with a clear effect.
- No file takes more than 2 of the leading results; its further chunks follow other files' results instead of being dropped.
- Top-level code outside functions and classes (settings, constants, SQL) is indexed. `config.py` in the dev repo was 34 lines of which only the 2-line docstring was searchable.
- The file path and class name are indexed with each chunk, so a method in `bayut_provider.py` matches "Bayut provider".
- Re-indexing replaces the previous corpus. Chunk ids were positions written into a persistent collection, so indexing a smaller repo, or restarting the app, left old chunks searchable. That is also why MRR on the built-in suite used to drift between runs.

The last three have no clear effect on these small sets (removing any one moves dev Hit@5 or MRR by a single question either way); they stay because each fixes a failure that can be shown directly, and each has a test.

**Known limitation.** On the held-out set the answer is usually 3rd to 5th rather than 1st (MRR 0.23): the README and test files still rank above it. The app indexes a user's tests, and a test names the same functions as the code it checks. Leaving tests out of the app's default corpus is the obvious next change, measured on a new held-out set.

**On DevRAG's own source** (`tests/eval_rag.py`, 21 questions, test files excluded):

| Metric | Before | After (identical across 3 runs) |
|--------|--------|------|
| Hit@5 | 85.7% (18/21) | 95.2% (20/21) |
| Hit@10 | 90.5% (19/21) | 100% (21/21) |
| MRR | 0.45–0.67 between runs | 0.85 |

This suite indexes the code it was written alongside, so it is a regression check rather than evidence the retriever works on other code. CI runs it on every push.

## Project Structure

```
devrag/
├── src/
│   ├── parser.py       # AST + Markdown parsing → CodeChunk objects
│   ├── retriever.py    # BM25 + ChromaDB + RRF hybrid search
│   └── app.py          # Streamlit UI + Gemini generation
├── tests/
│   ├── eval_rag.py     # 21-query regression suite on DevRAG's own source
│   ├── eval_external.py # retrieval on other repos, pinned (tests/external/)
│   └── test_*.py       # unit tests (pytest)
├── mock_data/          # Sample codebase for demos
├── .chroma/            # Vector index, built on first run (not in git)
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
