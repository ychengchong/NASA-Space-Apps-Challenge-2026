# Verification record

Audit date: 14 November 2026 (SGT). Working branch: `new-plan`.
Implementation baseline: `1fa0cf1`, the merged UI and review fixes on main.
This audit includes the uncommitted Draft 5/documentation cleanup. It is not proof
of a public deployment, live-model accuracy, user impact or completed submission.

This document records observed checks. The [evaluation protocol](evaluation.md)
defines future experiments; the [technical spec](technical-spec.md) defines the
target; [submission materials](submission.md) provide copy and final actions.
The dated Draft 5 section below adds the container and browser checks of 15 November
2026. The 14 November audit after it is kept as it was recorded.

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
