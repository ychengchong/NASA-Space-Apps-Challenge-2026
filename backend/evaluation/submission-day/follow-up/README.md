# Fresh-wording follow-up confirmation

Prepared before the calls on 15 November 2026, after the first submission-day suite became
development evidence. Same implementing agent; these are not independently authored or
blind human-reviewed tests. No original answer key or score is changed.

| Suite | Cases | SHA-256 |
| --- | --- | --- |
| `planner_suite.json` | 50 | `9b90a16e609ac5d9d094fee7744de658cc5eb17723f6612af783001353eb4c06` |
| `rag_suite.json` | 40 | `09104f7eef02bb279f6f13b3f532d34db9902c6c43daaf7dc38a0fc4195a5aff` |

`suite-freeze.json` freezes the expectations before the first follow-up call. Questions
use fresh wording on the same topics; this is a follow-up sample, not evidence of broad
independent generalisation. No prompt/code/answer-key tuning occurs during these runs.

The first run found five requests for ambiguous Athens that safely asked for a location,
one missed explicit season, missing context for some explanation questions and two guard
false positives. Some correct citations were also outside that run's predeclared source
list. Those failures remain in its recorded 44/50 and 29/40 automated results.

Before these follow-up calls, the guards exclude the app name from outcome verbs and
recognize trusted result-field identifiers while still rejecting actual URLs. Method
queries add grid-cell, comparison, seasonal-scope and unit-field context. Both planner
prompts explicitly preserve month ranges. Ambiguous names now have predeclared expected
clarification rather than an arbitrary geographic choice. The source lists explicitly
include reviewed alternative result-field documentation; unrelated sources are not
accepted merely because they mention a word in the question.

The target remains 45/50 planner/discovery and 36/40 explanations, zero critical factual
errors, with source-support review required in addition to automated checks. The matched
no-retrieval condition uses the same 40 questions and guards. The shared cumulative USD 1
ledger includes all earlier calls; it is neither reset nor raised for this follow-up.
See the parent README for accounting and independence limitations. Release activation
flags remain off until the required review and gate decision.

## Review without spending

Start with [the review packet](results/teammate-review.md), the raw result files and
the delivery summary in `../results/summary.json`. Reading reports makes no API calls.
From `backend/`, these commands also only read saved results:

```powershell
uv run python -m scripts.run_evaluation --report evaluation/submission-day/follow-up/results/planner.json
uv run python -m scripts.run_evaluation --report evaluation/submission-day/follow-up/results/rag.json --compare evaluation/submission-day/follow-up/results/rag-no-retrieval.json
```

The final candidate has later targeted fixes; the complete prospective scores above
are not a new full validation of those final changes. Do not reset the ledger or raise
the limit to rerun automatically. A future full run needs an approved budget, accurate
predeclared source expectations and the required source-support review. Evaluation-only
activation overrides must stay in the test process, not become production attestations.
