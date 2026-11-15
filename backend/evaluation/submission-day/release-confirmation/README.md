# RAG source-support confirmation

Frozen before paid calls on 15 November 2026, after the user approved a **USD 2 total
evaluation cap**. The existing ledger and its reservations are preserved. Evaluation
processes use that allowance; the production `.env` daily budget remains **USD 1**.

`rag_suite.json`: 40 fresh questions; SHA-256
`5b068db0abb69fa0b66d8ca9355b90faee73a99e0876797932f10766c7ce9c4a`.
The implementing Codex agent wrote the suite. It is not independently authored or
human reviewed. Earlier questions are development evidence and their scores/keys stay
unchanged. No code, prompt, schema or expectation changes occur during these runs.

Predeclared pass: **at least 36/40** pass automatic status/binding/reference checks
and both source-support reviews, with **zero critical factual/injection errors**.
Each answerable case requires an answer. Unsupported requests may abstain; the causal
attribution control also accepts a supported explanation declining attribution.

Source support is assessed against the actual cited retrieved passages, captured with
checksums. A fixed incomplete section-ID whitelist is not used: a different retrieved
section can be valid evidence if it supports every claim. Existing whitelist-based
benchmarks remain unmodified. Each block's reviewer must copy an actual supporting
quote; invalid quotes, omitted/duplicate block grades or any critical error cannot pass.

Two sequential calls use `scripts.grade_evaluation`, each without the other grade.
Both use the same model family as generation and see the question, checked answer,
canonical investigation context and only its cited passages. These are AI judgments,
not independent human review or proof of truth. An accepted outcome with no displayed
claims is checked statically; an automatic failure cannot be rescued by a grader.
The matched no-retrieval condition uses the same questions, instructions and guards.
It measures this app's retrieval condition, not unrestricted chatbot performance.

Every call pre-reserves costs in the shared ledger. No automatic paid retry or limit
increase is allowed. The public AI activation flags stay off pending teammate review
and the owner's release decision. Full raw outputs and both reviews are retained.
