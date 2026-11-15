# Draft 5: what is done and what remains

Updated on 15 November 2026 for branch `fix-draft5-release`. This list follows the
[Draft 5 checklist](technical-spec.md#draft-5-planned-delivery-checklist) and
[spec section 12](technical-spec.md#12-build-plan-and-submission). It was written by an AI
agent (Claude Code, Claude Opus 5.5) from the repository's own records. Codex added the
submission-day fixes and testing records; human review is still pending.

## Submission-day review

The team deferred user testing for the 15 November deadline. Record it as not conducted;
do not claim observed usability or educational impact. It is not needed to run the
cached prototype demonstration.

Follow-up branch `fix-draft5-release` fixes Windows corpus bytes and binds explanation
checks to each block's named/referenced places. The four cached NASA examples and
downloads passed with outbound requests blocked; checks are recorded in
[verification](verification.md#submission-day-fixes-and-offline-checks).

Teammate review before merging or enabling AI:

1. Review `.gitattributes`, `build_corpus.py`, `ai_guard.py`, `adapters/explain.py` and
   their regression tests. Confirm withholding an ambiguous mixed-outcome block is
   preferable to displaying a potentially incorrect claim.
2. Review the three recorded discovery citation failures R2-H17, R2-H39 and R2-H45
   against the original passages and grader reasons. A variable-name mention proves
   neither that a source explains the variable nor that it supports the generated reason.
   This branch does not claim to have solved factual support for arbitrary answers.
3. Review the NASA source documents and project notes as different evidence types.
   Confirm corpus provenance, source links and explanations of the scientific limits.
4. Keep discovery/explanations disabled. Changes invalidate the old live-model gate
   evidence; passing unit tests is not passing the semantic evaluation. Run a fresh,
   predeclared held-out suite only with a locally configured key and approved budget.
5. Open the saved Svalbard and Athens/Helsinki examples before recording the demo.
   Describe precipitation as exploratory/descriptive and the climate grid as distinct
   from a local weather station. Do not claim causal attribution or forecasts.

Public deployment and the demo/submission are still outstanding. The build table below
retains PR #8 baseline claims; the remaining-work sections include the follow-up. See
[current results](evaluation-results.md#submission-day-follow-up) and the
[teammate review packet](../backend/evaluation/submission-day/follow-up/results/teammate-review.md).

## Done

| Area | What exists | Evidence |
| --- | --- | --- |
| AI plumbing | `backend/app/ai.py`: bounded requests, one generation at a time, rate and daily-turn limits, budget reserved before every call, OpenAI Responses with `store=false` and strict schemas, vector-store search with its own charge | Unit tests with fake providers |
| Contracts | Spec 5 discovery and explanation types in `models.py`, generated TypeScript types, separate capability flags for planner, discovery and explanation | Unit tests |
| Document corpus | 23 sources (13 NASA POWER and GMAO pages, 10 project notes), sectioned and hashed in `backend/data/corpus/manifest.json`; owner-run build and upload scripts; uploaded to an OpenAI vector store (expires 30 days after last use) | `docs/verification.md`, `state/corpus-files.json` (local) |
| Guided discovery | `POST /api/discover`: up to three cited variable suggestions, typed clarification questions, a proposal that still needs confirmation; question-bar interface | Unit tests; live smoke tests; demo video |
| Cited explanations | `POST /api/explain` and the "Ask about this investigation" panel: the investigation is rebuilt from pinned snapshots without calling NASA, numbers appear only through allowlisted result fields, citations come from the manifest | Unit tests; live smoke tests; demo video |
| Output guard | `backend/app/ai_guard.py` withholds unretrieved or non-supporting citations, stray numbers, URLs, causal or forecast claims and text that contradicts the verdict | Unit tests, including adversarial strings |
| Evaluation | Two held-out rounds with blind suites (round 1: 75 + 65 cases; round 2: 70 + 77 cases plus 77 matched no-retrieval cases), a runner with a USD 5 spend ledger (about USD 1.76 used), saved AI grades | `docs/evaluation-results.md`, `backend/evaluation/` |
| Walkthroughs | Svalbard air temperature and Athens–Helsinki precipitation, with teacher prompts | `docs/walkthroughs.md` |
| User-study kit | Consent script, five tasks with predefined success, observation sheet | `docs/user-study-kit.md` |
| Deployment preparation | Container build (arm64 and amd64), state volume replacement, offline examples, browser/keyboard/phone/WebGL/tile/NASA-outage/rate-limit checks; deployment guide | `docs/verification.md`, `docs/deployment.md` |
| Phone globe | Below 640px the globe sits in its frame and "Zoom in to the grid cell" works | Unit tests; headless Chrome check |

## Remaining

### 1. The AI release gates still need review and validation

Discovery and explanations stay off (`DISCOVERY_EVALUATED=false`, `RAG_EVALUATED=false`).

- Latest complete follow-up: **50/50 planner/discovery** and **33/40 explanations** on
  automated checks, authored by the same agent implementing the fixes. Human support
  review is pending. The explanation target remains 90%; it was not met.
- Subsequent topic/guard fixes have targeted development evidence only; those checks
  do not replace a fresh full confirmation run. Some failed expected-section checks
  cited a different relevant section; keep the original scores and review actual support.
- The current USD 1 ledger reserved **USD 0.975993**, including the historical USD 0.15
  allowance. No new full RAG run fits its remainder. Do not erase the ledger or raise
  the cap without the owner's approval.
- The original PR #8 rounds and their grader records remain historical evidence in
  `docs/evaluation-results.md`; they are not scores for the final candidate.
- Turning a flag on is the owner's decision, recorded in `docs/evaluation-results.md`.

### 2. No person has reviewed the evaluation

All suites, expectations and grades were written by AI agents. A team member should spot-check
the AI grades in `backend/evaluation/round2/results/grader-1.json` and `grader-2.json`
against the answers and the cited passages, and review the suites themselves.

### 3. The last review of round 2 was not finished

The final review-and-fix step of round 2 was stopped to finish on time. Its findings were not
all applied. Re-run an integrity review of `docs/evaluation-results.md` against the result
files, and a code review of the round-2 changes in `backend/app/ai_guard.py`,
`backend/app/adapters/discover.py`, `explain.py` and `backend/scripts/run_evaluation.py`.

### 4. User observations

The team deferred user testing for this submission. None has been observed; the kit in
`docs/user-study-kit.md` remains for later validation. This is not a required action
for the current deadline, and no observed learning/usability outcome is claimed.

### 5. Public deployment

Nothing is deployed. Follow `docs/deployment.md`, then run its verification checklist on the
public host. Known points:

- The amd64 image builds but its runtime was not checked: under Rosetta on a Mac it hung while
  importing `scipy.stats`. Run it on a real x86_64 host.
- A non-empty state mount owned by root stops the app at startup; the app user's uid is not
  pinned in the Dockerfile.
- `compose.yaml` publishes port 8000 on every interface, which bypasses an HTTPS proxy. Bind it
  to `127.0.0.1` or block the port.
- `FORWARDED_ALLOW_IPS` behind a proxy on the same host is untested.
- `README.md` and the Dockerfile header show `docker run` without a state volume.

### 6. Demo and submission

- Record the 30-second video or prepare up to seven slides (`docs/submission.md`).
- Complete the submission checklist in `docs/submission.md`, including NASA and AI credits,
  and submit before 15 November 2026, 11:59 PM SGT.
- Any AI-generated image or video needs a visible watermark (AGENTS.md section 10).

### 7. Corpus decisions for the team

- Confirm that the reviewed source list is right, and that committing the extracted NASA text
  under `backend/data/corpus/sections/` is wanted.
- power.larc.nasa.gov's robots.txt blocks named AI crawlers for training. The corpus pages were
  fetched once, with a generic user agent, for cited retrieval only. Confirm this fits.
- The project-note URLs point at the `main` branch on GitHub, so they resolve only after this
  work is merged.
- Rebuilding the corpus changes its version even when the text does not, because some NASA
  pages change their markup; every rebuild needs a new upload.
- Reconcile actual OpenAI billing with the reserved upper bounds; uploaded files do not expire
  with the vector store and must be deleted separately.

### 8. Checklist items still open

From the spec's Draft 5 checklist:

- Review/version the corpus and verify retrieval and source mapping (retrieval relevance is
  below full).
- Verify ingestion, retrieval and storage accounting (actual usage is not reconciled).
- Record a decision for every consideration and listed resource (not checked against
  `docs/resource-assessment.md` in this work).
- The user study, the public deployment and the submission (items 4 to 6 above).

### 9. Smaller findings

- Spec section 10 says 409 for an unavailable snapshot or analysis version; the app returns 502
  for an unknown `snap=` and 400 for an unknown `av=`. Change one to match the other.
- Hidden reasoning tokens count against the output caps (1,024 for discovery and explanation,
  512 for the planner); reasoning effort is now low, but truncation was seen in round 1.
- During a map-tile outage the globe shows no basemap and no message; a short note may help.
- The yearly CSV writes values at full float precision while the monthly CSV uses two decimals.
- Our own 429 responses carry no `Retry-After` header.
- A round-2 result file (`backend/evaluation/round2/results/rag.json`) holds raw provider
  output with long encoded strings; one happens to start with `sk-`. It is not a key, but a
  secret scanner may flag it.
