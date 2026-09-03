# ADR-0003: Gemini Flash for generation with local fallback

## Status

Accepted

## Context

DevRAG needs to generate natural-language answers from retrieved code chunks. Options:

- **Local LLM**: Full privacy, but requires GPU and adds deployment complexity
- **Cloud API**: No local resources, but costs money and sends code externally
- **Gemini Flash free tier**: Zero cost, fast, sufficient quality for code Q&A. Sends code to Google but only when user explicitly asks a question.

## Decision

Use Google Gemini 2.0 Flash as the primary generator. Fall back to raw chunk display when no API key is set or on error.

- System prompt is tuned for code explanation: "explain WHAT it does and WHY, not HOW"
- Context window limited to top 5 chunks, each truncated to 2000 chars
- Fallback shows raw code with source citations

## Consequences

- Zero cost for typical usage (free tier generous)
- Falls back gracefully — app works without any API key
- Code is sent to Google on each query (privacy consideration)
- Model can be swapped by changing one constant
