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

Put the project under this `devrag/` folder (for example `git clone <your-repo> devrag/my-repo`), enter its path in the sidebar and click **Index**. The app refuses paths outside its own folder, so a hosted copy can't be pointed at the server's files.

Python and Markdown files are indexed. Tests (`test_*.py`, `*_test.py`, `conftest.py`, and anything under a `tests/` or `test/` directory) are left out by default, because they name the same functions as the code they test and outrank it.

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

**On codebases DevRAG was not built against** (`tests/eval_external.py`). These are the numbers that test "any codebase": other repositories pinned to a commit, indexed exactly as the app indexes your folder, with each answer file picked from the code by hand. A README ranking first counts as a miss. Each cell is Hit@5 · Hit@10 · MRR.

| Set | Questions | Original | Code-first ranking | + tests left out (now) |
|-----|----------:|----------|--------------------|------------------------|
| [customs-copilot](https://github.com/ahmedbasolan/customs-copilot) @719704c, **held-out** | 14 | — | 0.86 · 0.93 · 0.51 | **0.93 · 0.93 · 0.61** |
| [Sift](https://github.com/ahmedbasolan/Sift) @0fa5bcd, **held-out** | 14 | — | 0.86 · 0.93 · 0.57 | **0.93 · 1.00 · 0.65** |
| [motor-claims-triage](https://github.com/ahmedbasolan/motor-claims-triage) @036d5b5, held-out before | 14 | 0.14 · 0.43 · 0.08 | 0.71 · 0.86 · 0.23 | 0.79 · 1.00 · 0.36 |
| [dubai-property-bot](https://github.com/ahmedbasolan/dubai-property-bot) @5580c90, dev | 12 | 0.25 · 0.42 · 0.17 | 0.58 · 0.83 · 0.53 | 0.75 · 0.83 · 0.54 |

The customs-copilot and Sift questions were committed before tests were left out, then scored once before and once after. The two layouts cover the usual places tests live: beside the code (customs-copilot) and in a `tests/` directory (Sift). motor-claims-triage was the held-out set for code-first ranking and has now been scored a second time, so it is no longer unseen, but nothing was tuned on it. The dev set was used while building code-first ranking, so its numbers are optimistic. All sets are small: one question moves Hit@5 by 0.07–0.08.

```bash
git clone https://github.com/ahmedbasolan/motor-claims-triage ../motor-claims-triage
git -C ../motor-claims-triage checkout 036d5b5
python tests/eval_external.py tests/external/motor_claims_triage.json --repo-path ../motor-claims-triage
```

CI runs all four sets on every push and pull request, against each set's committed `.results.json`. The build fails if Hit@5 drops or MRR falls more than 0.02, and the log names the questions that ranked worse. A change that moves the scores commits the new results (`--out`), so any lowered baseline shows up in the diff.

**Clone folder name.** Each chunk is indexed with its folder and file name, and for a file at the root of a repo that folder used to be whatever the repo was cloned into: the same files scored Hit@5 0.93 as `customs-copilot/` and 1.00 as `customs_copilot/`. Paths are now taken from the folder being indexed, and all four sets score the same under either name. Hit@5 did not move on any set. Eight questions moved one place, and one dropped out of the top 10 on the dev set ("How are community investment scores weighted?", 10th before), which is why its Hit@10 fell from 0.92 to 0.83. The last column includes this fix.

**Tests left out.** Before this change a test file ranked above the answer on every one of the four repos, and ranked first on 1 to 4 questions per repo: a test names the same functions as the code it checks. With tests left out, none does. Across the 54 questions, 25 moved up, 28 stayed where they were, and 1 moved down: on the dev set, "How are community market reports generated from DuckDB?" went from 1st to 4th. Removing tests changes word statistics for the whole corpus, and `rag.py` now edges out `build_reports.py` there.

**Code-first ranking.** Docs used to win questions about code. A README chunk sits mid-table in both the keyword and the semantic ranking, Reciprocal Rank Fusion sums the two, and a file-frequency boost then multiplied every chunk of any file split into many chunks. On the dev set the semantic search alone ranked the answering file 1st or 2nd for 7 of 12 questions, and the merged result put it 4th to 17th. Now:

- Markdown counts half as much in the merge, except for "why / decision" questions, where design records are the answer. Taking this out drops dev MRR from 0.52 to 0.32 in the same run; it is the one change with a clear effect.
- No file takes more than 2 of the leading results; its further chunks follow other files' results instead of being dropped.
- Top-level code outside functions and classes (settings, constants, SQL) is indexed. `config.py` in the dev repo was 34 lines of which only the 2-line docstring was searchable.
- The file path and class name are indexed with each chunk, so a method in `bayut_provider.py` matches "Bayut provider".
- Re-indexing replaces the previous corpus. Chunk ids were positions written into a persistent collection, so indexing a smaller repo, or restarting the app, left old chunks searchable. That is also why MRR on the built-in suite used to drift between runs.

The last three have no clear effect on these small sets (removing any one moves dev Hit@5 or MRR by a single question either way); they stay because each fixes a failure that can be shown directly, and each has a test.

**Known limitation.** Docs are now what outranks the answer. On motor-claims-triage, whose README explains each module in prose, `README.md` ranks first on all 14 questions and the answer is usually 2nd or 3rd (MRR 0.36). Markdown already counts half in the merge; a doc that restates the code in the question's own words still wins.

**On DevRAG's own source** (`tests/eval_rag.py`, 21 questions, test files excluded):

| Metric | Original | Code-first ranking | Now, with this README |
|--------|----------|--------------------|-----------------------|
| Hit@5 | 85.7% (18/21) | 95.2% (20/21) | 95.2% (20/21) |
| Hit@10 | 90.5% (19/21) | 100% (21/21) | 100% (21/21) |
| MRR | 0.45–0.67 between runs | 0.85 | **0.49** |

The drop is the limitation above, caused by this file. The suite indexes this README, and its Evaluation section explains how retrieval works, so it ranks first for questions such as "How are code chunks indexed into ChromaDB?". The same retriever scores 0.85 on the commit before the section was first rewritten, 0.54 on that commit, and 0.49 with the further explanation added here. Leaving tests out does not move it (0.537 → 0.540 on the same README), since this suite already excluded test files. Any edit to this README changes the number, and CI runs the suite on every push but does not fail on a drop, which is why the first fall went unnoticed. The sets on other repos above now gate CI instead; this one stays ungated because editing this file moves it. This suite indexes the code it was written alongside, so it is a regression check rather than evidence the retriever works on other code.

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
