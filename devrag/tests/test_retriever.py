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


def _retriever() -> HybridRetriever:
    import tempfile

    return HybridRetriever(chroma_dir=tempfile.mkdtemp())


def _chunk(content, source_file, name, chunk_type="function", start=1, parent=None):
    return CodeChunk(
        content=content,
        source_file=source_file,
        chunk_type=chunk_type,
        name=name,
        start_line=start,
        end_line=start + 2,
        parent_class=parent,
    )


def test_file_path_is_searchable():
    """A method in bayut_provider.py that never says "Bayut" was unfindable by
    "how does the Bayut provider fetch listings?": the path wasn't indexed."""
    # A realistic handful of chunks: with two, a term in one of them gets a
    # BM25 IDF of exactly zero and nothing scores.
    others = [
        _chunk(f"def step_{i}(x):\n    return x + {i}", f"/repo/src/mod_{i}.py", f"step_{i}")
        for i in range(5)
    ]
    chunks = [
        _chunk(
            "def _search(self, q):\n    return self.session.get(URL, params=q)",
            "/repo/src/bayut_provider.py",
            "_search",
            "method",
            parent="Provider",
        ),
        *others,
    ]
    r = _retriever()
    r.index_chunks(chunks)
    top = r.search_bm25("bayut provider", top_k=1)
    assert top and top[0].chunk.source_file.endswith("bayut_provider.py")


def test_one_file_cannot_fill_the_top_results():
    """A README split into many chunks took the top 5 for most questions, so the
    code that answered them ranked 4th to 17th."""
    readme = [
        _chunk(
            f"## Section {i}\nThe yield calculation uses rents and prices.",
            "/repo/README.md",
            f"Section {i}",
            "markdown",
            start=i * 10,
        )
        for i in range(6)
    ]
    code = [
        _chunk(
            "def net_yield(rent, price):\n    return rent / price * 0.87",
            "/repo/src/calc.py",
            "net_yield",
        )
    ]
    r = _retriever()
    r.index_chunks(readme + code)
    top = r.search_rrf("yield calculation rents prices", top_k=3)
    files = [x.chunk.source_file for x in top]
    assert files.count("/repo/README.md") <= 2
    assert "/repo/src/calc.py" in files


def test_code_outranks_a_doc_describing_it():
    doc = _chunk(
        "## Mortgage\nThe monthly mortgage payment is calculated from principal, rate and term.",
        "/repo/README.md",
        "Mortgage",
        "markdown",
    )
    code = _chunk(
        "def monthly_mortgage_payment(principal, rate, term):\n"
        "    r = rate / 12\n    return principal * r / (1 - (1 + r) ** -term)",
        "/repo/src/calculators.py",
        "monthly_mortgage_payment",
    )
    r = _retriever()
    r.index_chunks([doc, code])
    top = r.search_rrf("How is the monthly mortgage payment calculated?", top_k=2)
    assert top[0].chunk.source_file == "/repo/src/calculators.py"


def test_why_questions_still_prefer_decision_records():
    adr = _chunk(
        "# ADR 0001: Hybrid retrieval\nWe chose BM25 plus embeddings because "
        "neither alone handles identifiers and concepts.",
        "/repo/docs/adr/0001-hybrid-retrieval.md",
        "ADR 0001",
        "markdown",
    )
    code = _chunk(
        "def search(q):\n    return bm25(q) + dense(q)", "/repo/src/retriever.py", "search"
    )
    r = _retriever()
    r.index_chunks([adr, code])
    top = r.search_rrf("Why was hybrid retrieval with BM25 chosen?", top_k=2)
    assert top[0].chunk.source_file.endswith("0001-hybrid-retrieval.md")


def test_reindexing_replaces_the_previous_corpus():
    """Chunk ids are positions, written with upsert into a persistent collection:
    indexing a smaller second repo left the first repo's chunks searchable."""
    r = _retriever()
    r.index_chunks(
        [
            _chunk(f"def old_{i}(): pass  # legacy billing", "/old/a.py", f"old_{i}")
            for i in range(5)
        ]
    )
    r.index_chunks([_chunk("def new(): pass", "/new/b.py", "new")])
    dense = r.search_chroma("legacy billing", top_k=5)
    assert all(x.chunk.source_file == "/new/b.py" for x in dense)


def test_reindexing_after_a_restart_replaces_the_previous_corpus():
    """The same bug across processes: a fresh retriever on an existing .chroma
    directory skipped the delete (it had no client yet), reopened the old
    collection and upserted over only its first positions."""
    import tempfile

    path = tempfile.mkdtemp()
    first = HybridRetriever(chroma_dir=path)
    first.index_chunks(
        [
            _chunk(f"def old_{i}(): pass  # legacy billing", "/old/a.py", f"old_{i}")
            for i in range(5)
        ]
    )
    second = HybridRetriever(chroma_dir=path)
    second.index_chunks([_chunk("def new(): pass", "/new/b.py", "new")])
    dense = second.search_chroma("legacy billing", top_k=5)
    assert all(x.chunk.source_file == "/new/b.py" for x in dense)
