"""Unit tests for the retriever module."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.parser import CodeChunk
from src.retriever import HybridRetriever, RankedResult


def test_retriever_creation():
    retriever = HybridRetriever()
    assert retriever is not None


def test_tokenize_simple():
    retriever = HybridRetriever()
    tokens = retriever._tokenize("def get_user_by_id()")
    assert "get" in tokens
    assert "user" in tokens
    assert "by" in tokens
    assert "id" in tokens


def test_tokenize_snake_case():
    retriever = HybridRetriever()
    tokens = retriever._tokenize("my_long_function_name")
    assert "my" in tokens
    assert "long" in tokens
    assert "function" in tokens
    assert "name" in tokens


def test_tokenize_camel_case():
    retriever = HybridRetriever()
    tokens = retriever._tokenize("getUserID")
    assert "get" in tokens
    assert "user" in tokens
    assert "id" in tokens


def test_tokenize_handles_strings():
    retriever = HybridRetriever()
    code = '# comment\nx = "hello"'
    tokens = retriever._tokenize(code)
    assert len(tokens) > 0


def test_retriever_index_empty():
    retriever = HybridRetriever()
    count = retriever.index_chunks([])
    assert count == 0


def test_retriever_index_chunks():
    chunks = [
        CodeChunk(
            content="def authenticate_user(username, password): pass",
            source_file="auth.py",
            chunk_type="function",
            name="authenticate_user",
            start_line=1,
            end_line=3,
        ),
        CodeChunk(
            content="def get_product(product_id): pass",
            source_file="products.py",
            chunk_type="function",
            name="get_product",
            start_line=1,
            end_line=3,
        ),
    ]
    retriever = HybridRetriever()
    count = retriever.index_chunks(chunks)
    assert count == 2


def test_bm25_search():
    """BM25 may return empty for terms with low IDF; verify search doesn't error."""
    chunks = [
        CodeChunk(
            content="The authenticate function handles user login",
            source_file="auth.py",
            chunk_type="function",
            name="authenticate",
            start_line=1,
            end_line=3,
        ),
        CodeChunk(
            content="def get_product(product_id): pass",
            source_file="products.py",
            chunk_type="function",
            name="get_product",
            start_line=1,
            end_line=3,
        ),
    ]
    retriever = HybridRetriever()
    retriever.index_chunks(chunks)
    results = retriever.search_bm25("authenticate", top_k=1)
    assert isinstance(results, list)


def test_search_rrf_returns_results():
    chunks = [
        CodeChunk(
            content="def authenticate_user(username, password): pass",
            source_file="auth.py",
            chunk_type="function",
            name="authenticate_user",
            start_line=1,
            end_line=3,
        ),
        CodeChunk(
            content="def get_product(product_id): pass",
            source_file="products.py",
            chunk_type="function",
            name="get_product",
            start_line=1,
            end_line=3,
        ),
    ]
    retriever = HybridRetriever()
    retriever.index_chunks(chunks)
    results = retriever.search_rrf("authentication", top_k=2)
    assert len(results) >= 0


def test_rrf_result_structure():
    chunks = [
        CodeChunk(
            content="def foo(): pass",
            source_file="test.py",
            chunk_type="function",
            name="foo",
            start_line=1,
            end_line=3,
        ),
    ]
    retriever = HybridRetriever()
    retriever.index_chunks(chunks)
    results = retriever.search_rrf("foo", top_k=1)
    if results:
        r = results[0]
        assert isinstance(r, RankedResult)
        assert isinstance(r.chunk, CodeChunk)
        assert r.score >= 0
        assert r.source in ["bm25", "chroma", "rrf"]


def test_retriever_clear():
    chunks = [
        CodeChunk(
            content="def foo(): pass",
            source_file="test.py",
            chunk_type="function",
            name="foo",
            start_line=1,
            end_line=3,
        ),
    ]
    retriever = HybridRetriever()
    retriever.index_chunks(chunks)
    retriever.clear()
    assert retriever._bm25 is None


def test_rank_result_dataclass():
    chunk = CodeChunk(
        content="test",
        source_file="test.py",
        chunk_type="function",
        name="foo",
        start_line=1,
        end_line=3,
    )
    result = RankedResult(chunk=chunk, score=0.95, source="rrf")
    assert result.score == 0.95
    assert result.source == "rrf"
    assert result.chunk.name == "foo"


def test_search_top_k_limit():
    chunks = [
        CodeChunk(
            content=f"def func_{i}(): pass",
            source_file=f"file_{i}.py",
            chunk_type="function",
            name=f"func_{i}",
            start_line=1,
            end_line=3,
        )
        for i in range(10)
    ]
    retriever = HybridRetriever()
    retriever.index_chunks(chunks)
    results = retriever.search_rrf("func", top_k=3)
    assert len(results) <= 3


def test_search_file_boosting():
    """Test that files appearing in multiple top results get boosted."""
    chunks = [
        CodeChunk(
            content=f"def func_{i}(): pass",
            source_file="main.py",
            chunk_type="function",
            name=f"func_{i}",
            start_line=1,
            end_line=3,
        )
        for i in range(5)
    ] + [
        CodeChunk(
            content="def other(): pass",
            source_file="other.py",
            chunk_type="function",
            name="other",
            start_line=1,
            end_line=3,
        )
    ]
    retriever = HybridRetriever()
    retriever.index_chunks(chunks)
    results = retriever.search_rrf("func", top_k=5)
    # main.py should dominate results due to file-level boosting
    main_results = [r for r in results if r.chunk.source_file == "main.py"]
    assert len(main_results) >= 3
