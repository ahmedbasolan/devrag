# Spec: Visual & Search Improvements

## Problem

DevRAG works but looks like a default Streamlit app. The UI is generic and immediately recognizable as AI-generated. Search quality suffers from naive tokenization and overly-small markdown chunks. Results are presented as plain text with no visual hierarchy or interactivity.

## Goals

1. **Distinctive visual identity** — custom palette, professional typography, intentional design. Not generic.
2. **Better search recall** — code-aware tokenization and smarter chunking mean more relevant results.
3. **Actionable results** — users can copy code, explore sources, and understand relevance at a glance.

## Non-goals

- No new retrieval algorithms (RRF stays as-is)
- No new LLM integrations
- No mobile app
- No authentication/user accounts

## Success criteria

- Visual: blind test — observers cannot identify it as "AI-generated" vs "hand-designed"
- Search: BM25 recall improves by ≥20% on the eval suite
- UX: time-to-insight reduces (user finds relevant code faster)
