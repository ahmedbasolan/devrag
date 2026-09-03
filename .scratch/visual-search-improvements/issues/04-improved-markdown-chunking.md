# 04: Improved Markdown Chunking

**What to build:** A smarter markdown parser that preserves context — keeps code blocks whole, splits on heading boundaries, and maintains enough surrounding text so chunks are meaningful on their own.

**Blocked by:** None (can start immediately)

**Status:** resolved

- [x] Split on heading boundaries (`#`, `##`, `###`) as primary分割 points
- [x] Preserve fenced code blocks (` ``` `) as atomic units — never split mid-block
- [x] Keep heading + its content together (don't separate `## Auth` from its first paragraph)
- [x] Increased chunk size target to 1000 chars (from 500) for more context
- [x] Split long sections on paragraph boundaries (`\n\n`), not mid-paragraph
- [x] Attached heading hierarchy as metadata: `["Authentication", "Login"]` for nested headings
- [x] Handle tables as complete units (don't split header from rows)
- [x] Verified with `mock_data/docs/api.md` (17 chunks) and `mock_data/docs/decisions.md` (5 chunks)
- [x] Chunk count stable: 138 → 136 (fewer, better chunks)
