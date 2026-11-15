# Submission-day prospective confirmation

Prepared on 15 November 2026 by OpenAI Codex, the same agent implementing the fixes.
These are fresh question texts, not independently authored or human-reviewed cases.
Do not call this a blind independent evaluation or treat automated checks as proof of
source entailment. A teammate must review the answers and citations before activation.

The final suite files are frozen before their first prospective model call:

| Suite | Cases | SHA-256 |
| --- | --- | --- |
| `planner_suite.json` | 50: 25 plan, 25 discover | `d9c5fb28e7d0b302321f60914e155b7d25db732e124420ddc935ee9eda864f01` |
| `rag_suite.json` | 40 | `6e6c863cc2c42d00f62ee9391cb5d70674821e8b6c1beb2478fa3a7c7dd44613` |

`suite-freeze.json` records these hashes. `suite-freeze-preparation.json` preserves an
earlier, unused preparation hash: five redundant named-variable questions were replaced
with broad/unsupported/ambiguous goals before any prospective calls. No expectations
are changed after the first prospective call. The earlier development suites remain
development evidence; fixes were based on those cases, not these confirmation answers.

The questions cover supported variables, comparisons, seasons, ambiguous/unknown places,
broad goals, unsupported quantities and forecasts. Explanations cover methods, result
references, dataset context, limits, unsupported requests, injection and a new plan.
This is a small, agent-authored sample. The earlier adversarial suites and software
tests provide additional coverage, not a guarantee of generalisation.

Predeclared target: at least 45/50 planner/discovery and 36/40 explanation cases pass,
with zero critical factual/citation/injection errors. A full pass requires source-support
review as well as the runner's checks. Every failure and abstention is reported. Both
explanation conditions use the same questions, model, prompts, schema, corpus identity
and guards. The no-retrieval condition cannot cite evidence and will withhold unsupported
answers; this compares the app's retrieval conditions, not unrestricted chatbot ability.

The runner records provider identity, instructions/schema hashes, corpus/version,
suite hash, latency, reservations, raw provider output, checked responses and pending
review items. Results are written after every case; a budget refusal leaves the remaining
cases explicitly not run. No paid retries or automatic fallback are performed.

The CLI preserves `AI_DAILY_BUDGET_MICROUSD` and caps its cumulative ledger at the smaller
of that setting and the historical USD 5 ceiling. For this run the limit is USD 1, including
the runner's conservative USD 0.15 prior-smoke allowance. The ledger does not reset with
another suite or scratch directory. Reservations overestimate generation/search costs;
they are not the provider invoice. A USD 0.0025 direct-search reservation is conservative:
the published USD 2.50/1,000 file-search tool rate applies to Responses tool calls, whereas
this app uses direct vector-store search. Storage is accounted separately; the approved
store indexed 194,910 source bytes into 379,943 storage bytes.

NASA fetching is separate from the LLM. The four frozen example investigations are loaded
from retained cached evidence. These questions and answer keys are never uploaded to the
retrieval corpus. Release activation flags in the local `.env` remain false; evaluation
enables capabilities only in its own process to measure them.
