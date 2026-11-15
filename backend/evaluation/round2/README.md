# Round 2 planner and discovery suites

This directory holds the fresh planner and discovery suites for the second evaluation round
of the Draft 5 release gates (spec section 12; [docs/evaluation.md](../../../docs/evaluation.md)).
Round 1 met neither gate (see [docs/evaluation-results.md](../../../docs/evaluation-results.md)).
These files replace round 1's planner suites for round 2. The round-1 files in the parent
directory stay as they are. This README describes only the planner and discovery files. The
RAG files in this directory (`rag_dev.json`, `rag_suite.json`) come from a separate step,
described in "Round 2 RAG suites" at the end of this file.

| File | Split | Cases | Use |
| --- | --- | --- | --- |
| `planner_dev.json` | development | 14 (11 discover, 3 plan) | Prompt and bound tuning only. Never reported as held-out evidence. |
| `planner_suite.json` | held-out | 70 (45 discover, 25 plan: 64% discover) | Confirmation run with a frozen model, prompt, schema and corpus. |

## Fixed before any model run

An AI (Claude Opus 5.5, working in Claude Code) wrote every case and every expectation in
both files. No person has reviewed them. They were written blind:

- No model was called and the app was not run.
- The round-1 results (`backend/evaluation/results/`) were not opened.
- The round-1 suites were read only for their schema. Every question here is new. None is
  reworded from round 1 or from the smoke questions listed in the parent README, and no
  question appears in both files.
- Only these sources were consulted: the spec, the catalogue (`backend/data/catalogue.json`),
  the corpus manifest and section files, the code of `/api/plan` and `/api/discover` and of
  the runner's suite loader, the request models, and offline calls to the deterministic
  place lookup (`resolve_place_query` / `find_place`). The place lookup was checked so that
  every expected place name is one the server resolves exactly, and every "must ask" name
  matches several reviewed places.
- `scripts/run_evaluation.py`'s `load_suite` accepts both files. That was an offline parse,
  with no request sent.

The files were fixed on 15 November 2026 at 06:08 SGT (2026-11-14 22:08:52 UTC), at
application commit `5bfa2e4`, with uncommitted changes from other agents in the working
tree. No model had seen any case at that time. SHA-256 of the files as fixed:

- `planner_dev.json`: `f2b896643e580bc16d4a2cae7e1daba3813f8ce85d602824caa8021105eff623`
- `planner_suite.json`: `187efe655cfb23989a90f8a1433a24af83b835a2af1f4e84d3cfa49cedd7852f`

Expectations in `planner_suite.json` must not be changed after a held-out run. If a case
proves wrong, record it as a suite error in the results, together with the reason, and
leave the case unchanged.

## Schema

The schema is the one in [backend/evaluation/README.md](../README.md), with three changes.

**IDs.** Held-out cases are `R2-Hnn` and development cases are `R2-DEVnn`, so they cannot
be confused with round 1's `Hnn` and `DEVnn`.

**Coverage.** The held-out file covers all sixteen categories:

| Category | Discover | Plan |
| --- | --- | --- |
| exact request | 3 | 2 |
| broad goal | 4 | 0 |
| source-backed suggestion | 4 | 0 |
| named period | 2 | 2 |
| unspecified period | 3 | 2 |
| leap/DJF season | 3 | 2 |
| ambiguous city | 3 | 2 |
| unknown variable | 3 | 2 |
| unsupported dates | 2 | 2 |
| forecasting | 2 | 2 |
| misleading premise | 3 | 1 |
| injection | 3 | 2 |
| long input | 2 | 1 |
| comparison | 2 | 2 |
| country name | 2 | 1 |
| invalid/odd input | 4 | 2 |

As in round 1, the development file has no long-input or invalid-input case, because
request validation decides those outcomes before any model call.

**Citation support.** This is new in round 2 and fixed before the run. In round 1, a
review after the run found three discovery cases whose suggestions cite a section that does
not support them. That check was not predeclared. Round 2 predeclares it in two parts:

- The suite header `citation_sections_by_variable` lists, for each of the 20 catalogue
  variables, the corpus sections that are about that variable:
  - the variable's catalogue note (`project-variables-NN`);
  - POWER or MERRA-2 sections that describe that same parameter as the app uses it.

  Sections about a different product are not listed for the variable. For example, the
  IMERG precipitation sections (`power-sources-meteorology-21`, `-22`,
  `power-sources-hydrology-18`, `power-methodology-04`) are not listed for `precipitation`,
  which is MERRA-2 PRECTOTCORR. The SMAP soil-moisture sections are not listed for the soil
  wetness variables either. The header `citation_sections_corpus` names the corpus that the
  map was built from.
