"""
Hybrid Retrieval Engine.

Sparse BM25 keyword search + dense vector search (ChromaDB + sentence-transformers).
Merges results via Reciprocal Rank Fusion (RRF).
"""

import contextlib
import os
import re
from dataclasses import dataclass
from pathlib import Path

import chromadb
import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

from .parser import CodeChunk

CHROMA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".chroma")
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


# Markdown's weight in the merge relative to code (see search_rrf).
DOC_WEIGHT = 0.5
# Most results one file may take before other files' results come first.
PER_FILE = 2
# Questions about design choices, where docs and ADRs are the answer.
DECISION_KEYWORDS = ("why", "strategy", "decision", "chosen", "approach", "trade-off", "tradeoff")


def _is_decision_record(chunk: CodeChunk) -> bool:
    return (chunk.source_file.lower().endswith(".md") and "adr" in chunk.source_file.lower()) or (
        chunk.chunk_type == "markdown" and chunk.metadata.get("heading", "").startswith("ADR")
    )


@dataclass
class RankedResult:
    chunk: CodeChunk
    score: float
    source: str  # 'bm25', 'chroma', or 'rrf'


class HybridRetriever:
    """Hybrid retriever combining BM25 sparse and ChromaDB dense search with RRF."""

    def __init__(self, chroma_dir: str = CHROMA_DIR):
        self.chroma_dir = chroma_dir
        self._embedder: SentenceTransformer | None = None
        self._chroma_client: chromadb.ClientAPI | None = None
        self._collection: chromadb.Collection | None = None
        self._bm25: BM25Okapi | None = None
        self._bm25_chunks: list[CodeChunk] = []
        self._chunk_map: dict[str, CodeChunk] = {}

    @property
    def embedder(self) -> SentenceTransformer:
        if self._embedder is None:
            self._embedder = SentenceTransformer(EMBEDDING_MODEL_NAME)
        return self._embedder

    @property
    def collection(self) -> chromadb.Collection:
        if self._chroma_client is None:
            self._chroma_client = chromadb.PersistentClient(path=self.chroma_dir)
        if self._collection is None:
            self._collection = self._chroma_client.get_or_create_collection(
                name="code_chunks",
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    def index_chunks(self, chunks: list[CodeChunk]) -> int:
        """Index chunks into both BM25 and ChromaDB. Returns count indexed."""
        if not chunks:
            return 0

        # Ids are list positions, so upserting a smaller corpus over a larger
        # one left the old tail searchable. Start from an empty collection.
        self.clear()
        self._bm25_chunks = chunks
        self._chunk_map = {str(i): c for i, c in enumerate(chunks)}

        self._build_bm25(chunks)
        count = self._index_chroma(chunks)

        return count

    @staticmethod
    def _index_text(chunk: CodeChunk) -> str:
        """What gets searched: the chunk plus where it lives.

        A method of BayutProvider in bayut_provider.py often never says "Bayut";
        its file and class do. Both BM25 and the embedding see this header; the
        chunk's own content is what is displayed.

        The path is taken from the ingest root, so a file at the root of a repo
        is just its name: from the absolute path it carried the folder the repo
        was cloned into, and scores changed with that folder's name.
        """
        where = "/".join(Path(chunk.relative_path or chunk.source_file).parts[-2:])
        names = " ".join(n for n in (chunk.parent_class, chunk.name) if n)
        return f"{where} {names}\n{chunk.content}"

    def _build_bm25(self, chunks: list[CodeChunk]) -> None:
        """Build BM25 index from chunks."""
        tokenized = [self._tokenize(self._index_text(c)) for c in chunks]
        self._bm25 = BM25Okapi(tokenized)

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Code-aware tokenizer that splits identifiers into meaningful tokens.

        Handles snake_case, camelCase, dotted names, and preserves string literals.
        """
        tokens = []
        # Protect string literals and comments from splitting
        protected = []
        placeholder = "\x00{}\x00"

        def protect(match):
            protected.append(match.group(0))
            return placeholder.format(len(protected) - 1)

        # Extract triple-quoted strings, single/double quoted strings, and comments
        cleaned = re.sub(r'""".*?"""', protect, text, flags=re.DOTALL)
        cleaned = re.sub(r"'''.*?'''", protect, cleaned, flags=re.DOTALL)
        cleaned = re.sub(r'"[^"\n]*"', protect, cleaned)
        cleaned = re.sub(r"'[^'\n]*'", protect, cleaned)
        cleaned = re.sub(r"#[^\n]*", protect, cleaned)

        # Split on non-alphanumeric boundaries (handles dots, underscores, hyphens)
        raw_tokens = re.split(r"[^a-zA-Z0-9]+", cleaned)

        for token in raw_tokens:
            if not token:
                continue
            # Check if this is a protected placeholder
            placeholder_match = re.match(r"\x00(\d+)\x00", token)
            if placeholder_match:
                idx = int(placeholder_match.group(1))
                # Add the original string literal as a single token
                tokens.append(protected[idx].lower())
                continue
            # Split camelCase: getUserById -> get, User, By, Id
            # Also split at digit boundaries: BM25Okapi -> BM25, Okapi
            camel_split = re.sub(r"([a-z])([A-Z])", r"\1 \2", token)
            camel_split = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", camel_split)
            camel_split = re.sub(r"([a-zA-Z])([0-9])", r"\1 \2", camel_split)
            camel_split = re.sub(r"([0-9])([a-zA-Z])", r"\1 \2", camel_split)
            for part in camel_split.split():
                tokens.append(part.lower())

        return tokens

    def _index_chroma(self, chunks: list[CodeChunk]) -> int:
        """Index chunks into ChromaDB in batches."""
        batch_size = 100
        total = 0

        for start in range(0, len(chunks), batch_size):
            batch = chunks[start : start + batch_size]
            ids = [str(start + i) for i in range(len(batch))]
            documents = [self._index_text(c) for c in batch]
            metadatas = [
                {
                    "source_file": c.source_file,
                    "chunk_type": c.chunk_type,
                    "name": c.name or "",
                    "start_line": c.start_line,
                    "end_line": c.end_line,
                    "parent_class": c.parent_class or "",
                }
                for c in batch
            ]

            self.collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
            )
            total += len(batch)

        return total

    def search_bm25(self, query: str, top_k: int = 10) -> list[RankedResult]:
        """Sparse keyword search via BM25."""
        if self._bm25 is None or not self._bm25_chunks:
            return []

        tokenized_query = self._tokenize(query)
        scores = self._bm25.get_scores(tokenized_query)

        top_indices = np.argsort(scores)[::-1][:top_k]
        results = []
        for idx in top_indices:
            if scores[idx] > 0:
                results.append(
                    RankedResult(
                        chunk=self._bm25_chunks[idx],
                        score=float(scores[idx]),
                        source="bm25",
                    )
                )

        return results

    def search_chroma(self, query: str, top_k: int = 10) -> list[RankedResult]:
        """Dense vector search via ChromaDB + sentence-transformers."""
        if self.collection.count() == 0:
            return []

        results = self.collection.query(
            query_texts=[query],
            n_results=top_k,
        )

        ranked = []
        for i in range(len(results["ids"][0])):
            distance = results["distances"][0][i] if results["distances"] else 0
            metadata = results["metadatas"][0][i] if results["metadatas"] else {}
            document = results["documents"][0][i] if results["documents"] else ""

            # The stored document carries the path header; return the original
            # chunk when this process indexed it.
            chunk = self._chunk_map.get(results["ids"][0][i]) or CodeChunk(
                content=document,
                source_file=metadata.get("source_file", ""),
                chunk_type=metadata.get("chunk_type", ""),
                name=metadata.get("name") or None,
                start_line=metadata.get("start_line", 0),
                end_line=metadata.get("end_line", 0),
                parent_class=metadata.get("parent_class") or None,
            )

            score = 1.0 - distance
            ranked.append(RankedResult(chunk=chunk, score=score, source="chroma"))

        return ranked

    def search_rrf(
        self, query: str, top_k: int = 10, bm25_weight: float = 1.0, chroma_weight: float = 1.0
    ) -> list[RankedResult]:
        """Hybrid search: BM25 and dense results merged by Reciprocal Rank Fusion.

        DevRAG answers questions about code, and docs used to win them: a
        README chunk sits mid-table in *both* lists and RRF sums the two,
        beating code that one retriever ranked first. A file-frequency boost
        then multiplied that, rewarding files for being split into many chunks.
        On a codebase DevRAG wasn't tuned on, the answering code ranked 4th-17th
        behind README, CASE_STUDY and REVIEW chunks.

        So: Markdown counts DOC_WEIGHT as much in the merge, except for
        "why/decision" questions, where design records are the answer. And no
        file may hold more than PER_FILE of the leading results; its further
        chunks still follow when nothing else matches.
        """
        bm25_results = self.search_bm25(query, top_k=top_k * 3)
        chroma_results = self.search_chroma(query, top_k=top_k * 3)

        query_lower = query.lower()
        is_decision_query = any(kw in query_lower for kw in DECISION_KEYWORDS)

        rrf_scores: dict[str, float] = {}
        rrf_chunks: dict[str, CodeChunk] = {}
        k = 60  # RRF constant

        for weight, ranked in ((bm25_weight, bm25_results), (chroma_weight, chroma_results)):
            for rank, result in enumerate(ranked):
                chunk = result.chunk
                key = f"{chunk.source_file}:{chunk.name}:{chunk.start_line}"
                is_doc = chunk.source_file.lower().endswith(".md")
                factor = 1.0 if is_decision_query or not is_doc else DOC_WEIGHT
                rrf_scores[key] = rrf_scores.get(key, 0) + factor * weight / (k + rank + 1)
                rrf_chunks[key] = chunk

        if is_decision_query:
            for key, chunk in rrf_chunks.items():
                if _is_decision_record(chunk):
                    rrf_scores[key] *= 1.3

        # Leading results: at most PER_FILE per file, by score; the rest follow.
        seen: dict[str, int] = {}
        leading, overflow = [], []
        for key in sorted(rrf_scores, key=lambda x: rrf_scores[x], reverse=True):
            source = rrf_chunks[key].source_file
            seen[source] = seen.get(source, 0) + 1
            (leading if seen[source] <= PER_FILE else overflow).append(key)

        return [
            RankedResult(chunk=rrf_chunks[key], score=rrf_scores[key], source="rrf")
            for key in (leading + overflow)[:top_k]
        ]

    def clear(self) -> None:
        """Clear all indexed data, including a collection left by an earlier run."""
        if self._chroma_client is None:
            # A fresh retriever on an existing directory has no client yet;
            # skipping the delete reopened the old collection on the next index.
            self._chroma_client = chromadb.PersistentClient(path=self.chroma_dir)
        with contextlib.suppress(Exception):  # nothing to delete
            self._chroma_client.delete_collection("code_chunks")
        self._collection = None
        self._bm25 = None
        self._bm25_chunks = []
        self._chunk_map = {}
