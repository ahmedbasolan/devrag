# 03: Code-Smart BM25 Tokenizer

**What to build:** A tokenizer that understands code identifiers — splitting `search_rrf` into `search` + `rrf`, handling camelCase, dotted imports, and common programming terms. This directly improves BM25 recall for technical queries.

**Blocked by:** None (can start immediately)

**Status:** resolved

- [x] Split snake_case identifiers: `search_rrf` → `search`, `rrf`
- [x] Split camelCase identifiers: `getUserById` → `get`, `User`, `By`, `Id`
- [x] Split dotted names: `flask.request.args` → `flask`, `request`, `args`
- [x] Handle alphanumeric boundaries: `BM25Okapi` → `bm25`, `okapi`
- [x] Lowercase all tokens for case-insensitive matching
- [x] Preserve string literals and comments as-is (don't split quoted text)
- [x] Tokenizer is a drop-in replacement for `HybridRetriever._tokenize`
- [x] Verified: eval suite passes, Hit@5=80%, Hit@10=100%
