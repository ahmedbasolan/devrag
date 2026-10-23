import os
import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parser import ingest_directory, CodeChunk
from src.retriever import HybridRetriever


# ---------------------------------------------------------------------------
# Design system
# ---------------------------------------------------------------------------

COLORS = {
    "bg": "#0E1117",
    "bg_card": "#1A1D23",
    "bg_hover": "#22262E",
    "border": "#2D3139",
    "accent": "#F59E0B",
    "accent_dim": "#D97706",
    "text": "#E5E7EB",
    "text_dim": "#9CA3AF",
    "text_muted": "#6B7280",
    "success": "#10B981",
    "warning": "#F59E0B",
    "error": "#EF4444",
    "user_bg": "#1E293B",
    "assistant_bg": "#1A1D23",
}

FONT = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
FONT_MONO = "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace"


def inject_css():
    """Inject custom CSS for the DevRAG design system."""
    st.markdown(f"""
    <style>
    /* ── Base ────────────────────────────────────────────── */
    .stApp {{
        background-color: {COLORS['bg']};
        font-family: {FONT};
    }}

    /* ── Animations ──────────────────────────────────────── */
    @keyframes fadeIn {{
        from {{ opacity: 0; transform: translateY(10px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}
    @keyframes slideIn {{
        from {{ opacity: 0; transform: translateX(-10px); }}
        to {{ opacity: 1; transform: translateX(0); }}
    }}
    @keyframes pulse {{
        0%, 100% {{ opacity: 1; }}
        50% {{ opacity: 0.5; }}
    }}
    @keyframes spin {{
        0% {{ transform: rotate(0deg); }}
        100% {{ transform: rotate(360deg); }}
    }}
    .stChatMessage {{
        animation: fadeIn 0.3s ease-out;
    }}
    .stExpander {{
        animation: slideIn 0.2s ease-out;
    }}

    /* ── Header ──────────────────────────────────────────── */
    .devrag-header {{
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 4px 0 20px 0;
        border-bottom: 1px solid {COLORS['border']};
        margin-bottom: 24px;
    }}
    .devrag-header .logo {{
        font-size: 28px;
        line-height: 1;
    }}
    .devrag-header h1 {{
        font-size: 22px;
        font-weight: 700;
        color: {COLORS['text']};
        margin: 0;
        letter-spacing: -0.5px;
    }}
    .devrag-header .tagline {{
        font-size: 13px;
        color: {COLORS['text_dim']};
        margin: 2px 0 0 0;
    }}

    /* ── Sidebar ─────────────────────────────────────────── */
    section[data-testid="stSidebar"] {{
        background-color: {COLORS['bg_card']};
        border-right: 1px solid {COLORS['border']};
    }}
    section[data-testid="stSidebar"] .stMarkdown h2,
    section[data-testid="stSidebar"] .stMarkdown h3 {{
        color: {COLORS['text']};
        font-weight: 600;
    }}

    /* ── Chat input ──────────────────────────────────────── */
    .stChatInput {{
        border: 1px solid {COLORS['border']};
        border-radius: 12px;
        background: {COLORS['bg_card']};
    }}
    .stChatInput:focus-within {{
        border-color: {COLORS['accent']};
        box-shadow: 0 0 0 2px rgba(245, 158, 11, 0.15);
    }}

    /* ── Chat messages ───────────────────────────────────── */
    .stChatMessage {{
        border-radius: 12px;
        padding: 16px;
        margin: 8px 0;
        border: 1px solid {COLORS['border']};
    }}
    div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-user"]) {{
        background: {COLORS['user_bg']};
        border-color: {COLORS['border']};
    }}
    div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-assistant"]) {{
        background: {COLORS['assistant_bg']};
        border-color: {COLORS['border']};
    }}

    /* ── Buttons ─────────────────────────────────────────── */
    .stButton > button {{
        border-radius: 8px;
        font-weight: 600;
        font-family: {FONT};
        transition: all 0.15s ease;
        border: 1px solid {COLORS['border']};
        background: {COLORS['bg_card']};
        color: {COLORS['text']};
    }}
    .stButton > button:hover {{
        border-color: {COLORS['accent']};
        color: {COLORS['accent']};
    }}
    .stButton > button[kind="primary"],
    .stButton > button[data-testid="stBaseButton-primary"] {{
        background: {COLORS['accent']};
        color: #000;
        border-color: {COLORS['accent']};
        font-weight: 700;
    }}
    .stButton > button[kind="primary"]:hover,
    .stButton > button[data-testid="stBaseButton-primary"]:hover {{
        background: {COLORS['accent_dim']};
        border-color: {COLORS['accent_dim']};
        color: #000;
    }}

    /* ── Inputs ──────────────────────────────────────────── */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {{
        border-radius: 8px;
        border: 1px solid {COLORS['border']};
        background: {COLORS['bg']};
        color: {COLORS['text']};
        font-family: {FONT_MONO};
        font-size: 13px;
    }}
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {{
        border-color: {COLORS['accent']};
        box-shadow: 0 0 0 2px rgba(245, 158, 11, 0.15);
    }}

    /* ── Expanders ───────────────────────────────────────── */
    .streamlit-expanderHeader {{
        background: {COLORS['bg_card']};
        border: 1px solid {COLORS['border']};
        border-radius: 8px;
        color: {COLORS['text']};
        font-weight: 600;
    }}
    .streamlit-expanderHeader:hover {{
        border-color: {COLORS['accent']};
    }}

    /* ── Success / Info / Warning ────────────────────────── */
    .stSuccess {{
        background: rgba(16, 185, 129, 0.1);
        border: 1px solid rgba(16, 185, 129, 0.3);
        border-radius: 8px;
    }}
    .stInfo {{
        background: rgba(245, 158, 11, 0.08);
        border: 1px solid rgba(245, 158, 11, 0.25);
        border-radius: 8px;
    }}

    /* ── Code blocks ─────────────────────────────────────── */
    .stCodeBlock {{
        border-radius: 8px;
        border: 1px solid {COLORS['border']};
    }}

    /* ── Empty state ─────────────────────────────────────── */
    .empty-state {{
        text-align: center;
        padding: 80px 40px;
        color: {COLORS['text_dim']};
    }}
    .empty-state .icon {{
        font-size: 48px;
        margin-bottom: 16px;
        opacity: 0.6;
    }}
    .empty-state h3 {{
        color: {COLORS['text']};
        font-size: 18px;
        font-weight: 600;
        margin: 0 0 8px 0;
    }}
    .empty-state p {{
        font-size: 14px;
        max-width: 360px;
        margin: 0 auto;
        line-height: 1.6;
    }}

    /* ── Result cards (prepared for ticket #02) ──────────── */
    .result-card {{
        background: {COLORS['bg_card']};
        border: 1px solid {COLORS['border']};
        border-radius: 10px;
        padding: 14px 16px;
        margin: 8px 0;
        transition: border-color 0.15s ease;
    }}
    .result-card:hover {{
        border-color: {COLORS['accent']};
    }}
    .result-card .result-header {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 8px;
    }}
    .result-card .result-file {{
        font-family: {FONT_MONO};
        font-size: 12px;
        color: {COLORS['accent']};
    }}
    .result-card .result-name {{
        font-weight: 600;
        color: {COLORS['text']};
        font-size: 14px;
    }}
    .result-card .result-meta {{
        font-size: 12px;
        color: {COLORS['text_muted']};
    }}

    /* ── Utility ─────────────────────────────────────────── */
    .section-divider {{
        border: none;
        border-top: 1px solid {COLORS['border']};
        margin: 24px 0;
    }}
    .accent-text {{
        color: {COLORS['accent']};
    }}
    .muted-text {{
        color: {COLORS['text_muted']};
        font-size: 12px;
    }}

    /* ── Hide Streamlit branding ─────────────────────────── */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}
    </style>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

def _get_api_key():
    # Check environment variable first
    key = os.getenv("GEMINI_API_KEY", "") or os.getenv("GROQ_API_KEY", "") or os.getenv("OPENAI_API_KEY", "")
    if key:
        return key
    # Check session state (for UI-entered keys)
    try:
        import streamlit as st
        if "api_key" in st.session_state:
            return st.session_state.api_key
    except RuntimeError:
        pass
    return ""


def _get_provider():
    try:
        import streamlit as st
        return st.session_state.get("provider", "gemini")
    except RuntimeError:
        return "gemini"


def generate_response(query: str, chunks: list[CodeChunk]) -> str:
    if not chunks:
        return "Nothing found. Index a directory first."

    context = ""
    for i, c in enumerate(chunks[:5], 1):
        context += f"[{i}] {c.source_file} > {c.name or 'module'} (L{c.start_line}-{c.end_line})\n"
        context += f"```\n{c.content[:2000]}\n```\n\n"

    api_key = _get_api_key()
    provider = _get_provider()

    if not api_key:
        return _fallback(query, chunks)

    prompt = (
        f"You are explaining a codebase to a smart person who doesn't write code. "
        f"Answer the question in plain English. Use analogies. "
        f"Don't explain HOW the code works — explain WHAT it does and WHY it matters. "
        f"If you reference code, explain it in one sentence. "
        f"Keep it short — 2 to 4 sentences max.\n\n"
        f"CODE CONTEXT:\n{context}\n\nQuestion: {query}"
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
            return _fallback(query, chunks)

    except Exception as e:
        return f"{provider.title()} error: {e}\n\n" + _fallback(query, chunks)


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


# ---------------------------------------------------------------------------
# Source display
# ---------------------------------------------------------------------------

def render_sources(results: list):
    """Render source citations as interactive result cards with expandable panels."""
    if not results:
        return

    with st.expander(f"Sources ({len(results)})", expanded=False):
        for i, r in enumerate(results[:5], 1):
            c = r.chunk
            file_path = Path(c.source_file)
            file_ext = file_path.suffix.lstrip(".")
            file_name = file_path.name

            # Relevance score as percentage
            score_pct = min(int(r.score * 1000), 100)

            # File type badge
            badge_colors = {
                "py": ("#3572A5", "Python"),
                "md": ("#519ABA", "Markdown"),
                "js": ("#f1e05a", "JavaScript"),
                "ts": ("#3178c6", "TypeScript"),
            }
            badge_color, badge_label = badge_colors.get(file_ext, ("#6B7280", file_ext.upper()))

            # Score color
            if score_pct >= 70:
                score_color = COLORS['success']
            elif score_pct >= 40:
                score_color = COLORS['accent']
            else:
                score_color = COLORS['text_muted']

            # Expandable card for each result
            with st.expander(f"[{i}] {c.name or file_name} — {file_name} L{c.start_line}–{c.end_line}", expanded=(i == 1)):
                # Header with badge and score
                st.markdown(f"""
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                    <div>
                        <span style="font-weight:600; color:{COLORS['text']}; font-size:15px;">{c.name or file_name}</span>
                        <span style="color:{COLORS['text_muted']}; font-size:12px; margin-left:8px;">{file_name} → L{c.start_line}–{c.end_line}</span>
                    </div>
                    <div style="display:flex; align-items:center; gap:8px;">
                        <span style="background:{badge_color}20; color:{badge_color}; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:600;">{badge_label}</span>
                        <span style="color:{score_color}; font-size:12px; font-weight:600; font-family:{FONT_MONO};">{score_pct}%</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Docstring if available
                if c.docstring:
                    st.markdown(f"""
                    <div style="background:{COLORS['bg']}; border:1px solid {COLORS['border']}; border-radius:6px; padding:10px 12px; margin-bottom:12px; font-size:13px; color:{COLORS['text_dim']}; line-height:1.5;">
                        {c.docstring[:300]}
                    </div>
                    """, unsafe_allow_html=True)

                # Full code with copy button (st.code has built-in copy)
                lang = file_ext if file_ext in ("py", "javascript", "typescript", "bash", "http") else ""
                if lang == "py":
                    lang = "python"
                st.code(c.content, language=lang if lang else None, line_numbers=True)

                # Metadata footer
                meta_parts = []
                if c.parent_class:
                    meta_parts.append(f"Class: `{c.parent_class}`")
                if c.metadata.get("args"):
                    meta_parts.append(f"Args: {', '.join(c.metadata['args'][:5])}")
                if c.metadata.get("heading_path"):
                    path = " → ".join(c.metadata["heading_path"])
                    meta_parts.append(f"Section: {path}")
                if meta_parts:
                    st.markdown(f"""
                    <div style="font-size:11px; color:{COLORS['text_muted']}; padding-top:8px; border-top:1px solid {COLORS['border']};">
                        {"&nbsp;&nbsp;·&nbsp;&nbsp;".join(meta_parts)}
                    </div>
                    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    st.set_page_config(
        page_title="DevRAG",
        page_icon="⚡",
        layout="centered",
        initial_sidebar_state="expanded",
    )

    inject_css()

    # Session state
    if "retriever" not in st.session_state:
        st.session_state.retriever = HybridRetriever()
    if "indexed" not in st.session_state:
        st.session_state.indexed = False
    if "chunk_count" not in st.session_state:
        st.session_state.chunk_count = 0
    if "top_k" not in st.session_state:
        st.session_state.top_k = 5
    if "file_types" not in st.session_state:
        st.session_state.file_types = ["py", "md"]
    if "chunk_types" not in st.session_state:
        st.session_state.chunk_types = ["function", "class", "method", "markdown", "module_docstring"]

    # ── Auto-load pre-built index, or build one from DevRAG's own source ──
    if not st.session_state.indexed:
        chroma_dir = st.session_state.retriever.chroma_dir
        chroma_db = os.path.join(chroma_dir, "chroma.sqlite3")
        if os.path.exists(chroma_db) and os.path.getsize(chroma_db) > 0:
            # Pre-built index exists — load it
            try:
                count = st.session_state.retriever.collection.count()
                if count > 0:
                    st.session_state.indexed = True
                    st.session_state.chunk_count = count
            except Exception:
                pass
        if not st.session_state.indexed:
            # First run: the index isn't committed, so build it once here
            with st.spinner("First run: indexing DevRAG's own source..."):
                chunks = ingest_directory(str(Path(__file__).parent.parent))
                st.session_state.retriever.index_chunks(chunks)
                st.session_state.indexed = True
                st.session_state.chunk_count = len(chunks)

    # ── Sidebar ────────────────────────────────────────────
    with st.sidebar:
        st.markdown("""
        <div style="padding: 4px 0 20px 0;">
            <div style="font-size: 20px; font-weight: 700; color: #E5E7EB; letter-spacing: -0.5px;">⚡ DevRAG</div>
            <div style="font-size: 12px; color: #6B7280; margin-top: 2px;">Local code intelligence</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("### Index")

        repo_path = st.text_input(
            "Codebase path",
            value=str(Path(__file__).parent.parent),
            label_visibility="collapsed",
            placeholder="/path/to/your/repo",
        )

        if st.button("Index", type="primary", use_container_width=True):
            with st.spinner("Scanning and indexing..."):
                chunks = ingest_directory(repo_path)
                st.session_state.retriever.index_chunks(chunks)
                st.session_state.indexed = True
                st.session_state.chunk_count = len(chunks)

        if st.session_state.indexed:
            st.success(f"Indexed {st.session_state.chunk_count} chunks")

        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

        # API key status
        api_key = _get_api_key()
        provider = _get_provider()
        provider_names = {"gemini": "Gemini", "groq": "Groq", "openai": "OpenAI"}
        provider_colors = {"gemini": "#4285F4", "groq": "#F55036", "openai": "#10A37F"}

        if api_key:
            st.markdown(f"""
            <div style="display:flex; align-items:center; gap:6px; font-size:12px; color:{COLORS['success']};">
                <span style="width:6px; height:6px; border-radius:50%; background:{provider_colors.get(provider, COLORS['success'])}; display:inline-block;"></span>
                {provider_names.get(provider, provider)} connected
            </div>
            """, unsafe_allow_html=True)
            if st.button("Change API Key", type="secondary", use_container_width=True):
                st.session_state.show_key_change = True
                st.rerun()
        else:
            st.markdown(f"""
            <div style="display:flex; align-items:center; gap:6px; font-size:12px; color:{COLORS['text_muted']};">
                <span style="width:6px; height:6px; border-radius:50%; background:{COLORS['text_muted']}; display:inline-block;"></span>
                No API key — fallback mode
            </div>
            """, unsafe_allow_html=True)
            if st.button("Add API Key", type="secondary", use_container_width=True):
                st.session_state.show_key_change = True
                st.rerun()

        # API key change modal
        if st.session_state.get("show_key_change", False):
            with st.expander("🔑 Update API Key", expanded=True):
                # Provider selection
                new_provider = st.selectbox(
                    "Provider",
                    options=["gemini", "groq", "openai"],
                    format_func=lambda x: {"gemini": "Google Gemini", "groq": "Groq", "openai": "OpenAI"}[x],
                    key="new_provider_select"
                )
                placeholders = {"gemini": "AIzaSy...", "groq": "gsk_...", "openai": "sk-..."}
                new_key = st.text_input(
                    "API Key",
                    type="password",
                    placeholder=placeholders[new_provider],
                    key="new_api_key_input"
                )
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Save", type="primary", use_container_width=True):
                        if new_key:
                            # Validate
                            valid = True
                            if new_provider == "gemini" and not new_key.startswith("AIza"):
                                st.error("❌ Gemini keys start with AIza")
                                valid = False
                            elif new_provider == "groq" and not new_key.startswith("gsk_"):
                                st.error("❌ Groq keys start with gsk_")
                                valid = False
                            elif new_provider == "openai" and not new_key.startswith("sk-"):
                                st.error("❌ OpenAI keys start with sk-")
                                valid = False

                            if valid:
                                os.environ[f"{new_provider.upper()}_API_KEY"] = new_key
                                st.session_state.api_key = new_key
                                st.session_state.provider = new_provider
                                st.session_state.show_key_change = False
                                st.success("✅ API key updated!")
                                st.rerun()
                        else:
                            st.error("Please enter a key")
                with col2:
                    if st.button("Cancel", use_container_width=True):
                        st.session_state.show_key_change = False
                        st.rerun()

        # ── Search filters ──────────────────────────────────
        if st.session_state.indexed:
            st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
            st.markdown("### Search")

            # Top-k
            st.session_state.top_k = st.slider(
                "Results to show",
                min_value=3,
                max_value=20,
                value=st.session_state.top_k,
                key="top_k_slider",
            )

            # File type filter
            file_type_options = {"py": "Python", "md": "Markdown", "js": "JS", "ts": "TS"}
            cols = st.columns(2)
            selected_file_types = []
            for idx, (ext, label) in enumerate(file_type_options.items()):
                with cols[idx % 2]:
                    if st.checkbox(label, value=ext in st.session_state.file_types, key=f"ft_{ext}"):
                        selected_file_types.append(ext)
            if selected_file_types:
                st.session_state.file_types = selected_file_types

            # Chunk type filter
            chunk_type_options = ["function", "class", "method", "markdown", "module_docstring"]
            chunk_labels = {"function": "Functions", "class": "Classes", "method": "Methods",
                          "markdown": "Markdown", "module_docstring": "Docstrings"}
            selected_chunk_types = []
            for ct in chunk_type_options:
                if st.checkbox(chunk_labels[ct], value=ct in st.session_state.chunk_types, key=f"ct_{ct}"):
                    selected_chunk_types.append(ct)
            if selected_chunk_types:
                st.session_state.chunk_types = selected_chunk_types

    # ── Main area ──────────────────────────────────────────
    # Header
    st.markdown("""
    <div class="devrag-header">
        <div class="logo">⚡</div>
        <div>
            <h1>DevRAG</h1>
            <p class="tagline">Ask questions about any local codebase</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Check if API key is set
    api_key = _get_api_key()
    if not api_key:
        # Show API key setup screen
        st.markdown(f"""
        <div style="text-align:center; padding:60px 40px; background:{COLORS['bg_card']}; border:1px solid {COLORS['border']}; border-radius:12px; margin:20px 0;">
            <div style="font-size:48px; margin-bottom:16px;">🔑</div>
            <h2 style="color:{COLORS['text']}; margin-bottom:8px;">Welcome to DevRAG</h2>
            <p style="color:{COLORS['text_dim']}; font-size:14px; max-width:400px; margin:0 auto;">
                Choose your AI provider and enter your API key to get started.
            </p>
        </div>
        """, unsafe_allow_html=True)

        # Provider selection
        st.markdown(f"""
        <div style="text-align:center; margin:20px 0 10px; color:{COLORS['text']}; font-weight:600;">
            Choose your AI provider
        </div>
        """, unsafe_allow_html=True)

        providers = {
            "gemini": {"name": "Google Gemini", "desc": "Free tier available", "color": "#4285F4", "url": "https://aistudio.google.com/apikey", "placeholder": "AIzaSy..."},
            "groq": {"name": "Groq", "desc": "Fast inference, free tier", "color": "#F55036", "url": "https://console.groq.com/keys", "placeholder": "gsk_..."},
            "openai": {"name": "OpenAI", "desc": "GPT-4o mini", "color": "#10A37F", "url": "https://platform.openai.com/api-keys", "placeholder": "sk-..."},
        }

        cols = st.columns(3)
        for idx, (key, info) in enumerate(providers.items()):
            with cols[idx]:
                st.markdown(f"""
                <div style="background:{COLORS['bg_card']}; border:2px solid {COLORS['border']}; border-radius:8px; padding:16px; text-align:center; height:100px;">
                    <div style="font-size:20px; font-weight:700; color:{info['color']};">{info['name']}</div>
                    <div style="font-size:12px; color:{COLORS['text_dim']}; margin-top:4px;">{info['desc']}</div>
                </div>
                """, unsafe_allow_html=True)

        selected_provider = st.radio(
            "Select provider",
            options=list(providers.keys()),
            format_func=lambda x: providers[x]["name"],
            horizontal=True,
            label_visibility="collapsed",
        )

        provider_info = providers[selected_provider]

        # API key input
        with st.form("api_key_form"):
            st.markdown(f"**{provider_info['name']}** API Key")
            user_api_key = st.text_input(
                "API Key",
                type="password",
                placeholder=provider_info["placeholder"],
                label_visibility="collapsed",
            )
            submitted = st.form_submit_button("Start Using DevRAG →", type="primary", use_container_width=True)

            if submitted and user_api_key:
                # Validate key format
                valid = True
                if selected_provider == "gemini" and not user_api_key.startswith("AIza"):
                    st.error("❌ Gemini keys start with **AIzaSy**")
                    valid = False
                elif selected_provider == "groq" and not user_api_key.startswith("gsk_"):
                    st.error("❌ Groq keys start with **gsk_**")
                    valid = False
                elif selected_provider == "openai" and not user_api_key.startswith("sk-"):
                    st.error("❌ OpenAI keys start with **sk-**")
                    valid = False

                if valid:
                    os.environ[f"{selected_provider.upper()}_API_KEY"] = user_api_key
                    st.session_state.api_key = user_api_key
                    st.session_state.provider = selected_provider
                    st.success(f"✅ {provider_info['name']} connected!")
                    st.balloons()
                    st.rerun()
            elif submitted:
                st.error("Please enter an API key")

        # Get key link
        st.markdown(f"""
        <div style="text-align:center; margin-top:12px;">
            <a href="{provider_info['url']}" target="_blank" style="color:{COLORS['accent']}; font-size:13px;">
                Don't have a key? Get one free →
            </a>
        </div>
        """, unsafe_allow_html=True)

        # Skip option
        st.markdown(f"""
        <div style="text-align:center; margin-top:16px;">
            <span style="color:{COLORS['text_muted']}; font-size:13px;">
                Or continue in <strong>fallback mode</strong> (raw code snippets instead of AI explanations).
            </span>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Continue without AI →", type="secondary", use_container_width=True):
            st.session_state.api_key = ""
            st.rerun()

        return

    # Empty state with example queries
    if not st.session_state.indexed:
        st.markdown("""
        <div class="empty-state">
            <div class="icon">⚡</div>
            <h3>Point at a codebase</h3>
            <p>Enter a path in the sidebar and click <strong>Index</strong> to start asking questions about your code.</p>
        </div>
        """, unsafe_allow_html=True)
        return

    # Ready state — show example queries
    if "query_history" not in st.session_state:
        st.session_state.query_history = []

    if not st.session_state.query_history:
        st.markdown(f"""
        <div style="text-align:center; padding:40px 20px 20px; color:{COLORS['text_dim']};">
            <div style="font-size:14px; margin-bottom:16px;">Try asking:</div>
        </div>
        """, unsafe_allow_html=True)

        example_queries = [
            "How does user authentication work?",
            "What is the cache invalidation strategy?",
            "How are database migrations handled?",
            "How does the rate limiting work?",
            "What payment gateways are supported?",
        ]
        for eq in example_queries:
            st.markdown(f"""
            <div style="text-align:center; margin:4px 0;">
                <code style="background:{COLORS['bg_card']}; border:1px solid {COLORS['border']}; border-radius:6px; padding:6px 14px; font-size:13px; color:{COLORS['text_dim']}; cursor:default;">{eq}</code>
            </div>
            """, unsafe_allow_html=True)

    # Chat
    query = st.chat_input("Ask a question about the code...")
    if query:
        # Show user message immediately
        st.chat_message("user").write(query)

        # Search phase
        with st.status("🔍 Searching codebase...", expanded=False) as status:
            st.write("Tokenizing query...")
            raw_results = st.session_state.retriever.search_rrf(query, top_k=st.session_state.top_k * 3)
            st.write(f"Found {len(raw_results)} potential matches")

            # Apply filters
            filtered_results = []
            for r in raw_results:
                c = r.chunk
                ext = Path(c.source_file).suffix.lstrip(".")
                if ext not in st.session_state.file_types:
                    continue
                if c.chunk_type not in st.session_state.chunk_types:
                    continue
                filtered_results.append(r)
                if len(filtered_results) >= st.session_state.top_k:
                    break

            st.write(f"Filtered to {len(filtered_results)} results")
            status.update(label="✅ Search complete", state="complete", expanded=False)

        # Generation phase
        with st.status("🤖 Thinking...", expanded=False) as status:
            st.write("Analyzing code context...")
            chunks = [r.chunk for r in filtered_results]
            answer = generate_response(query, chunks)
            status.update(label="✅ Answer ready", state="complete", expanded=False)

        # Show answer with animation
        st.markdown("""
        <style>
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .stMarkdown {
            animation: fadeIn 0.3s ease-out;
        }
        </style>
        """, unsafe_allow_html=True)

        st.chat_message("assistant").markdown(answer)

        render_sources(filtered_results)


if __name__ == "__main__":
    main()
