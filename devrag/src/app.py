import os
from html import escape as _html_escape
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from src.generator import _get_api_key, _get_provider, generate_response  # noqa: E402
from src.parser import ingest_directory  # noqa: E402
from src.retriever import HybridRetriever  # noqa: E402

# ---------------------------------------------------------------------------
# Design system
# ---------------------------------------------------------------------------

COLORS = {
    "bg": "#0E1117",
    "bg_card": "#1A1D23",
    "bg_hover": "#22262E",
    "border": "#2D3139",
    "border_input": "#64748B",
    "accent": "#F59E0B",
    "accent_dim": "#D97706",
    "text": "#E5E7EB",
    "text_dim": "#9CA3AF",
    "text_muted": "#8B94A3",
    "success": "#10B981",
    "warning": "#F59E0B",
    "error": "#EF4444",
    "user_bg": "#1E293B",
    "assistant_bg": "#1A1D23",
}

FONT = (
    "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI Variable Display', "
    "'Segoe UI', Roboto, 'Helvetica Neue', sans-serif"
)
FONT_MONO = "'JetBrains Mono', 'Fira Code', 'Cascadia Code', 'SF Mono', Consolas, monospace"

# Phosphor Icons (regular weight, 256px grid) — inline SVG, no network needed.
_ICONS = {
    "lightning": (
        "M215.79,118.17a8,8,0,0,0-5-5.66L153.18,90.9l14.66-73.33a8,8,0,0,0-13.69-7"
        "-112,120a8,8,0,0,0,3,13l57.63,21.61L88.16,238.43a8,8,0,0,0,13.69,7l112-120A8,8,0,0,0,215.79,118.17ZM109.37,214l10.47-52.38a8,8,0,0,0-5-9.06L62,132.71l84.62-90.66L136.16,94.43a8,8,0,0,0,5,9.06l52.8,19.8Z"
    ),
    "key": (
        "M216.57,39.43A80,80,0,0,0,83.91,120.78L28.69,176A15.86,15.86,0,0,0,24,187.31V216a16,16,0,0,0,16,16H72a8,8,0,0,0,8-8V208H96a8,8,0,0,0,8-8V184h16a8,8,0,0,0,5.66-2.34l9.56-9.57A79.73,79.73,0,0,0,160,176h.1A80,80,0,0,0,216.57,39.43ZM224,98.1c-1.09,34.09-29.75,61.86-63.89,61.9H160a63.7,63.7,0,0,1-23.65-4.51,8,8,0,0,0-8.84,1.68L116.69,168H96a8,8,0,0,0-8,8v16H72a8,8,0,0,0-8,8v16H40V187.31l58.83-58.82a8,8,0,0,0,1.68-8.84A63.72,63.72,0,0,1,96,95.92c0-34.14,27.81-62.8,61.9-63.89A64,64,0,0,1,224,98.1ZM192,76a12,12,0,1,1-12-12A12,12,0,0,1,192,76Z"
    ),
    "magnifying-glass": (
        "M229.66,218.34l-50.07-50.06a88.11,88.11,0,1,0-11.31,11.31l50.06,50.07a8,8,0,0,0,11.32-11.32ZM40,112a72,72,0,1,1,72,72A72.08,72.08,0,0,1,40,112Z"
    ),
    "robot": (
        "M200,48H136V16a8,8,0,0,0-16,0V48H56A32,32,0,0,0,24,80V192a32,32,0,0,0,32,32H200a32,32,0,0,0,32-32V80A32,32,0,0,0,200,48Zm16,144a16,16,0,0,1-16,16H56a16,16,0,0,1-16-16V80A16,16,0,0,1,56,64H200a16,16,0,0,1,16,16Zm-52-56H92a28,28,0,0,0,0,56h72a28,28,0,0,0,0-56Zm-24,16v24H116V152ZM80,164a12,12,0,0,1,12-12h8v24H92A12,12,0,0,1,80,164Zm84,12h-8V152h8a12,12,0,0,1,0,24ZM72,108a12,12,0,1,1,12,12A12,12,0,0,1,72,108Zm88,0a12,12,0,1,1,12,12A12,12,0,0,1,160,108Z"
    ),
    "check-circle": (
        "M173.66,98.34a8,8,0,0,1,0,11.32l-56,56a8,8,0,0,1-11.32,0l-24-24a8,8,0,0,1,11.32-11.32L112,148.69l50.34-50.35A8,8,0,0,1,173.66,98.34ZM232,128A104,104,0,1,1,128,24,104.11,104.11,0,0,1,232,128Zm-16,0a88,88,0,1,0-88,88A88.1,88.1,0,0,0,216,128Z"
    ),
    "x-circle": (
        "M165.66,101.66,139.31,128l26.35,26.34a8,8,0,0,1-11.32,11.32L128,139.31l-26.34,26.35a8,8,0,0,1-11.32-11.32L116.69,128,90.34,101.66a8,8,0,0,1,11.32-11.32L128,116.69l26.34-26.35a8,8,0,0,1,11.32,11.32ZM232,128A104,104,0,1,1,128,24,104.11,104.11,0,0,1,232,128Zm-16,0a88,88,0,1,0-88,88A88.1,88.1,0,0,0,216,128Z"
    ),
    "sparkle": (
        "M197.58,129.06,146,110l-19-51.62a15.92,15.92,0,0,0-29.88,0L78,110l-51.62,19a15.92,15.92,0,0,0,0,29.88L78,178l19,51.62a15.92,15.92,0,0,0,29.88,0L146,178l51.62-19a15.92,15.92,0,0,0,0-29.88ZM137,164.22a8,8,0,0,0-4.74,4.74L112,223.85,91.78,169A8,8,0,0,0,87,164.22L32.15,144,87,123.78A8,8,0,0,0,91.78,119L112,64.15,132.22,119a8,8,0,0,0,4.74,4.74L191.85,144ZM144,40a8,8,0,0,1,8-8h16V16a8,8,0,0,1,16,0V32h16a8,8,0,0,1,0,16H184V64a8,8,0,0,1-16,0V48H152A8,8,0,0,1,144,40ZM248,88a8,8,0,0,1-8,8h-8v8a8,8,0,0,1-16,0V96h-8a8,8,0,0,1,0-16h8V72a8,8,0,0,1,16,0v8h8A8,8,0,0,1,248,88Z"
    ),
}


