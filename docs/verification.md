# Verification record

Latest audit: 15 November 2026 (SGT), `main` at `c85adb6` plus the local submission
documentation/environment-template cleanup. No analysis, verdict or UI code was
changed by this cleanup.

## Submission cleanup checks

- Full backend suite: **1,621 passed** with `python -m pytest -q -p no:cacheprovider`.
- Ruff lint/format and `python -m scripts.generate_types --check` passed.
- Full frontend suite: **767 passed**; ESLint, Prettier and TypeScript/Vite build passed.
- The build retains its large-chunk warning. This is not a failed build.
- The locally configured backend and frontend responded successfully; direct and
  frontend-proxied `/api/capabilities` reported all three AI paths available.
  This readiness check made no paid model call and did not test generated answers.
- All three merged PRs (#7, #8, #10) were confirmed merged on GitHub before this cleanup.
  The cleanup itself remains uncommitted until the team publishes it.
- All repository Markdown file/image links resolve locally after removing the
  obsolete planning checklist. Three watermarked submission PNGs are in `docs/images/`.
- The actual configured OpenAI key was absent from the tracked/submittable files
  checked; `.env` remains ignored. No credentials were printed or copied into images.
- The committed NASA seed matches its Git bytes, and all 173 corpus sections match
  their manifest hashes. Saved scientific and evaluation results were not rewritten.

The [AI evaluation report](evaluation-results.md) records the unmet quality target
and the team's activation decision. No student study or public deployment is
verified, and no final demo/presentation URL has been provided. The
[submission guide](submission.md) contains the requirements audit and final actions.

## Historical verification checkpoints

The dated records below are preserved as originally observed. Their branch names,
test totals, "current" scores, budgets and disabled-feature statements refer to
those earlier checkpoints. They do not override the latest status above.

## Latest Draft 5 integration check

On 15 November 2026, `fix-draft5-release` was fast-forwarded to
`origin/draft-5` at `b1b4a5d` (UI fixes), then the local release changes were
reapplied without conflicts. A backup remains in the
`draft5-before-latest-integration` stash. Nothing was committed or pushed.

The integrated working tree passed **1,617 backend tests**, Ruff lint and format
checks, **771 frontend tests**, ESLint, Prettier and the TypeScript/Vite production
build. Git reported no unresolved files or whitespace errors. The build still
warns about large globe/Plotly chunks. These checks establish integration
compatibility; they do not establish AI accuracy, browser behavior or deployment
readiness. No paid model calls were made for this integration check.

## Final submission-day candidate

On 15 November 2026, `fix-draft5-release` passed **1,600 backend tests** with
`python -m pytest -q -p no:cacheprovider`. Ruff lint/format checks and generated-type
checks passed. The unchanged frontend's **758 tests**, lint, formatting and production
build passed earlier in this follow-up. No tests were skipped or weakened to make the
suite pass. Named-source fixtures were updated to exercise the new retrieval boundaries.

The authorized live OpenAI runs and their limits are recorded in
[evaluation results](evaluation-results.md#submission-day-follow-up). The latest complete
prospective sample scored 50/50 planner/discovery and 33/40 explanations on automated
checks. Subsequent targeted checks are development evidence; no full explanation gate
or human factual-support review is claimed for the final candidate.

The corpus's 173 section files match their manifest hashes. Both prospective suite
hash sets are unchanged after the runs, and paired identities match. The committed
NASA seed matches Git bytes. A check confirmed that the actual local API key does not
appear in the public evaluation artifacts or documentation, and all release flags in
the local `.env` remain false. The daily setting is USD 1; the evaluation ledger reserved
USD 0.975993, including the prior USD 0.15 allowance. Source/metadata integrity checks
are in [delivery checks](../backend/evaluation/submission-day/results/delivery-checks.json).

The offline example/API/export verification below remains applicable; the final changes
do not alter statistics, verdict templates, numerical contracts or frontend code. Public
hosting/container runtime and a new interactive browser session were not verified here.

## Submission-day fixes and offline checks

Date: 15 November 2026. Branch `fix-draft5-release`, based on PR #8 head `3ea4d50`.
This initial checkpoint covered local uncommitted fixes on Windows, before the later
authorized live-model runs above. No paid API calls were made during this checkpoint.

- Reproduced Windows corpus hash failures and comparison blocks borrowing another
  place's outcome. Regression tests failed before the fixes and passed afterward.
- Corpus section files and frozen evaluation JSON use LF checkout rules. The corpus
  writer writes the exact UTF-8 bytes it hashes, without Windows newline translation.
- Explanation checks use the named/referenced places of each block. Separate blocks
  are required for differing comparison outcomes; unsupported commentary is withheld.
- Backend: `python -m pytest -q -p no:cacheprovider` passed **1,574 tests**.
  Ruff lint/format and `python -m scripts.generate_types --check` passed.
- Frontend: `npm test -- --maxWorkers=2` passed **758 tests**. Lint, formatting and the
  production build passed. This is not a new interactive browser/phone check.
- A scratch cache copied from the committed seed served all four saved examples with
  an HTTP transport that rejects every outbound request. Each example passed identical
  pinned replay, PNG export, monthly/yearly CSV export for every place, and SHA-256
  verification of the evidence downloads. Outbound requests: **0**. The seed was unchanged.
- Health/readiness passed. With AI explicitly disabled, capabilities reported all AI
  paths unavailable and `/api/plan`, `/api/discover`, `/api/explain` returned 503.
- The Windows investigation IDs for walkthroughs A/B were respectively
  `4692d380992ac316c3dda6c9cd74451affaeca437f89b4236edb1fd5a67d1cbf` and
  `de88d1deddfb527b9ba0529d7c5d2b6c14acf5b86f09843df11256442155a15a`.
  Their evidence hashes match the original walkthrough record. Exact investigation
  hashes were not reproduced across platforms; replay was identical locally. Do not
  present the earlier recorded IDs as verified portable IDs.

The historical live-model scores below and in `evaluation-results.md` do not validate
these changes. Discovery and explanation remain gated off until a fresh evaluation
passes and a teammate reviews source support. See the review checklist in
[submission guide](submission.md#final-checklist).

## Draft 5 stage 7: container and browser checks

Date: 15 November 2026. Branch `draft-5`, HEAD `5bfa2e4`, built from a working tree that also
held uncommitted backend and corpus changes from parallel work, so these results are not a
clean build of one commit. Machine: an arm64 Mac with Docker. All runs had AI off
(`AI_ENABLED=false`, `AI_PROVIDER=disabled`, `RAG_ENABLED=false`) and no API keys. Nothing was
deployed and no paid model call was made. The [deployment guide](deployment.md) uses these
results.

### Container

| Check | Observed result |
| --- | --- |
| Build without cache, linux/arm64 | Passed in 27 s. `npm ci`, the Vite build and `uv sync --locked --no-dev` all succeeded. One BuildKit warning, JSONArgsRecommended, for the deliberate shell-form `CMD`. |
| Build without cache, linux/amd64 | Passed in 45 s |
| Image size | About 157 MB (arm64) and 159 MB (amd64) as reported by `docker image inspect`, which is the compressed content size. Unpacked on disk, `docker image ls` showed 708 MB (arm64) and 677 MB (amd64). |
| Image contents | Backend app, `.venv`, `backend/data` with the committed `cache.sqlite` (same SHA-1 as the repository copy), the corpus (185 files, every SHA-1 equal to the working tree) and the built frontend. No `.env` file, `node_modules`, tests, scripts, evaluation folder or `cache.local.sqlite`. |
| First start on a fresh named volume at `/app/state` | Created `power.sqlite` (88 series rows), `operations.sqlite` and an empty `snapshots/` |
| Health and capability routes | `/healthz` ok, `/readyz` ready, `/api/capabilities` all three AI features `false`, `/api/examples` four examples |
| Web app routes | `/` and a `/case` deep link both served the app HTML. An unknown `/api/` route answered 404 JSON, not the app HTML. |
| Four examples from the cache | All answered 200 in 10-23 ms with no new NASA rows. Svalbard: significant rising, +0.79 °C per decade, 1981-2025. |
| Live NASA fetch | A new Reykjavik case answered 200 in 2.55 s with retained raw response bytes |
| Volume replacement | After the container was removed and a new one started on the same volume, all 9 state files were byte-identical |
| Offline replacement container (`--network none`) | The four examples, the Reykjavik pinned link, the CSV and JSON series, the evidence JSON and `chart.png` all answered 200 with unchanged IDs |
| Uncached case while offline | 502 `source_unavailable` with the spec 10 error shape and no stack trace |
| Disabled AI routes | POST `/api/plan`, `/api/discover` and `/api/explain` answered 503 `ai_unavailable` |
| Logs | Method, path, status and duration only; no query strings, client addresses, `Traceback` or `ERROR` lines |
| Stop signal | `docker stop` finished within 1 s with a clean uvicorn shutdown |
| Non-empty state mount owned by root | The container exited with code 3 at startup: `PermissionError` writing to `/app/state` |
| amd64 image started under Rosetta emulation | Did not start: the server ran at full CPU for 306 s without finishing startup. `import scipy.stats` did not finish; `import numpy` did. Runtime on amd64 is not verified. |

### Browser

Playwright drove Chrome against a local backend and the Vite dev server, with scratch state.
The phone size was emulated (375 by 812 with touch), not a real device.

| Check | Observed result |
| --- | --- |
| Manual case journey at 1440, 800 and 375 px wide | Helsinki air temperature 1981-2025 loaded in 2.6-2.7 s at every size: rising, significant, +0.58 °C per decade. No sideways page scroll on the home page or any of the four tabs. Tabs set `aria-selected` and show one panel. No console errors. |
| Keyboard only | From the question bar, a typed question gave a keyword proposal, Enter on "Run this case" opened it, and Tab reached the footer. Every stop had a visible focus outline; the globe shows focus with a dashed frame and a crosshair. Tabs support ArrowLeft, ArrowRight, Home and End. |
| Pinned link in a fresh browser | "Copy link" copied the pinned URL. Opened in a new browser process, it showed the same verdict text. |
| Downloads | Yearly and monthly CSV (`text/csv`, attachment) and evidence JSON (`application/json`, schema `power_series_v1`) downloaded |
| WebGL fallback | With `--disable-webgl` and with `--disable-3d-apis`, the globe area showed its no-WebGL message and cases still answered with no page errors |
| Map tile outage | With every request to `tiles.openfreemap.org` blocked, cases and pinned links still worked. The globe showed no basemap and no message, and the console logged fetch errors. |
| NASA outage (local proxy that answers 502) | An uncached case answered 502 `source_unavailable`. The page showed that NASA's service is not answering, with "Try again" and the examples. A cached case still answered. |
| Rate limit (5 per minute) | Requests 6 and 7 answered 429 `rate_limited`; the page showed "The case could not load" with "Try again" |
| AI off | The question bar explains that the AI helper is off and uses keyword matching; no "Ask about this investigation" panel; no POST requests were made |

### Findings for the team

- Spec 10 says an unavailable snapshot or analysis version answers 409. Observed: an unknown
  snapshot answers 502 `source_unavailable` and an unknown analysis version 400
  `bad_request`. The code or the spec has to change; that is a team decision.
- A state mount that is not writable by the image's `app` user stops startup. The user's uid
  (999 in this build) is not fixed in the Dockerfile.
- `docker run --rm` without `-v <volume>:/app/state`, as in the Dockerfile header, keeps no
  state.
- During a tile outage the user gets no message. Whether to add one is a product question.
- The 429 answer has no `Retry-After` header. The spec does not ask for one.
- Yearly CSV values have full float precision; monthly values have two decimals.

### Not checked in this stage

A public HTTPS deployment, the host's proxy and `FORWARDED_ALLOW_IPS`; the amd64 image on a
real x86_64 machine; a real phone; cancellation of a running request; an OpenAI outage and AI
budget or turn exhaustion (AI was off); the AI paths with keys; NASA retry behaviour on
connection failures (the fake proxy received one connection attempt); and rollback to an
older image on the same volume.

## Observed checks

| Check | Result |
| --- | --- |
| Backend environment | CPython 3.14.5; backend/.venv previously installed from uv.lock; imports/package compatibility verified |
| Full backend suite | 706 passed, 39.93 seconds |
| Backend Ruff lint and formatting | Passed |
| Pydantic-to-TypeScript contract check | Passed |
| Frontend tests | 512 passed, 47 files, Node 22.23.5 |
| Frontend ESLint, Prettier and TypeScript/Vite build | Passed |
| Built UI and API route smoke check | Passed through FastAPI TestClient/ASGI; no browser or network server claimed |
| Three cached examples | All opened, pinned JSON replay retained each investigation ID, share routes served HTML |
| Evidence and exports | SHA-256 verified for every example snapshot; pinned monthly CSVs and PNG exports returned successfully |
| Disabled AI / unknown API route | Planner returned 503; capabilities reported false; unknown API returned 404 rather than SPA HTML |
| Outbound calls / seed integrity during smoke check | Zero outbound calls with a blocking fake transport; committed cache checksum unchanged |
| Documentation links, whitespace and source packaging | Checked during cleanup; no secrets, environments or generated runtime state included in the source bundle |
| Docker build-context exclusions | Environment variants, keys, local tool/credential folders and generated artifacts excluded; image build remains unverified |

Scientific regressions cover missing internal/endpoint years,
disjoint comparison coverage, changed source snapshots, grid boundaries and a zero
median rate with significant rank evidence. These distinct statistics are not conflated.

## Reproduce the automated checks

Use the Python/Node versions in the README and install locked dependencies first.
From backend/ run:

```powershell
python -m pytest -q -p no:cacheprovider
python -m ruff check .
python -m ruff format --check .
python -m scripts.generate_types --check
```

From frontend/ run:

```powershell
npm test -- --maxWorkers=2
npm run lint
npm run format:check
npm run build
```

The route smoke check used the built frontend, a separate copy of the seed,
isolated operational/snapshot storage, a fixed 2026-11-14 cutoff, AI disabled and
an outbound transport that fails any request. It exercised the real analysis
path for the three shipped examples, not a mock numerical response. It does not
verify live NASA availability, browser rendering or network deployment.

## Previously retained scientific evidence

The [original study](../research/inference-results.json) records 18 confirmation
settings with 4,000 null replications each. The separately predeclared
[full-length panel](../research/inference-confirmation-all-lengths.json) records
156 settings, with maximum one-sided 95% upper bound 0.0670674. Earlier checks also
covered 18 tied-value stress settings and constant p=1. These studies were not
rerun for this documentation cleanup; the scientific-method section was preserved.

## What remains unverified

The manual app and inference engine were exercised with cached NASA data. Provider
integration uses fake HTTP transports. No paid model request or real Ollama generation
was made. The AI remains off until exact model identity, evaluation and required
budget/persistence configuration are supplied. No benchmark accuracy is claimed.

No browser/device interaction was verified in this audit. Contributor-reported older
UI checks are preserved in the [AI contribution record](ai-disclosure.md), not treated
as new observations. Docker was unavailable, so Linux image build and persistent
container replacement were not tested. Public deployment, the target-user study and
the final recording/presentation remain team tasks. The team confirmed no public
demo or hosted app link is available yet. The build warns about large lazy-loaded
globe and Plotly chunks (approximately 300 KB and 385 KB gzip respectively).

Draft 5 discovery, corpus ingestion/retrieval, cited explanations, expanded accounting
and their evaluation suites are planned, not implemented. Existing automated planner
tests use fakes and cannot justify enabling a real model by themselves.

Legacy seed data is marked as normalized evidence without original response bytes;
new downloads retain exact bytes. Unknown scientific product releases remain unknown.
This prototype does not claim universal climate calibration, a judging score or a
Global Winner outcome. A final source revision, public demo/supporting links and
successful official submission must be confirmed before the submission is complete.
