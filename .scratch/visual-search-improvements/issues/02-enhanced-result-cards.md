# 02: Enhanced Result Cards

**What to build:** Replace the plain-text source citations with visually rich result cards that show relevance scores, syntax-highlighted code previews, and file type indicators — so users can immediately assess which results matter.

**Blocked by:** #01 (needs styling foundation and color palette)

**Status:** resolved

- [x] Each result displayed as a styled card with consistent layout
- [x] Relevance score shown as percentage with color coding (green/amber/gray)
- [x] Code preview with syntax highlighting via `st.code`
- [x] File type badge (Python=blue, Markdown=teal, etc.)
- [x] Source path displayed with line range
- [x] Docstring/summary shown when available (truncated)
- [x] Cards are scannable: name → file → badge → score
- [x] Visual distinction via score color (high=green, mid=amber, low=gray)
