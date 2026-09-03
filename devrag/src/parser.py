"""
Data Ingestion & Parsing module.

Extracts Python code elements (functions, classes, docstrings) using AST.
Parses .md documentation into context-aware chunks with structural metadata.
"""

import ast
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class CodeChunk:
    """Represents a parsed chunk of code or documentation."""
    content: str
    source_file: str
    chunk_type: str  # 'function', 'class', 'method', 'module_docstring', 'markdown'
    name: Optional[str] = None
    start_line: int = 0
    end_line: int = 0
    docstring: Optional[str] = None
    parent_class: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    @property
    def citation(self) -> str:
        loc = f"{self.source_file}"
        if self.name:
            loc += f" > {self.name}"
        loc += f" (L{self.start_line}-{self.end_line})"
        return loc

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "source_file": self.source_file,
            "chunk_type": self.chunk_type,
            "name": self.name,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "docstring": self.docstring,
            "parent_class": self.parent_class,
            "metadata": self.metadata,
        }


def parse_python_file(file_path: str) -> List[CodeChunk]:
    """Parse a Python file into structured code chunks using the AST module."""
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        source = f.read()

    try:
        tree = ast.parse(source, filename=file_path)
    except SyntaxError:
        return [CodeChunk(
            content=source,
            source_file=file_path,
            chunk_type="module_raw",
            start_line=1,
            end_line=source.count("\n") + 1,
        )]

    chunks: List[CodeChunk] = []
    lines = source.splitlines()

    module_docstring = ast.get_docstring(tree)
    if module_docstring:
        chunks.append(CodeChunk(
            content=f'"""\n{module_docstring}\n"""',
            source_file=file_path,
            chunk_type="module_docstring",
            name="__module_doc__",
            start_line=1,
            end_line=module_docstring.count("\n") + 2,
            docstring=module_docstring,
        ))

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            chunks.extend(_parse_class(node, file_path, lines))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            chunks.append(_parse_function(node, file_path, lines))

    if not chunks:
        chunks.append(CodeChunk(
            content=source,
            source_file=file_path,
            chunk_type="module_raw",
            start_line=1,
            end_line=len(lines),
        ))

    return chunks


def _parse_class(node: ast.ClassDef, file_path: str, lines: List[str]) -> List[CodeChunk]:
    """Parse a class definition into chunks."""
    chunks: List[CodeChunk] = []
    end_line = _get_end_line(node, lines)
    class_source = "\n".join(lines[node.lineno - 1 : end_line])

    docstring = ast.get_docstring(node)
    chunks.append(CodeChunk(
        content=class_source,
        source_file=file_path,
        chunk_type="class",
        name=node.name,
        start_line=node.lineno,
        end_line=end_line,
        docstring=docstring,
        metadata={"bases": [b.id if isinstance(b, ast.Name) else str(b) for b in node.bases]},
    ))

    for item in node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            chunks.append(_parse_function(item, file_path, lines, parent_class=node.name))

    return chunks


def _parse_function(
    node, file_path: str, lines: List[str], parent_class: Optional[str] = None
) -> CodeChunk:
    """Parse a function/method definition into a chunk."""
    end_line = _get_end_line(node, lines)
    func_source = "\n".join(lines[node.lineno - 1 : end_line])
    docstring = ast.get_docstring(node)

    chunk_type = "method" if parent_class else "function"
    args = [a.arg for a in node.args.args]

    return CodeChunk(
        content=func_source,
        source_file=file_path,
        chunk_type=chunk_type,
        name=node.name,
        start_line=node.lineno,
        end_line=end_line,
        docstring=docstring,
        parent_class=parent_class,
        metadata={"args": args, "is_async": isinstance(node, ast.AsyncFunctionDef)},
    )


def _get_end_line(node, lines: List[str]) -> int:
    """Estimate end line of an AST node."""
    if hasattr(node, "end_lineno") and node.end_lineno:
        return node.end_lineno
    return node.lineno + 10