def icon(name: str, size: int = 16, style: str = "") -> str:
    """Render an inline Phosphor icon (decorative — callers pair it with text)."""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" '
        f'width="{size}" height="{size}" fill="currentColor" aria-hidden="true" '
        f'focusable="false" style="flex-shrink:0;{style}"'
        f'><path d="{_ICONS[name]}"/></svg>'
    )


def inject_css():
    """Inject custom CSS for the DevRAG design system."""
    st.markdown(
        f"""
    <style>
    /* ── Base ────────────────────────────────────────────── */
    :root {{ color-scheme: dark; }}
    .stApp {{
        background-color: {COLORS["bg"]};
        background-image: radial-gradient(
            1100px 460px at 50% -8%,
            rgba(245, 158, 11, 0.055),
            transparent 70%
        );
        font-family: {FONT};
    }}
    ::selection {{
        background: rgba(245, 158, 11, 0.28);
        color: #FFFFFF;
    }}

    /* ── Scrollbar ───────────────────────────────────────── */
    ::-webkit-scrollbar {{ width: 10px; height: 10px; }}
    ::-webkit-scrollbar-track {{ background: transparent; }}
    ::-webkit-scrollbar-thumb {{
        background: {COLORS["border"]};
        border-radius: 8px;
        border: 2px solid {COLORS["bg"]};
    }}
    ::-webkit-scrollbar-thumb:hover {{ background: #3F4650; }}

    /* ── Animations (opt-in, motion-safe users only) ─────── */
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
    @media (prefers-reduced-motion: no-preference) {{
        .stChatMessage {{ animation: fadeIn 0.3s ease-out; }}
        .stExpander {{ animation: slideIn 0.2s ease-out; }}
    }}
    @media (prefers-reduced-motion: reduce) {{
        .stChatMessage, .stExpander, .stMarkdown {{
            animation: none !important;
        }}
        * {{ transition-duration: 0.01ms !important; }}
    }}

    /* ── Header ──────────────────────────────────────────── */
    .devrag-header {{
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 4px 0 20px 0;
        border-bottom: none;
        position: relative;
        margin-bottom: 24px;
    }}
    .devrag-header::after {{
        content: "";
        position: absolute;
        left: 0;
        right: 0;
        bottom: 0;
        height: 1px;
        background: linear-gradient(
            90deg,
            transparent,
            rgba(245, 158, 11, 0.35),
            rgba(255, 255, 255, 0.06),
            transparent
        );
    }}
    .devrag-header .logo {{
        font-size: 28px;
        line-height: 1;
        color: {COLORS["accent"]};
        display: flex;
        filter: drop-shadow(0 0 10px rgba(245, 158, 11, 0.45));
    }}
    .devrag-header h1 {{
        font-size: 22px;
        font-weight: 700;
        margin: 0;
        letter-spacing: -0.6px;
        background: linear-gradient(95deg, #FDE68A 0%, #F59E0B 55%, #D97706 100%);
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
    }}
    .devrag-header .tagline {{
        font-size: 13px;
        color: {COLORS["text_dim"]};
        margin: 2px 0 0 0;
        letter-spacing: 0.01em;
    }}
    .devrag-wordmark {{
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 20px;
        font-weight: 700;
        letter-spacing: -0.4px;
        background: linear-gradient(95deg, #FDE68A 0%, #F59E0B 55%, #D97706 100%);
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
    }}
    .devrag-wordmark svg {{
        color: {COLORS["accent"]};
        filter: drop-shadow(0 0 8px rgba(245, 158, 11, 0.4));
    }}

    /* ── Sidebar ─────────────────────────────────────────── */
    section[data-testid="stSidebar"] {{
        background-color: {COLORS["bg_card"]};
        border-right: 1px solid {COLORS["border"]};
        box-shadow: 1px 0 24px rgba(0, 0, 0, 0.25);
    }}
    section[data-testid="stSidebar"] .stMarkdown h2,
    section[data-testid="stSidebar"] .stMarkdown h3 {{
        color: {COLORS["text_muted"]};
        font-weight: 600;
        font-size: 11px;
        letter-spacing: 0.09em;
        text-transform: uppercase;
        margin-bottom: 4px;
    }}

    /* ── Chat input ──────────────────────────────────────── */
    .stChatInput {{
        border: 1px solid {COLORS["border"]};
        border-radius: 14px;
        background: {COLORS["bg_card"]};
        box-shadow:
            inset 0 1px 0 rgba(255, 255, 255, 0.03),
            0 8px 24px rgba(0, 0, 0, 0.35);
        transition: border-color 0.18s ease, box-shadow 0.18s ease;
    }}
    .stChatInput:focus-within {{
        border-color: rgba(245, 158, 11, 0.65);
        box-shadow:
            0 0 0 3px rgba(245, 158, 11, 0.14),
            0 8px 24px rgba(0, 0, 0, 0.4);
    }}

    /* ── Chat messages ───────────────────────────────────── */
    .stChatMessage {{
        border-radius: 14px;
        padding: 16px;
        margin: 8px 0;
        border: 1px solid {COLORS["border"]};
        box-shadow:
            inset 0 1px 0 rgba(255, 255, 255, 0.03),
            0 6px 18px rgba(0, 0, 0, 0.28);
        transition: border-color 0.18s ease;
    }}
    div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-user"]) {{
        background: {COLORS["user_bg"]};
        border-color: rgba(245, 158, 11, 0.22);
        border-left: 2px solid rgba(245, 158, 11, 0.55);
    }}
    div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-assistant"]) {{
        background: {COLORS["assistant_bg"]};
        border-color: {COLORS["border"]};
    }}

    /* ── Buttons ─────────────────────────────────────────── */
    .stButton > button,
    [data-testid="stFormSubmitButton"] button {{
        border-radius: 10px;
        font-weight: 600;
        font-family: {FONT};
        cursor: pointer;
        border: 1px solid {COLORS["border"]};
        background: {COLORS["bg_card"]};
        color: {COLORS["text"]};
        transition:
            border-color 0.18s ease,
            color 0.18s ease,
            background 0.18s ease,
            box-shadow 0.18s ease,
            transform 0.18s ease;
    }}
    .stButton > button:hover,
    [data-testid="stFormSubmitButton"] button:hover {{
        border-color: rgba(245, 158, 11, 0.55);
        color: #FBBF24;
        background: {COLORS["bg_hover"]};
    }}
    .stButton > button:focus-visible,
    [data-testid="stFormSubmitButton"] button:focus-visible,
    .streamlit-expanderHeader:focus-visible {{
        outline: 2px solid {COLORS["accent"]};
        outline-offset: 2px;
    }}
    .stButton > button[kind="primary"],
    .stButton > button[data-testid="stBaseButton-primary"],
    [data-testid="stFormSubmitButton"] button[kind="primary"] {{
        background: linear-gradient(180deg, #FBBF24 0%, #F59E0B 60%, #E8900A 100%);
        color: #1A1200;
        border-color: rgba(251, 191, 36, 0.6);
        font-weight: 700;
        letter-spacing: 0.01em;
        box-shadow:
            inset 0 1px 0 rgba(255, 255, 255, 0.3),
            0 4px 14px rgba(245, 158, 11, 0.22);
    }}
    .stButton > button[kind="primary"]:hover,
    .stButton > button[data-testid="stBaseButton-primary"]:hover,
    [data-testid="stFormSubmitButton"] button[kind="primary"]:hover {{
        background: linear-gradient(180deg, #FCD34D 0%, #F59E0B 60%, #E8900A 100%);
        border-color: #FBBF24;
        color: #1A1200;
        transform: translateY(-1px);
        box-shadow:
            inset 0 1px 0 rgba(255, 255, 255, 0.35),
            0 6px 20px rgba(245, 158, 11, 0.32);
    }}
    .stButton > button[kind="primary"]:active,
    [data-testid="stFormSubmitButton"] button[kind="primary"]:active {{
        transform: translateY(0);
    }}

    /* ── Inputs ──────────────────────────────────────────── */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {{
        border-radius: 10px;
        border: 1px solid {COLORS["border_input"]};
        background: {COLORS["bg"]};
        color: {COLORS["text"]};
        font-family: {FONT_MONO};
        font-size: 13px;
        transition: border-color 0.18s ease, box-shadow 0.18s ease;
    }}
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {{
        border-color: {COLORS["accent"]};
        box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.15);
    }}

    /* ── Expanders ───────────────────────────────────────── */
    .streamlit-expanderHeader {{
        background: {COLORS["bg_card"]};
        border: 1px solid {COLORS["border"]};
        border-radius: 10px;
        color: {COLORS["text"]};
        font-weight: 600;
        cursor: pointer;
        transition: border-color 0.18s ease, box-shadow 0.18s ease;
    }}
    .streamlit-expanderHeader:hover {{
        border-color: rgba(245, 158, 11, 0.45);
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25);
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
        border: 1px solid {COLORS["border"]};
    }}

    /* ── Empty state ─────────────────────────────────────── */
    .empty-state {{
        text-align: center;
        padding: 80px 40px;
        color: {COLORS["text_dim"]};
    }}
    .empty-state .icon {{
        display: flex;
        justify-content: center;
        margin-bottom: 16px;
        color: {COLORS["accent"]};
        filter: drop-shadow(0 0 16px rgba(245, 158, 11, 0.45));
    }}
    .empty-state h3 {{
        color: {COLORS["text"]};
        font-size: 18px;
        font-weight: 600;
        margin: 0 0 8px 0;
        letter-spacing: -0.02em;
    }}
    .empty-state p {{
        font-size: 14px;
        max-width: 360px;
        margin: 0 auto;
        line-height: 1.6;
    }}

    /* ── Result cards (prepared for ticket #02) ──────────── */
    .result-card {{
        background: {COLORS["bg_card"]};
        border: 1px solid {COLORS["border"]};
        border-radius: 12px;
        padding: 14px 16px;
        margin: 8px 0;
        box-shadow:
            inset 0 1px 0 rgba(255, 255, 255, 0.03),
            0 4px 14px rgba(0, 0, 0, 0.22);
        transition: border-color 0.18s ease, box-shadow 0.18s ease;
    }}
    .result-card:hover {{
        border-color: rgba(245, 158, 11, 0.45);
        box-shadow:
            inset 0 1px 0 rgba(255, 255, 255, 0.04),
            0 6px 20px rgba(0, 0, 0, 0.32);
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
        color: {COLORS["accent"]};
    }}
    .result-card .result-name {{
        font-weight: 600;
        color: {COLORS["text"]};
        font-size: 14px;
    }}
    .result-card .result-meta {{
        font-size: 12px;
        color: {COLORS["text_muted"]};
    }}

    /* ── Utility ─────────────────────────────────────────── */
    .section-divider {{
        border: none;
        border-top: 1px solid transparent;
        background: linear-gradient(
            90deg,
            transparent,
            {COLORS["border"]},
            transparent
        );
        margin: 24px 0;
    }}
    .accent-text {{
        color: {COLORS["accent"]};
    }}
    .muted-text {{
        color: {COLORS["text_muted"]};
        font-size: 12px;
    }}
    .example-chip {{
        display: inline-block;
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid {COLORS["border"]};
        border-radius: 999px;
        padding: 7px 16px;
        font-size: 13px;
        font-family: {FONT_MONO};
        color: {COLORS["text_dim"]};
        margin: 4px 5px;
        transition: background 0.18s ease, border-color 0.18s ease;
    }}
    .example-chip:hover {{
        background: rgba(245, 158, 11, 0.06);
        border-color: rgba(245, 158, 11, 0.35);
        color: {COLORS["text"]};
    }}
    .stMarkdown a:focus-visible {{
        outline: 2px solid {COLORS["accent"]};
        outline-offset: 2px;
        border-radius: 4px;
    }}

    /* ── Hide Streamlit branding ─────────────────────────── */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}
    </style>
    """,
        unsafe_allow_html=True,
    )


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
            badge_color, badge_label = badge_colors.get(file_ext, ("#8B94A3", file_ext.upper()))

            # Score color
            if score_pct >= 70:
                score_color = COLORS["success"]
            elif score_pct >= 40:
                score_color = COLORS["accent"]
            else:
                score_color = COLORS["text_muted"]

            # Expandable card for each result
            with st.expander(
                f"[{i}] {c.name or file_name} — {file_name} L{c.start_line}–{c.end_line}",
                expanded=(i == 1),
            ):
                # Header with badge and score
                safe_name = _html_escape(str(c.name or file_name))
                safe_file_name = _html_escape(file_name)
                st.markdown(
                    f"""
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                    <div>
                        <span style="font-weight:600; color:{COLORS["text"]}; font-size:15px;">{safe_name}</span>
                        <span style="color:{COLORS["text_muted"]}; font-size:12px; margin-left:8px;">{safe_file_name} → L{c.start_line}–{c.end_line}</span>
                    </div>
                    <div style="display:flex; align-items:center; gap:8px;">
                        <span style="background:{badge_color}20; color:{badge_color}; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:600;">{badge_label}</span>
                        <span style="color:{score_color}; font-size:12px; font-weight:600; font-family:{FONT_MONO};">{score_pct}%</span>
                    </div>
                </div>
                """,
                    unsafe_allow_html=True,
                )

                # Docstring if available
                if c.docstring:
                    safe_docstring = _html_escape(c.docstring[:300])
                    st.markdown(
                        f"""
                    <div style="background:{COLORS["bg"]}; border:1px solid {COLORS["border"]}; border-radius:6px; padding:10px 12px; margin-bottom:12px; font-size:13px; color:{COLORS["text_dim"]}; line-height:1.5;">
                        {safe_docstring}
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )

                # Full code with copy button (st.code has built-in copy)
                lang = (
                    file_ext
                    if file_ext in ("py", "javascript", "typescript", "bash", "http")
                    else ""
                )
                if lang == "py":
                    lang = "python"
                st.code(c.content, language=lang if lang else None, line_numbers=True)

                # Metadata footer
                meta_parts = []
                if c.parent_class:
                    meta_parts.append(f"Class: `{_html_escape(c.parent_class)}`")
                if c.metadata.get("args"):
                    safe_args = _html_escape(", ".join(c.metadata["args"][:5]))
                    meta_parts.append(f"Args: {safe_args}")
                if c.metadata.get("heading_path"):
                    safe_path = _html_escape(" → ".join(c.metadata["heading_path"]))
                    meta_parts.append(f"Section: {safe_path}")
                if meta_parts:
                    st.markdown(
                        f"""
                    <div style="font-size:11px; color:{COLORS["text_muted"]}; padding-top:8px; border-top:1px solid {COLORS["border"]};">
                        {"&nbsp;&nbsp;·&nbsp;&nbsp;".join(meta_parts)}
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )


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
        st.session_state.chunk_types = [
            "function",
            "class",
            "method",
            "markdown",
            "module_docstring",
        ]

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
        st.markdown(
            f"""
        <div style="padding: 4px 0 20px 0;">
            <div class="devrag-wordmark">{icon("lightning", 20)}<span>DevRAG</span></div>
            <div style="font-size: 12px; color: {COLORS["text_muted"]}; margin-top: 4px;">Local code intelligence</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        st.markdown("### Index")

        repo_path = st.text_input(
            "Codebase path",
            value=str(Path(__file__).parent.parent),
            label_visibility="collapsed",
            placeholder="/path/to/your/repo",
        )

        if st.button("Index", type="primary", use_container_width=True):
            # C-1: Validate path to prevent arbitrary filesystem read
            allowed_root = Path(__file__).parent.parent.resolve()
            try:
                resolved = Path(repo_path).resolve()
                if not resolved.is_relative_to(allowed_root):
                    st.error(
                        "Path must be within the project directory for security. "
                        f"Use a path under: `{allowed_root}`"
                    )
                    st.stop()
            except (ValueError, OSError):
                st.error("Invalid path.")
                st.stop()

            with st.spinner("Scanning and indexing..."):
                chunks = ingest_directory(str(resolved))
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
            st.markdown(
                f"""
            <div style="display:flex; align-items:center; gap:6px; font-size:12px; color:{COLORS["success"]};">
                <span style="width:6px; height:6px; border-radius:50%; background:{provider_colors.get(provider, COLORS["success"])}; display:inline-block;"></span>
                {provider_names.get(provider, provider)} connected
            </div>
            """,
                unsafe_allow_html=True,
            )
            if st.button("Change API Key", type="secondary", use_container_width=True):
                st.session_state.show_key_change = True
                st.rerun()
        else:
            st.markdown(
                f"""
            <div style="display:flex; align-items:center; gap:6px; font-size:12px; color:{COLORS["text_muted"]};">
                <span style="width:6px; height:6px; border-radius:50%; background:{COLORS["text_muted"]}; display:inline-block;"></span>
                No API key — fallback mode
            </div>
            """,
                unsafe_allow_html=True,
            )
            if st.button("Add API Key", type="secondary", use_container_width=True):
                st.session_state.show_key_change = True
                st.rerun()

        # API key change modal
        if st.session_state.get("show_key_change", False):
            with st.expander("Update API Key", expanded=True):
                # Provider selection
                new_provider = st.selectbox(
                    "Provider",
                    options=["gemini", "groq", "openai"],
                    format_func=lambda x: {
                        "gemini": "Google Gemini",
                        "groq": "Groq",
                        "openai": "OpenAI",
                    }[x],
                    key="new_provider_select",
                )
                placeholders = {"gemini": "AIzaSy...", "groq": "gsk_...", "openai": "sk-..."}
                new_key = st.text_input(
                    "API Key",
                    type="password",
                    placeholder=placeholders[new_provider],
                    key="new_api_key_input",
                )
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Save", type="primary", use_container_width=True):
                        if new_key:
                            # Validate
                            valid = True
                            if new_provider == "gemini" and not new_key.startswith("AIza"):
                                st.error("Gemini keys start with AIza")
                                valid = False
                            elif new_provider == "groq" and not new_key.startswith("gsk_"):
                                st.error("Groq keys start with gsk_")
                                valid = False
                            elif new_provider == "openai" and not new_key.startswith("sk-"):
                                st.error("OpenAI keys start with sk-")
                                valid = False

                            if valid:
                                st.session_state.api_key = new_key
                                st.session_state.provider = new_provider
                                st.session_state.show_key_change = False
                                st.success("API key updated")
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
                    if st.checkbox(
                        label, value=ext in st.session_state.file_types, key=f"ft_{ext}"
                    ):
                        selected_file_types.append(ext)
            if selected_file_types:
                st.session_state.file_types = selected_file_types

            # Chunk type filter
            chunk_type_options = ["function", "class", "method", "markdown", "module_docstring"]
            chunk_labels = {
                "function": "Functions",
                "class": "Classes",
                "method": "Methods",
                "markdown": "Markdown",
                "module_docstring": "Docstrings",
            }
            selected_chunk_types = []
            for ct in chunk_type_options:
                if st.checkbox(
                    chunk_labels[ct], value=ct in st.session_state.chunk_types, key=f"ct_{ct}"
                ):
                    selected_chunk_types.append(ct)
            if selected_chunk_types:
                st.session_state.chunk_types = selected_chunk_types

    # ── Main area ──────────────────────────────────────────
    # Header
    st.markdown(
        f"""
    <div class="devrag-header">
        <div class="logo">{icon("lightning", 30)}</div>
        <div>
            <h1>DevRAG</h1>
            <p class="tagline">Ask questions about any local codebase</p>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # Check if API key is set
    api_key = _get_api_key()
    if not api_key:
        # Show API key setup screen
        st.markdown(
            f"""
        <div style="text-align:center; padding:60px 40px; background:{COLORS["bg_card"]}; border:1px solid {COLORS["border"]}; border-radius:16px; margin:20px 0; box-shadow: inset 0 1px 0 rgba(255,255,255,0.03), 0 8px 24px rgba(0,0,0,0.28);">
            <div style="display:flex; justify-content:center; margin-bottom:16px; color:{COLORS["accent"]}; filter:drop-shadow(0 0 14px rgba(245,158,11,0.4));">{icon("key", 44)}</div>
            <h2 style="color:{COLORS["text"]}; margin-bottom:8px; letter-spacing:-0.02em;">Welcome to DevRAG</h2>
            <p style="color:{COLORS["text_dim"]}; font-size:14px; max-width:400px; margin:0 auto;">
                Choose your AI provider and enter your API key to get started.
            </p>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # Provider selection
        st.markdown(
            f"""
        <div style="text-align:center; margin:20px 0 10px; color:{COLORS["text"]}; font-weight:600;">
            Choose your AI provider
        </div>
        """,
            unsafe_allow_html=True,
        )

        providers = {
            "gemini": {
                "name": "Google Gemini",
                "desc": "Free tier available",
                "color": "#4285F4",
                "url": "https://aistudio.google.com/apikey",
                "placeholder": "AIzaSy...",
            },
            "groq": {
                "name": "Groq",
                "desc": "Fast inference, free tier",
                "color": "#F55036",
                "url": "https://console.groq.com/keys",
                "placeholder": "gsk_...",
            },
            "openai": {
                "name": "OpenAI",
                "desc": "GPT-4o mini",
                "color": "#10A37F",
                "url": "https://platform.openai.com/api-keys",
                "placeholder": "sk-...",
            },
        }

        cols = st.columns(3)
        for idx, (_key, info) in enumerate(providers.items()):
            with cols[idx]:
                st.markdown(
                    f"""
                <div style="background:{COLORS["bg_card"]}; border:2px solid {COLORS["border"]}; border-radius:8px; padding:16px; text-align:center; height:100px;">
                    <div style="font-size:20px; font-weight:700; color:{info["color"]};">{info["name"]}</div>
                    <div style="font-size:12px; color:{COLORS["text_dim"]}; margin-top:4px;">{info["desc"]}</div>
                </div>
                """,
                    unsafe_allow_html=True,
                )

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
            submitted = st.form_submit_button(
                "Start Using DevRAG →", type="primary", use_container_width=True
            )

            if submitted and user_api_key:
                # Validate key format
                valid = True
                if selected_provider == "gemini" and not user_api_key.startswith("AIza"):
                    st.error("Gemini keys start with **AIzaSy**")
                    valid = False
                elif selected_provider == "groq" and not user_api_key.startswith("gsk_"):
                    st.error("Groq keys start with **gsk_**")
                    valid = False
                elif selected_provider == "openai" and not user_api_key.startswith("sk-"):
                    st.error("OpenAI keys start with **sk-**")
                    valid = False

                if valid:
                    st.session_state.api_key = user_api_key
                    st.session_state.provider = selected_provider
                    st.success(f"{provider_info['name']} connected")
                    st.rerun()
            elif submitted:
                st.error("Please enter an API key")

        # Get key link
        st.markdown(
            f"""
        <div style="text-align:center; margin-top:12px;">
            <a href="{provider_info["url"]}" target="_blank" style="color:{COLORS["accent"]}; font-size:13px;">
                Don't have a key? Get one free →
            </a>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # Skip option
        st.markdown(
            f"""
        <div style="text-align:center; margin-top:16px;">
            <span style="color:{COLORS["text_muted"]}; font-size:13px;">
                Or continue in <strong>fallback mode</strong> (raw code snippets instead of AI explanations).
            </span>
        </div>
        """,
            unsafe_allow_html=True,
        )

        if st.button("Continue without AI →", type="secondary", use_container_width=True):
            st.session_state.api_key = ""
            st.rerun()

        return

    # Empty state with example queries
    if not st.session_state.indexed:
        st.markdown(
            f"""
        <div class="empty-state">
            <div class="icon">{icon("lightning", 48)}</div>
            <h3>Point at a codebase</h3>
            <p>Enter a path in the sidebar and click <strong>Index</strong> to start asking questions about your code.</p>
        </div>
        """,
            unsafe_allow_html=True,
        )
        return

    # Ready state — show example queries
    if "query_history" not in st.session_state:
        st.session_state.query_history = []

    if not st.session_state.query_history:
        st.markdown(
            f"""
        <div style="text-align:center; padding:40px 20px 20px; color:{COLORS["text_dim"]};">
            <div style="font-size:14px; margin-bottom:16px;">Try asking:</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        example_queries = [
            "How does user authentication work?",
            "What is the cache invalidation strategy?",
            "How are database migrations handled?",
            "How does the rate limiting work?",
            "What payment gateways are supported?",
        ]
        for eq in example_queries:
            st.markdown(
                f"""
            <div style="text-align:center; margin:4px 0;">
                <span class="example-chip">{eq}</span>
            </div>
            """,
                unsafe_allow_html=True,
            )

    # Chat
    query = st.chat_input("Ask a question about the code...")
    if query:
        # Show user message immediately
        st.chat_message("user").write(query)

        # Search phase
        with st.status("Searching the codebase…", expanded=False) as status:
            st.write("Tokenizing query…")
            raw_results = st.session_state.retriever.search_rrf(
                query, top_k=st.session_state.top_k * 3
            )
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
            status.update(label="Search complete", state="complete", expanded=False)

        # Generation phase
        with st.status("Reading code & composing an answer…", expanded=False) as status:
            st.write("Analyzing code context…")
            answer = generate_response(query, filtered_results)
            status.update(label="Answer ready", state="complete", expanded=False)

        st.chat_message("assistant").markdown(answer)

        render_sources(filtered_results)


if __name__ == "__main__":
    main()
