"""Stress test DevRAG retrieval and generation."""

import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.parser import ingest_directory
from src.retriever import HybridRetriever

QUERIES = [
    # Normal queries
    "How does the hybrid retrieval work?",
    "Where are errors handled?",
    "What arguments does index_chunks take?",
    "How do I add a new file type?",
    "What's the difference between BM25 and Chroma?",
    "How are markdown files split?",
    "Where is the Gemini API configured?",
    # Edge cases
    "",                          # empty query
    "xyzzy no match here",       # nonsense
    "a" * 500,                   # very long query
    "SELECT * FROM users",       # SQL injection attempt
    "<script>alert(1)</script>", # XSS attempt
    "How to hack the system?",   # adversarial
    # Technical deep dives
    "What is Reciprocal Rank Fusion and how is it implemented?",
    "How does the AST parser handle syntax errors?",
    "What embedding model is used and why?",
    "How is ChromaDB persistence configured?",
    "What metadata is stored for each code chunk?",
    # Repeated queries (cache behavior)
    "How does the hybrid retrieval work?",
    "How does the hybrid retrieval work?",
    "How does the hybrid retrieval work?",
]

def main():
    print("=" * 60)
    print("DevRAG Stress Test")
    print("=" * 60)

    # Index
    print("\n[1] Indexing project...")
    t0 = time.time()
    chunks = ingest_directory(str(Path(__file__).parent))
    print(f"    {len(chunks)} chunks in {time.time()-t0:.2f}s")

    retriever = HybridRetriever()
    t0 = time.time()
    count = retriever.index_chunks(chunks)
    print(f"    Indexed {count} in {time.time()-t0:.2f}s")

    # Search stress test
    print("\n[2] Running 22 queries...")
    times = []
    empty = 0
    errors = 0

    for i, q in enumerate(QUERIES, 1):
        t0 = time.time()
        try:
            results = retriever.search_rrf(q, top_k=5)
            elapsed = time.time() - t0
            times.append(elapsed)
            if not results:
                empty += 1
            status = f"{len(results)} results"
        except Exception as e:
            elapsed = time.time() - t0
            times.append(elapsed)
            errors += 1
            status = f"ERROR: {e}"

        short_q = q[:40] + "..." if len(q) > 40 else q or "(empty)"
        print(f"    [{i:2d}] {elapsed*1000:6.1f}ms | {status} | {short_q}")

    # Stats
    print("\n[3] Stats")
    print(f"    Total queries:  {len(QUERIES)}")
    print(f"    Empty results:  {empty}")
    print(f"    Errors:         {errors}")
    print(f"    Avg latency:    {sum(times)/len(times)*1000:.1f}ms")
    print(f"    Max latency:    {max(times)*1000:.1f}ms")
    print(f"    Min latency:    {min(times)*1000:.1f}ms")
    print("=" * 60)

if __name__ == "__main__":
    main()
