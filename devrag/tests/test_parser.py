"""Unit tests for the parser module."""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.parser import (
    CodeChunk,
    ingest_directory,
    parse_markdown_file,
    parse_python_file,
)


def _write_temp_file(content: str, suffix: str) -> str:
    """Write content to a temp file and return its path."""
    fd, fname = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "w") as f:
        f.write(content)
    return fname


def test_parse_simple_function():
    code = '''def hello():
    """Say hello."""
    return "world"
'''
    fname = _write_temp_file(code, ".py")
    chunks = parse_python_file(fname)
    os.unlink(fname)

    assert len(chunks) >= 1
    func_chunk = [c for c in chunks if c.chunk_type == "function"]
    assert len(func_chunk) == 1
    assert func_chunk[0].name == "hello"
    assert "Say hello" in func_chunk[0].docstring


def test_parse_class_with_methods():
    code = '''class MyClass:
    """A sample class."""

    def method_a(self):
        """Method A."""
        pass

    def method_b(self, x):
        """Method B."""
        return x
'''
    fname = _write_temp_file(code, ".py")
    chunks = parse_python_file(fname)
    os.unlink(fname)

    class_chunks = [c for c in chunks if c.chunk_type == "class"]
    method_chunks = [c for c in chunks if c.chunk_type == "method"]

    assert len(class_chunks) == 1
    assert class_chunks[0].name == "MyClass"
    assert len(method_chunks) == 2
    assert method_chunks[0].name == "method_a"
    assert method_chunks[1].name == "method_b"
    assert method_chunks[1].parent_class == "MyClass"


def test_parse_async_function():
    code = '''async def fetch_data():
    """Fetch data asynchronously."""
    return {}
'''
    fname = _write_temp_file(code, ".py")
    chunks = parse_python_file(fname)
    os.unlink(fname)

    func_chunk = [c for c in chunks if c.chunk_type == "function"]
    assert len(func_chunk) == 1
    assert func_chunk[0].name == "fetch_data"
    assert func_chunk[0].metadata.get("is_async") is True


def test_parse_module_docstring():
    code = '''"""This is the module docstring."""

def foo():
    pass
'''
    fname = _write_temp_file(code, ".py")
    chunks = parse_python_file(fname)
    os.unlink(fname)

    doc_chunks = [c for c in chunks if c.chunk_type == "module_docstring"]
    assert len(doc_chunks) == 1
    assert "module docstring" in doc_chunks[0].content.lower()


def test_parse_markdown_with_headings():
    md = """# Section 1

Some text here.

## Subsection

More text.

```python
def code():
    pass
```
"""
    fname = _write_temp_file(md, ".md")
    chunks = parse_markdown_file(fname)
    os.unlink(fname)

    assert len(chunks) >= 1
    heading_chunks = [c for c in chunks if c.chunk_type == "markdown"]
    assert len(heading_chunks) >= 1
    assert heading_chunks[0].name == "Section 1"


def test_parse_markdown_preserves_code_blocks():
    md = """# Doc

```python
def hello():
    pass
```
"""
    fname = _write_temp_file(md, ".md")
    chunks = parse_markdown_file(fname)
    os.unlink(fname)

    for c in chunks:
        assert "def hello" in c.content


def test_ingest_directory():
    with tempfile.TemporaryDirectory() as tmpdir:
        src = Path(tmpdir) / "src"
        src.mkdir()
        (src / "test.py").write_text("def foo(): pass\n")
        (src / "README.md").write_text("# Doc\n\nText\n")

        chunks = ingest_directory(tmpdir)
        assert len(chunks) >= 2

        py_chunks = [c for c in chunks if c.chunk_type == "function"]
        md_chunks = [c for c in chunks if c.chunk_type == "markdown"]
        assert len(py_chunks) >= 1
        assert len(md_chunks) >= 1


def test_ingest_directory_excludes_test_files():
    """Test files duplicate the names of the code they exercise, so they must
    be excludable or they displace the real definitions from the top-k."""
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "retriever.py").write_text("def search_rrf(q): pass\n")
        (Path(tmpdir) / "test_retriever.py").write_text("def test_search_rrf(): pass\n")

        with_tests = ingest_directory(tmpdir, include_tests=True)
        assert any("test_retriever" in c.source_file for c in with_tests)

        without_tests = ingest_directory(
            tmpdir, include_tests=True, exclude_files=("test_retriever.py",)
        )
        assert not any("test_retriever" in c.source_file for c in without_tests)
        assert any("retriever.py" in c.source_file for c in without_tests)


def _layout(root: Path, files: list[str]) -> None:
    for rel in files:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if rel.endswith(".md"):
            path.write_text("# Notes\n\nHow the fixtures are built.\n")
        else:
            path.write_text(f"def f_{path.stem}(): pass\n")