- Every case has the key `expected.citation_support`:
  - `"every_suggestion"`, on every discover case except the 400 ones: each variable
    suggestion in the response, whatever its status, must cite at least one section listed
    for its own variable. The runner reads the cited sections from `section_id` in the
    response's citations.
  - `"not_applicable"`, on plan cases and 400 cases.

Passing the list check is necessary, not sufficient. The reviewer pass must still read each
reason against the text of every section it cites. A reason that a cited section does not
support is a fabricated citation (the RAG suite's definition), even when the section is on
the list.

A suggestion that cites no section about its own variable, or whose reason a cited section
does not support, fails its case. It is also a **critical error** under spec 12's
fabricated-citation rule. This adds to the critical errors listed in the parent README.

When the files were fixed, the runner in the working tree recorded what the server's own
citation filter kept (`citation_support` in each results case). It did not check this
suite's `expected.citation_support` against `citation_sections_by_variable`. The runner
now does (added after the files were fixed, without changing them): a case with
`"every_suggestion"` gets a `citation_support` check whose detail names every suggested
variable that cites no listed section, and a failed check also records the critical error
`fabricated_citation`. The reviewer pass still has to read each reason against its cited
sections, and the results must say how that pass was done and by whom (an AI must be named
as such).

## Round 2 RAG suites

| File | Split | Cases | Use |
| --- | --- | --- | --- |
| `rag_dev.json` | development | 10 | Prompt and retrieval tuning only. Never reported as held-out evidence. |
| `rag_suite.json` | held-out | 77 | Confirmation run of `POST /api/explain` with a frozen model, prompt, schema and corpus. |

**Fixed before any model run.** An AI (Claude Opus 5.5, working in Claude Code) wrote every
question and every expectation in both files. No person has reviewed them. They were written
blind: no model was called, no retrieval was run and the app was not run against them, and
the round-1 results (`backend/evaluation/results/`) were not opened. The round-1 RAG suites
were read only for their schema and their `must_not` vocabulary. Every question is new: none
appears in a round-1 RAG suite, and no question appears in both round-2 files (checked by
exact text). The spend ledger holds no entry for any round-2 case ID (`r2-NNN`, `r2d-NN`) at
the time below.

**Schema.** As in [backend/evaluation/README.md](../README.md) for the RAG suites, with one
addition: every case has `expected.expected_retrieval_any`, the corpus sections a good
retrieval should return, so retrieval relevance can be scored apart from answer support. An
empty list means no section is on topic, and relevance is not scored for that case. The
scoring notes in each file define this. The held-out file covers fifteen categories and the
development file ten of them, all built on the four
frozen examples (Svalbard annual temperature, Novosibirsk winter temperature, Athens and
Helsinki rainfall, Madison summer haze). They include wrong-investigation binding (4 held-out
cases, 1 development case) and unknown or invalid investigation IDs (3 held-out, 1 development).

**Result-fields note.** The project note "What the result fields mean" (`project-result-fields-01`
to `-09`) was added to the corpus by another agent while these files were being written. Its
sections were then added, still blind, to the cases that ask what a result field means, and
`corpus_version` in both files is the manifest version that includes it
(`1592032ec6d77064140a4ad4c1e2666c81c885f1bb78721d3ce10570edf4037c`). If the corpus changes
again, a held-out run must record the mismatch and must not edit the expectations.

The files were fixed on 15 November 2026 at 10:05 SGT (2026-11-15 02:05 UTC), at application
commit `5bfa2e4`, with uncommitted changes from other agents in the working tree. SHA-256 of
the files as fixed:

- `rag_dev.json`: `5992a11bc2f5f97eff0d302754f93f1a1ddd3e1cebfd450ed0e12647623a433c`
- `rag_suite.json`: `e3b763b97cc2b57a61a737eb97e82dfee520139c2db4eca4fc216297049e3d78`

Expectations in `rag_suite.json` must not be changed after a held-out run. If a case proves
wrong, record it as a suite error in the results, with the reason, and leave the case
unchanged.

When the files were fixed, the runner checked `sections_any` but did not score
`expected_retrieval_any`. It now does (added after the files were fixed, without changing
them): each case with a non-empty list records `retrieval_relevance` (relevant when any
search of the case returned a listed section, with the hits and every returned section),
and the report counts the scored and relevant cases and names the others. As the scoring
notes say, this is apart from the pass result. The results must say how the reviewer pass
was done and by whom (an AI must be named as such).
