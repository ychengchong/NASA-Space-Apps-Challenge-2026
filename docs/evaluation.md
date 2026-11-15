# Evaluation and submission evidence

Status: two held-out rounds were run with `gpt-6-luna` on 15 November 2026, each graded by
automated checks and two AI graders, not by people. Neither gate is met in either round.
Round 2, on new suites, is the current evidence:

- Planner/discovery passed 60 of 70 cases (85.7%, below the 90% target), with 3 critical
  fabricated citations in discovery.
- RAG passed 65 of 77 cases (84.4%, below 90%) under the automated checks and both graders
  combined, with no critical error.

See the [evaluation results](evaluation-results.md), which keep round 1 as history. No
student study has been run.
This protocol implements the planned [Draft 5 release gates](technical-spec.md#12-build-plan-and-submission).
Existing software checks are recorded separately in [verification](verification.md).

## Submission-day follow-up

The follow-up uses `gpt-6-luna` with a USD 1 cumulative evaluation ledger, preserving
the configured daily request allowance rather than overriding it with USD 5. Existing
development cases were used to diagnose product-mismatched discovery citations and
over-specific selection for broad goals. They remain development evidence.

[Prospective confirmation suites](../backend/evaluation/submission-day/README.md) contain
50 planner/discovery and 40 explanation questions, plus a matched no-retrieval run.
Their questions/expectations are fixed before their first prospective calls. They were
written by the implementing agent, not independently or by a person. Automated scores
and pending source-support review must be distinguished; no new activation attestation
is implied. The older round-2 scores above remain historical evidence for the prior code.
User testing was deferred by the team for the submission deadline and was not conducted.

## Student interpretation study

Use the same tasks with at least five target students. Record assistance and errors,
not names or private chat. Obtain participants' agreement before observing them.
Predefine success before running the study and report every attempt.

1. Open the annual T2M example. Identify the NASA source, cell, dates and units.
2. State the estimated rate and distinguish it from the evidence for a trend.
3. Compare two places and identify the common analysis years.
4. Explain why a missing-year or source-transition case has no significance result.
5. Complete the interpretation lesson, then explain why non-significance is not
   proof of no change and why significance does not establish causation.

Record completion, assistance, time and interpretation errors by task. Report the
sample size, all failures and changes made. Do not invent outcome percentages.

The ready kit for these tasks, with a consent script, predefined success criteria, an
observation sheet, assistance and error codes and reporting rules, is the
[user study kit](user-study-kit.md). No observations have been made with it yet. The two
guided teacher walkthroughs built on the same frozen examples are in
[walkthroughs](walkthroughs.md).

## Planner semantic confirmation suite

Record exact provider/model/digest/quantization, licence, hardware, application
commit, prompt/schema version, context/output bounds and timing environment.
Keep confirmation questions separate from prompt development examples.

Predeclare >=90% correct resolution or appropriate clarification on the fixed
suite, zero critical unsupported numeric/verdict claims, and a practical latency
bound for the available hardware before activating AI. Report counts and uncertainty.
Use at least fifty held-out planner/discovery questions covering simple cases, broad
investigation goals, source-backed variable suggestions, named periods, unspecified
periods, leap/DJF cases, ambiguous cities, unknown variables, unsupported dates,
forecasting, misleading premises, invalid JSON/types, prompt injection and long inputs.
Expected behavior must be written before querying the model. A valid JSON object
alone does not count as semantic success. Include cancellation/provider failure.

OpenAI is the selected path for new discovery/RAG work. The evaluated model is
`gpt-6-luna`; its identities and results are in the [evaluation results](evaluation-results.md).
AI_EVALUATED, DISCOVERY_EVALUATED and RAG_EVALUATED are owner activation
attestations after recording evidence, not automatically measured success claims. Only
the owner sets them to true, or someone the owner has delegated the decision to. An AI
agent may otherwise report that a gate's evidence is met, but does not set the flag.

For round 2 the lead agent of the evaluation workflow reports that the owner delegated the
gate decisions to it on 15 November 2026. Under the rules below, it set
`DISCOVERY_EVALUATED=false` and `RAG_EVALUATED=false`, because neither gate passed. The
rules it applied:

- The planner/discovery gate passes only if at least 90% of the held-out planner cases pass
  and there are zero critical errors. Citation support counts if either grader judges it
  unsupported.
- The RAG gate passes only if the combined pass rate is at least 90% and there are zero
  critical errors. A case passes the combined verdict only when the automated checks and
  both graders all pass it.

## Planned RAG confirmation suite

Prepare at least forty held-out questions with expected supporting source sections
or an explicit no-evidence outcome. Cover definitions, source/grid context, limitations,
conflicting or absent evidence, invalid citations, misleading causal premises,
wrong-investigation binding, navigation/cancellation and prompt injection. Do not
include test questions or answer keys in the retrieval corpus.

Evaluate retrieval relevance separately from answer support/citation correctness.
Predeclare a >=90% fully supported-answer-or-appropriate-abstention target, and zero
invented numerical findings, unsupported verdict changes, fabricated citations or
successful instruction/secret-access injections in the release suite. Citation IDs
and schema validity alone are not evidence that a passage supports an answer.

Run matched RAG/no-RAG conditions on the same questions and record regressions as
well as improvements. Freeze corpus/model/prompt/schema identities and report all
counts, uncertainty, latency, timeouts and generation/retrieval costs. Set practical
latency/cost limits before running the suite; measure ingestion/storage separately.
AI targets remain release requirements, not achieved outcomes. The team deferred the
user study for this submission; it remains a future validation target, and no measured
usability or educational impact is claimed.

## Final public demonstration

Verify one complete HTTPS investigation and a copied pinned link in a fresh session;
check phone-width layout, keyboard controls, CSV/evidence downloads and missing-pin
errors. Confirm the named state volume survives replacing the application container.
Choose the organizer's 30-second video or seven-slide presentation format. Explain:
problem/audience, NASA dataset and its contribution, one real investigation, rate,
conditional evidence/unavailable states, limitations, and observed impact. Add the
public project/supporting-material URL. Do not promise a winner percentile.
