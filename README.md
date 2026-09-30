# DevRAG

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-orange)](https://streamlit.io)
[![RAG](https://img.shields.io/badge/RAG-Hybrid%20BM25%20+%20ChromaDB-informational)](https://github.com/ahmedbasolan/devrag)
[![CI](https://github.com/ahmedbasolan/devrag/actions/workflows/ci.yml/badge.svg)](https://github.com/ahmedbasolan/devrag/actions/workflows/ci.yml)

⚡ Ask questions about any codebase. Get answers with source citations. Zero-cost, privacy-first, runs entirely on your machine.

## Quickstart

```bash
git clone https://github.com/ahmedbasolan/devrag.git
cd devrag/devrag
pip install -r requirements.txt
streamlit run src/app.py
```

Open [http://localhost:8501](http://localhost:8501). On first run the app indexes its own source code (takes a few seconds), so you can start asking questions immediately.

## Features

- **AST-based Python parsing** — Exact function/class boundaries, not regex
- **Hybrid RAG** — BM25 sparse + ChromaDB dense embeddings + Reciprocal Rank Fusion
- **Code-aware tokenizer** — Handles snake_case, camelCase, dotted names, string literals
- **Multi-provider** — Gemini, Groq, OpenAI with graceful fallback
- **Smart file-level boosting** — RRF enhanced with file frequency and ADR keyword detection
- **Beautiful Streamlit UI** — Dark theme, animations, expandable result cards
- **Built-in evaluation** — 21 queries with Hit Rate@k and MRR metrics
- **Stress tested** — Edge cases, adversarial inputs, repeated queries

## License

MIT — See LICENSE file for details.
