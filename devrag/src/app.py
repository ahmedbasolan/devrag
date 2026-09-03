import os
import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parser import ingest_directory, CodeChunk
from src.retriever import HybridRetriever


def _get_api_key():
    return os.getenv("GEMINI_API_KEY", "")


def generate_response(query: str, chunks: list[CodeChunk]) -> str:
    if not chunks:
        return "Nothing found. Index a directory first."

    context = ""
    for i, c in enumerate(chunks[:5], 1):
        context += f"[{i}] {c.source_file} > {c.name or 'module'} (L{c.start_line}-{c.end_line})\n"
        context += f"```\n{c.content[:2000]}\n```\n\n"

    api_key = _get_api_key()
    if not api_key:
        return _fallback(query, chunks)

    try:
        from google import genai

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=(
                f"You are explaining a codebase to a smart person who doesn't write code. "
                f"Answer the question in plain English. Use analogies. "
                f"Don't explain HOW the code works — explain WHAT it does and WHY it matters. "
                f"If you reference code, explain it in one sentence. "
                f"Keep it short — 2 to 4 sentences max.\n\n"
                f"CODE CONTEXT:\n{context}\n\nQuestion: {query}"
            ),
        )
        return response.text

    except Exception as e:
        return f"Gemini error: {e}\n\n" + _fallback(query, chunks)


def _fallback(query: str, chunks: list[CodeChunk]) -> str:
    parts = [f"**What I found about:** _{query}_\n"]
    for i, c in enumerate(chunks[:3], 1):
        label = c.name or Path(c.source_file).name
        parts.append(f"**[{i}]** Found in `{label}`")
        if c.docstring:
            parts.append(f"> {c.docstring[:300]}")
        parts.append(f"```python\n{c.content[:600]}\n```\n")
    parts.append("_Set GEMINI_API_KEY for smarter answers._")
    return "\n".join(parts)


def main():
    st.set_page_config(page_title="DevRAG", page_icon=":gear:", layout="centered")
    st.title(":gear: DevRAG")
    st.caption("Ask questions about any local codebase")

    if "retriever" not in st.session_state:
        st.session_state.retriever = HybridRetriever()
    if "indexed" not in st.session_state:
        st.session_state.indexed = False

    with st.sidebar:
        st.subheader("Setup")
        repo_path = st.text_input("Path to codebase", value=str(Path(__file__).parent.parent))
        if st.button("Index", type="primary", use_container_width=True):
            with st.spinner("Indexing..."):
                chunks = ingest_directory(repo_path)
                st.session_state.retriever.index_chunks(chunks)
                st.session_state.indexed = True
                st.success(f"Done — {len(chunks)} chunks indexed")

    if not st.session_state.indexed:
        st.info("Enter a path and click **Index** to start.")
        return

    query = st.chat_input("Ask a question...")
    if query:
        results = st.session_state.retriever.search_rrf(query, top_k=5)
        chunks = [r.chunk for r in results]
        answer = generate_response(query, chunks)

        st.chat_message("user").write(query)
        st.chat_message("assistant").markdown(answer)

        with st.expander("Sources", expanded=False):
            for i, r in enumerate(results[:5], 1):
                c = r.chunk
                st.write(f"**[{i}]** `{c.source_file}` > `{c.name or 'module'}` (L{c.start_line}-{c.end_line})")


if __name__ == "__main__":
    main()
