# Contributing to DevRAG

## Getting Started

```bash
cd devrag
pip install -r requirements.txt
pip install -e ".[dev]"
```

## Running the App

```bash
streamlit run src/app.py
```

## Running Tests

```bash
cd devrag
pytest tests/ -v
```

## Running Evaluation

```bash
python tests/eval_rag.py --repo-path mock_data
```

## Linting & Formatting

```bash
cd devrag
ruff check .
ruff format .
```

## Adding a New Feature

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Make your changes
3. Add tests for new functionality
4. Ensure all tests pass: `pytest tests/ -v`
5. Ensure linting passes: `ruff check . && ruff format --check .`
6. Commit and open a Pull Request

## Project Structure

```
devrag/
├── src/
│   ├── parser.py       # AST + Markdown parsing → CodeChunk objects
│   ├── retriever.py    # BM25 + ChromaDB + RRF hybrid search
│   └── app.py          # Streamlit UI + multi-provider generation
├── tests/
│   ├── test_parser.py  # Unit tests for AST/Markdown parsing
│   ├── test_retriever.py # Unit tests for hybrid search
│   └── eval_rag.py     # 21-query evaluation suite with metrics
├── mock_data/          # Sample codebase for demos and tests
├── .chroma/            # Pre-built index (ships ready to use)
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

## Code Style
- **Python**: Follow PEP 8 with ruff. Line length: 100.
- **Type hints**: Use where applicable for public functions

## License
MIT — See LICENSE file for details.