def parse_markdown_file(file_path: str, chunk_size: int = 1000) -> List[CodeChunk]:
    """Parse a markdown file into context-aware chunks split on headings.

    Improvements over basic splitting:
    - Preserves fenced code blocks as atomic units
    - Keeps heading + content together
    - Attaches heading hierarchy as metadata
    - Splits on paragraph boundaries, not mid-paragraph
    """
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    # Extract fenced code blocks and protect them from splitting
    code_blocks = []
    placeholder = "\x00CODE_BLOCK_{}\x00"

    def protect_code(match):
        idx = len(code_blocks)
        code_blocks.append(match.group(0))
        return placeholder.format(idx)

    protected = re.sub(r'```[\s\S]*?```', protect_code, content)

    # Split on heading boundaries
    sections = re.split(r"(?=^#{1,4}\s)", protected, flags=re.MULTILINE)
    sections = [s.strip() for s in sections if s.strip()]

    chunks: List[CodeChunk] = []
    current_offset = 1
    heading_stack: List[str] = []  # Track heading hierarchy

    for section in sections:
        lines_in_section = section.count("\n") + 1
        heading_match = re.match(r"^(#{1,4})\s+(.+)", section)
        heading = heading_match.group(2).strip() if heading_match else None
        heading_level = len(heading_match.group(1)) if heading_match else 0

        # Update heading stack
        if heading:
            # Pop deeper or equal headings
            while heading_stack and len(heading_stack) >= heading_level:
                heading_stack.pop()
            heading_stack.append(heading)

        # Restore code blocks in this section
        restored = section
        for i, block in enumerate(code_blocks):
            restored = restored.replace(placeholder.format(i), block)

        if len(restored) > chunk_size:
            sub_chunks = _split_long_section(restored, chunk_size)
            for sub in sub_chunks:
                # Restore code blocks in sub-chunks
                for i, block in enumerate(code_blocks):
                    sub = sub.replace(placeholder.format(i), block)
                chunks.append(CodeChunk(
                    content=sub,
                    source_file=file_path,
                    chunk_type="markdown",
                    name=heading,
                    start_line=current_offset,
                    end_line=current_offset + sub.count("\n"),
                    metadata={
                        "heading": heading,
                        "heading_path": list(heading_stack),
                        "heading_level": heading_level,
                    },
                ))
        else:
            chunks.append(CodeChunk(
                content=restored,
                source_file=file_path,
                chunk_type="markdown",
                name=heading,
                start_line=current_offset,
                end_line=current_offset + lines_in_section - 1,
                metadata={
                    "heading": heading,
                    "heading_path": list(heading_stack),
                    "heading_level": heading_level,
                },
            ))

        current_offset += lines_in_section

    return chunks


def _split_long_section(section: str, chunk_size: int) -> List[str]:
    """Split a long markdown section into smaller chunks on paragraph boundaries.

    Preserves code blocks as atomic units and never splits mid-paragraph.
    """
    # Protect code blocks from splitting
    code_blocks = []
    placeholder = "\x00CB_{}\x00"

    def protect_code(match):
        idx = len(code_blocks)
        code_blocks.append(match.group(0))
        return placeholder.format(idx)

    protected = re.sub(r'```[\s\S]*?```', protect_code, section)

    # Split on paragraph boundaries
    paragraphs = re.split(r"\n\n+", protected)
    result = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) + 2 > chunk_size and current:
            result.append(current.strip())
            current = para
        else:
            current = current + "\n\n" + para if current else para

    if current.strip():
        result.append(current.strip())

    # Restore code blocks
    restored_result = []
    for chunk in result:
        for i, block in enumerate(code_blocks):
            chunk = chunk.replace(placeholder.format(i), block)
        restored_result.append(chunk)

    return restored_result if restored_result else [section]


def ingest_directory(
    dir_path: str, extensions: tuple = (".py", ".md")
) -> List[CodeChunk]:
    """Recursively ingest a directory, returning all parsed chunks."""
    all_chunks: List[CodeChunk] = []
    root = Path(dir_path)

    for file_path in sorted(root.rglob("*")):
        if not file_path.is_file():
            continue
        ext = file_path.suffix.lower()
        if ext not in extensions:
            continue

        try:
            if ext == ".py":
                all_chunks.extend(parse_python_file(str(file_path)))
            elif ext == ".md":
                all_chunks.extend(parse_markdown_file(str(file_path)))
        except Exception as e:
            print(f"Warning: failed to parse {file_path}: {e}")

    return all_chunks
