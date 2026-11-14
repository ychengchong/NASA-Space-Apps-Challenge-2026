# Evaluation and submission evidence

Status: protocol prepared; no student study or real-model accuracy result is claimed.
This protocol implements the planned [Draft 5 release gates](technical-spec.md#12-build-plan-and-submission).
Existing software checks are recorded separately in [verification](verification.md).

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

OpenAI is the selected path for new discovery/RAG work; no exact model is selected
or approved by this document. AI_EVALUATED is an owner activation
attestation after recording evidence, not an automatically measured success claim.

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
User-study and AI targets are release requirements, not achieved outcomes.

## Final public demonstration

Verify one complete HTTPS investigation and a copied pinned link in a fresh session;
check phone-width layout, keyboard controls, CSV/evidence downloads and missing-pin
errors. Confirm the named state volume survives replacing the application container.
Choose the organizer's 30-second video or seven-slide presentation format. Explain:
problem/audience, NASA dataset and its contribution, one real investigation, rate,
conditional evidence/unavailable states, limitations, and observed impact. Add the
public project/supporting-material URL. Do not promise a winner percentile.
