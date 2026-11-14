# Verification record

Audit date: 14 November 2026 (SGT). Working branch: `new-plan`.
Implementation baseline: `1fa0cf1`, the merged UI and review fixes on main.
This audit includes the uncommitted Draft 5/documentation cleanup. It is not proof
of a public deployment, live-model accuracy, user impact or completed submission.

This document records observed checks. The [evaluation protocol](evaluation.md)
defines future experiments; the [technical spec](technical-spec.md) defines the
target; [submission materials](submission.md) provide copy and final actions.

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
