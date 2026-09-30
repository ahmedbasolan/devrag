"""Generation logic: prompt construction, LLM dispatch, and fallback responses."""

import logging
import re
import time
from collections import deque
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Rate limiting ──────────────────────────────────────────────────────

_query_timestamps: deque = deque()
RATE_LIMIT = 10  # max queries per minute


def _check_rate_limit() -> bool:
    """Return True if rate limit is exceeded."""
    now = time.time()
    while _query_timestamps and _query_timestamps[0] < now - 60:
        _query_timestamps.popleft()
    if len(_query_timestamps) >= RATE_LIMIT:
        return True
    _query_timestamps.append(now)
    return False


# ── Query sanitization ────────────────────────────────────────────────

_INJECTION_PATTERNS = re.compile(
    r"(?i)(ignore|disregard|forget|override)\s+(all\s+)?(previous|above|prior|earlier)",
)


def _sanitize_query(query: str) -> str:
    """Strip potential prompt injection patterns and limit length."""
    cleaned = _INJECTION_PATTERNS.sub("", query)
    return cleaned.strip()[:1000]


# ── API key and provider ──────────────────────────────────────────────


def _get_api_key() -> str:
    """Read API key from env vars or session state."""
    import os

    key = (
        os.getenv("GEMINI_API_KEY", "")
        or os.getenv("GROQ_API_KEY", "")
        or os.getenv("OPENAI_API_KEY", "")
    )
    if key:
        return key
    try:
        import streamlit as st

        if "api_key" in st.session_state:
            return st.session_state.api_key
    except RuntimeError:
        pass
    return ""


def _get_provider() -> str:
    try:
        import streamlit as st

        return st.session_state.get("provider", "gemini")
    except RuntimeError:
        return "gemini"


# ── Generation ────────────────────────────────────────────────────────


def generate_response(query: str, results: list) -> str:
    if _check_rate_limit():
        return "Rate limit exceeded. Please wait a moment and try again."

    if not results:
        return "Nothing found. Index a directory first."

    safe_query = _sanitize_query(query)

    context = ""
    for i, r in enumerate(results[:5], 1):
        c = r.chunk
        context += f"[{i}] {c.source_file} > {c.name or 'module'} (L{c.start_line}-{c.end_line})\n"
        context += f"```\n{c.content[:2000]}\n```\n\n"

    api_key = _get_api_key()
    provider = _get_provider()

    if not api_key:
        return _fallback(query, results)

    prompt = (
        "You are explaining a codebase to a smart person who doesn't write code. "
        "Answer the question in plain English. Use analogies. "
        "Don't explain HOW the code works — explain WHAT it does and WHY it matters. "
        "If you reference code, explain it in one sentence. "
        "Keep it short — 2 to 4 sentences max.\n\n"
        "---\n"
        f"CODE CONTEXT:\n{context}\n"
        "---\n"
        f"User question: {safe_query}\n"
        "---\n"
        "Answer:"
    )

    try:
        if provider == "gemini":
            from google import genai

            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
            )
            return response.text

        elif provider == "groq":
            from groq import Groq

            client = Groq(api_key=api_key)
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
            )
            return response.choices[0].message.content

        elif provider == "openai":
            from openai import OpenAI

            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
            )
            return response.choices[0].message.content

        else:
            return _fallback(query, results)

    except Exception:
        logger.exception("LLM provider error")
        return (
            "Something went wrong with the AI provider. "
            "Please check your API key and try again.\n\n" + _fallback(query, results)
        )


def _fallback(query: str, results: list) -> str:
    parts = [f"**What I found about:** _{query}_\n"]
    for i, r in enumerate(results[:3], 1):
        c = r.chunk
        label = c.name or Path(c.source_file).name
        parts.append(f"**[{i}]** Found in `{label}`")
        if c.docstring:
            parts.append(f"> {c.docstring[:300]}")
        parts.append(f"```python\n{c.content[:600]}\n```\n")
    parts.append("_Set GEMINI_API_KEY for smarter answers._")
    return "\n".join(parts)
