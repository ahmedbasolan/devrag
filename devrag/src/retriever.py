"""
Hybrid Retrieval Engine.

Sparse BM25 keyword search + dense vector search (ChromaDB + sentence-transformers).
Merges results via Reciprocal Rank Fusion (RRF).
"""

import os
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

import chromadb
import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

from .parser import CodeChunk


CHROMA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".chroma")
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@dataclass
class RankedResult:
    chunk: CodeChunk
    score: float
    source: str  # 'bm25', 'chroma', or 'rrf'


class HybridRetriever:
    """Hybrid retriever combining BM25 sparse and ChromaDB dense search with RRF."""

    def __init__(self, chroma_dir: str = CHROMA_DIR):
        self.chroma_dir = chroma_dir
        self._embedder: Optional[SentenceTransformer] = None
        self._chroma_client: Optional[chromadb.ClientAPI] = None
        self._collection: Optional[chromadb.Collection] = None
        self._bm25: Optional[BM25Okapi] = None
        self._bm25_chunks: List[CodeChunk] = []
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

    def index_chunks(self, chunks: List[CodeChunk]) -> int:
        """Index chunks into both BM25 and ChromaDB. Returns count indexed."""
        if not chunks:
            return 0

        self._bm25_chunks = chunks
        self._chunk_map = {str(i): c for i, c in enumerate(chunks)}

        self._build_bm25(chunks)
        count = self._index_chroma(chunks)

        return count

    def _build_bm25(self, chunks: List[CodeChunk]) -> None:
        """Build BM25 index from chunks."""
        tokenized = [
            self._tokenize(c.content) for c in chunks
        ]
        self._bm25 = BM25Okapi(tokenized)

    @staticmethod
    def _tokenize(text: str) -> List[str]:
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
        raw_tokens = re.split(r'[^a-zA-Z0-9]+', cleaned)

        for token in raw_tokens:
            if not token:
                continue
            # Check if this is a protected placeholder
            placeholder_match = re.match(r'\x00(\d+)\x00', token)
            if placeholder_match:
                idx = int(placeholder_match.group(1))
                # Add the original string literal as a single token
                tokens.append(protected[idx].lower())
                continue
            # Split camelCase: getUserById -> get, User, By, Id
            # Also split at digit boundaries: BM25Okapi -> BM25, Okapi
            camel_split = re.sub(r'([a-z])([A-Z])', r'\1 \2', token)
            camel_split = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', camel_split)
            camel_split = re.sub(r'([a-zA-Z])([0-9])', r'\1 \2', camel_split)
            camel_split = re.sub(r'([0-9])([a-zA-Z])', r'\1 \2', camel_split)
            for part in camel_split.split():
                tokens.append(part.lower())

        return tokens

    def _index_chroma(self, chunks: List[CodeChunk]) -> int:
        """Index chunks into ChromaDB in batches."""
        batch_size = 100
        total = 0

        for start in range(0, len(chunks), batch_size):
            batch = chunks[start : start + batch_size]
            ids = [str(start + i) for i in range(len(batch))]
            documents = [c.content for c in batch]
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

    def search_bm25(self, query: str, top_k: int = 10) -> List[RankedResult]:
        """Sparse keyword search via BM25."""
        if self._bm25 is None or not self._bm25_chunks:
            return []

        tokenized_query = self._tokenize(query)
        scores = self._bm25.get_scores(tokenized_query)

        top_indices = np.argsort(scores)[::-1][:top_k]
        results = []
        for idx in top_indices:
            if scores[idx] > 0:
                results.append(RankedResult(
                    chunk=self._bm25_chunks[idx],
                    score=float(scores[idx]),
                    source="bm25",
                ))

        return results

    def search_chroma(self, query: str, top_k: int = 10) -> List[RankedResult]:
        """Dense vector search via ChromaDB + sentence-transformers."""
        if self.collection.count() == 0:
            return []

        results = self.collection.query(
            query_texts=[query],
            n_results=top_k,
        )

        ranked = []
        for i in range(len(results["ids"][0])):
            doc_id = results["ids"][0][i]
            distance = results["distances"][0][i] if results["distances"] else 0
            metadata = results["metadatas"][0][i] if results["metadatas"] else {}
            document = results["documents"][0][i] if results["documents"] else ""

            chunk = CodeChunk(
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
    ) -> List[RankedResult]:
        """Hybrid search using Reciprocal Rank Fusion with file-level boosting.

        After RRF merging, boosts chunks from files that appear in the top results.
        This counteracts the dilution effect where large files produce many small chunks
        that individually score lower than focused chunks from smaller files.
        """
        bm25_results = self.search_bm25(query, top_k=top_k * 3)
        chroma_results = self.search_chroma(query, top_k=top_k * 3)

        rrf_scores: dict[str, float] = {}
        rrf_chunks: dict[str, CodeChunk] = {}

        k = 60  # RRF constant

        for rank, result in enumerate(bm25_results):
            key = f"{result.chunk.source_file}:{result.chunk.name}:{result.chunk.start_line}"
            rrf_scores[key] = rrf_scores.get(key, 0) + bm25_weight / (k + rank + 1)
            rrf_chunks[key] = result.chunk

        for rank, result in enumerate(chroma_results):
            key = f"{result.chunk.source_file}:{result.chunk.name}:{result.chunk.start_line}"
            rrf_scores[key] = rrf_scores.get(key, 0) + chroma_weight / (k + rank + 1)
            rrf_chunks[key] = result.chunk

        # ── File-level boosting ──────────────────────────────
        # Count how many times each file appears in the top results
        file_counts: dict[str, int] = {}
        sorted_keys = sorted(rrf_scores.keys(), key=lambda k: rrf_scores[k], reverse=True)
        for key in sorted_keys[:top_k * 2]:
            file_path = rrf_chunks[key].source_file
            file_counts[file_path] = file_counts.get(file_path, 0) + 1

        # Boost files that appear in multiple top results
        # The more a file appears, the more its other chunks should be boosted
        boosted_scores: dict[str, float] = {}
        for key, score in rrf_scores.items():
            file_path = rrf_chunks[key].source_file
            file_count = file_counts.get(file_path, 0)
            if file_count >= 2:
                # Boost: more appearances = higher multiplier (capped at 1.5x)
                boost = 1.0 + min(file_count * 0.1, 0.5)
                boosted_scores[key] = score * boost
            else:
                boosted_scores[key] = score

        # Also boost markdown doc chunks for decision-type queries
        decision_keywords = {"why", "strategy", "decision", "chosen", "approach", "trade-off", "tradeoff"}
        query_lower = query.lower()
        is_decision_query = any(kw in query_lower for kw in decision_keywords)
        if is_decision_query:
            for key, chunk in rrf_chunks.items():
                if chunk.source_file.endswith(".md") and "adr" in chunk.source_file.lower():
                    boosted_scores[key] = boosted_scores.get(key, rrf_scores.get(key, 0)) * 1.3
                elif chunk.chunk_type == "markdown" and chunk.metadata.get("heading", "").startswith("ADR"):
                    boosted_scores[key] = boosted_scores.get(key, rrf_scores.get(key, 0)) * 1.3

        # Re-sort by boosted scores
        sorted_keys = sorted(boosted_scores.keys(), key=lambda k: boosted_scores[k], reverse=True)

        results = []
        for key in sorted_keys[:top_k]:
            results.append(RankedResult(
                chunk=rrf_chunks[key],
                score=boosted_scores[key],
                source="rrf",
            ))

        return results

    def clear(self) -> None:
        """Clear all indexed data."""
        if self._chroma_client:
            try:
                self._chroma_client.delete_collection("code_chunks")
                self._collection = None
            except Exception:
                pass
        self._bm25 = None
        self._bm25_chunks = []
        self._chunk_map = {}
