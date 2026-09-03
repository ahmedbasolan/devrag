# ADR-0002: AST parsing over regex for Python code

## Status

Accepted

## Context

DevRAG needs to extract structured chunks (functions, classes, methods) from Python source files. Two approaches:

- **Regex**: Simple pattern matching on `def`/`class` lines. Breaks on nested definitions, decorators, multi-line signatures, and async functions.
- **AST**: Python's `ast` module produces exact node boundaries. Handles all Python syntax correctly.

## Decision

Use `ast.parse()` for Python files. Fall back to raw source on `SyntaxError`.

- `ast.get_docstring()` extracts docstrings cleanly
- `node.end_lineno` gives exact end lines (Python 3.8+)
- Class methods are parsed as separate chunks with `parent_class` metadata

## Consequences

- Correct parsing of all Python syntax (decorators, async, nested classes)
- Zero external dependencies (stdlib only)
- Non-Python files and syntax errors fall back to raw chunking
- Markdown files use a separate heading-based parser (not AST)