CODE_FILES = ["app.py", "src/latest.py", "src/contest.py", "testing_utils.py", "docs/guide.md"]
TEST_FILES = [
    "test_app.py",
    "app_test.py",
    "conftest.py",
    "tests/helpers.py",
    "tests/README.md",
    "test/test_cli.py",
    "backend/tests/test_api.py",
]


def test_tests_are_left_out_by_default():
    """On three repos DevRAG wasn't built against, test files ranked above the
    code they test: a test names the same functions, so it matches the same
    questions. Both layouts are common: test_*.py beside the code, or a tests/
    directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        _layout(root, CODE_FILES + TEST_FILES)

        indexed = {
            Path(c.source_file).relative_to(root).as_posix() for c in ingest_directory(tmpdir)
        }

        assert indexed == set(CODE_FILES)


def test_tests_can_still_be_included():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        _layout(root, CODE_FILES + TEST_FILES)

        chunks = ingest_directory(tmpdir, include_tests=True)
        indexed = {Path(c.source_file).relative_to(root).as_posix() for c in chunks}

        assert indexed == set(CODE_FILES + TEST_FILES)


def test_ingest_directory_skips_cache_and_build_dirs():
    """Build output and caches must never enter the corpus."""
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "app.py").write_text("def run(): pass\n")
        for junk in ("__pycache__", ".pytest_cache", ".chroma", "node_modules"):
            d = Path(tmpdir) / junk
            d.mkdir()
            (d / "junk.py").write_text("def junk(): pass\n")

        sources = [c.source_file for c in ingest_directory(tmpdir)]
        assert any("app.py" in s for s in sources)
        assert not any("__pycache__" in s for s in sources)
        assert not any(".pytest_cache" in s for s in sources)
        assert not any(".chroma" in s for s in sources)
        assert not any("node_modules" in s for s in sources)


def test_code_chunk_citation():
    chunk = CodeChunk(
        content="test",
        source_file="file.py",
        chunk_type="function",
        name="my_func",
        start_line=1,
        end_line=10,
    )
    cit = chunk.citation
    assert "file.py" in cit
    assert "my_func" in cit
    assert "L1" in cit
    assert "10" in cit


def test_code_chunk_to_dict():
    chunk = CodeChunk(
        content="test",
        source_file="file.py",
        chunk_type="function",
        name="my_func",
        start_line=1,
        end_line=10,
    )
    d = chunk.to_dict()
    assert d["source_file"] == "file.py"
    assert d["name"] == "my_func"
    assert d["start_line"] == 1


def test_empty_file_parses():
    code = ""
    fname = _write_temp_file(code, ".py")
    chunks = parse_python_file(fname)
    os.unlink(fname)

    assert len(chunks) >= 1
    assert chunks[0].chunk_type == "module_raw"


def test_ast_syntax_error_fallback():
    code = "def bad( :\n"
    fname = _write_temp_file(code, ".py")
    chunks = parse_python_file(fname)
    os.unlink(fname)

    assert len(chunks) >= 1
    assert chunks[0].chunk_type == "module_raw"


def test_parse_function_args():
    code = '''def calculate(a, b, c=None):
    """Calculate something."""
    pass
'''
    fname = _write_temp_file(code, ".py")
    chunks = parse_python_file(fname)
    os.unlink(fname)

    func_chunk = [c for c in chunks if c.chunk_type == "function"]
    assert len(func_chunk) == 1
    assert func_chunk[0].metadata.get("args") == ["a", "b", "c"]


def test_parse_module_raw():
    code = "x = 1\ny = 2\n"
    fname = _write_temp_file(code, ".py")
    chunks = parse_python_file(fname)
    os.unlink(fname)

    raw_chunks = [c for c in chunks if c.chunk_type == "module_raw"]
    assert len(raw_chunks) >= 1


def test_module_level_settings_are_indexed():
    """A settings module was invisible: config.py's 32 lines of constants were
    dropped because only functions, classes and the docstring became chunks, so
    "where is the max tokens budget configured?" could never be answered."""
    code = '''"""Settings."""
import os

LLM_MAX_TOKENS = 1500
LLM_TEMPERATURE = 0.2


def helper():
    return 1


RATE_LIMIT = int(os.environ.get("RATE_LIMIT", "10"))
'''
    fname = _write_temp_file(code, ".py")
    chunks = parse_python_file(fname)
    os.unlink(fname)

    module_code = [c for c in chunks if c.chunk_type == "module_code"]
    text = "\n".join(c.content for c in module_code)
    assert "LLM_MAX_TOKENS = 1500" in text
    assert "RATE_LIMIT" in text
    assert "def helper" not in text  # functions keep their own chunk


def test_imports_alone_are_not_a_module_chunk():
    code = '"""Doc."""\nimport os\nfrom pathlib import Path\n\n\ndef f():\n    pass\n'
    fname = _write_temp_file(code, ".py")
    chunks = parse_python_file(fname)
    os.unlink(fname)

    assert not [c for c in chunks if c.chunk_type == "module_code"]
