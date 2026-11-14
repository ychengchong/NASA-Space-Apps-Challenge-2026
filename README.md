# Trend Detective

Investigate a regional Earth-system claim with NASA POWER data: choose a quantity,
location and dates, inspect its time series and estimated rate, and see whether a
justified statistical test is available. Built for [Be an Earth System Trend
Detective!](https://www.spaceappschallenge.org/2026/challenges/earth-system-trend-detective/).

The app is a prototype, not a forecasting service or a causal attribution tool.
One meaningfully used NASA dataset meets the organizer requirement supplied to
the team. More datasets, AI and MCP are not prerequisites for the challenge.

## Run locally

Use 64-bit CPython **3.14.5**, uv and Node **22.23.5**. Backend package metadata
allows Python >=3.12, but this change is tested on Windows 3.14.5. Docker uses the
same Python version; a successful Windows test is not a verified Linux image.

```powershell
cd backend
uv sync --locked
uv run uvicorn app.main:app --reload
```

In another terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open http://localhost:5173. The manual settings and cached examples work without
an AI key or a live NASA connection. Uncached locations/quantities need NASA POWER.
After `npm run build`, the backend serves the built UI at http://localhost:8000.

Copy `.env.example` to `.env` if needed and export its variables before starting
the backend; the app does not load `.env` automatically. Never commit credentials.

## What is implemented

- Manual settings and visible confirmation before running edited or AI-proposed cases.
- Original coordinate precision, actual grid-cell context and explicit supported dates.
  Unsupported dates are rejected with available ranges; they are not silently clamped.
- Calendar-day-weighted annual/seasonal means, leap years, missing data and real-year slopes.
- Sen's slope per decade, canonical verdicts, chart/map context and inspectable evidence.
- Two-place comparisons fitted on identical complete years, with the actual year list.
  This comparison is descriptive, not a test that the trends differ.
- Content-addressed evidence, versioned result IDs, pinned links, monthly/yearly CSVs
  from the viewed snapshot and downloadable checksum-verified evidence JSON.
- An interpretation question that gives guidance after a learner chooses an answer.
- Optional confirmed AI planning, CLI, REST and MCP tools using the same analysis layer.
- Period explorer and regional maps as descriptive views; neither reports significance.
  Regional area means keep a fixed footprint rather than averaging a changing set of cells.

## What significance means here

Formal inference is enabled only for individual **annual T2M** records with **20-45
contiguous complete years**, a homogeneous source period and the approved frozen
calibration table. Ten to nineteen values yield a descriptive rate; fewer than ten
produce a too-few-years result. Gaps, source transitions, unvalidated quantities or
seasons, unsupported lengths and unavailable calibration produce explicit
`inference_unavailable` results with null p-values. Unsupported confidence intervals
and OLS p-values are null. OLS slope remains descriptive.

The selected procedure is `mk_mc_envelope_v1`: ordinary MK scores evaluated against
a conservative Monte Carlo null envelope. Its declared simulation family is stationary
AR(1) with correlations 0, 0.2 or 0.5 and Gaussian or centered exponential innovations.
It is not Hamed-Rao, a distribution-free climate guarantee or proof of causation.
The [study plan](research/inference-plan.md), [all confirmation settings](research/inference-results.json)
and table checksum are retained. All 18 original confirmation settings and a separately predeclared
[156-setting full-length panel](research/inference-confirmation-all-lengths.json)
passed the proposed per-setting upper-bound <=7% guardrail at a nominal 5% threshold.
All 18 additional tied-value stress settings passed too. These are per-setting
Monte Carlo checks, not a simultaneous or universal climate guarantee. Conservatism reduces power.
Real series can violate these assumptions; a significant result does not certify them.

Solar/cloud records crossing the 2001 source transition remain descriptive. NASA
[warns about source changes in radiation trend analysis](https://power.larc.nasa.gov/docs/methodology/data/sources_fluxes/).
The app's day-weighted mean is an explicitly named statistic; POWER's own annual
processing uses means of months, so those values need not be identical.

## Evidence and persistence

The committed `backend/data/cache.sqlite` is an immutable seed. On first startup,
it is copied to `state/power.sqlite`; operational counters, budget reservations and
generation leases use `state/operations.sqlite`. Immutable content-addressed evidence
lives in `state/snapshots`. Configure `CACHE_PATH`, `OPERATIONAL_DB_PATH` and
`SNAPSHOT_PATH` to override these locations. Do not put private data there.

New NASA fetches retain the exact response bytes and safe query URL. Legacy seed
rows were supplied without their original response bytes: their normalized series
is frozen and that provenance limitation is visible. API version and scientific
product release are distinct; unknown product releases are reported as unknown.
A missing snapshot or unsupported analysis version returns an explicit error and
never substitutes live data. Preserve the snapshot directory when sharing links.

For a local container with persistent evidence/counters:

```powershell
Copy-Item .env.example .env
# Set PUBLIC_BASE_URL and trusted proxy addresses for your deployment.
docker compose up --build
```

Compose mounts the named `trend-state` volume at `/app/state`. Keep that volume on
redeploy and include it in backups. Use an HTTPS proxy for public deployment, set
`PUBLIC_BASE_URL`, and configure `FORWARDED_ALLOW_IPS` to trust only that proxy.
Liveness: `/healthz`; local data/calibration readiness: `/readyz`. Neither spends AI
credits or calls NASA. Docker and a public HTTPS deployment require separate verification.

## Optional AI planner

AI is **off by default**. `/api/plan` accepts one question and returns catalogue
settings for the user to review, edit and confirm. It cannot run an investigation,
return invented coordinates or display a free-form numerical explanation. All result
numbers and verdicts come from Python. The former `/api/chat` endpoint refuses requests.

For local Ollama, install a model appropriate to your own hardware and licence,
then set `AI_PROVIDER=ollama`, an exact `AI_MODEL` tag, `OLLAMA_MODEL_DIGEST` and a
loopback `OLLAMA_URL`. The server verifies the installed name/digest before generating.
No model was downloaded, selected or benchmarked by this implementation. A hosted
backend cannot use a laptop's localhost; co-locate inference or keep AI local.

Only enable `AI_ENABLED=true` and `AI_EVALUATED=true` after recording a real semantic
and latency evaluation for the exact model. Use the [evaluation protocol](docs/evaluation.md).
Fake-provider tests establish integration behavior, not model accuracy.

Optional Anthropic/OpenAI modes require an explicit model/key, owner-supplied daily
microdollar budget and input/output prices per million tokens, plus
`AI_BUDGET_DURABLE=true` with persistent operational storage. There are no guessed
model defaults or automatic paid fallbacks. Conservative atomic reservations happen
before provider calls; failures/cancellation retain reservations. Maintain rates for
the selected model. OpenAI uses structured output and `store=false`.

Bounds: 8 KiB body, one question <=2,000 characters, one generation at a time across
workers sharing operational state, 512 output tokens and a 30-second operation
deadline. Local context is capped at 8,192 tokens, with a conservative input bound.
Daily request and per-address limits apply. Chat text is not stored server-side.

## Development checks

From `backend/`:

```powershell
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run python -m scripts.generate_types --check
```

From `frontend/`:

```powershell
npm run test
npm run lint
npm run format:check
npm run build
```

Shared frontend result types are generated from Pydantic; run
`uv run python -m scripts.generate_types` after a contract change. Tests use fake
providers and saved NASA responses and do not require network or paid API calls.
To reproduce the full inference study, run `uv run python -m scripts.calibrate_inference`
from `backend/`; verify that its table/report checksums remain identical. Run
`uv run python -m scripts.confirm_lengths` to reproduce the additional full-length panel.

The [technical specification](docs/technical-spec.md) records implemented behavior
and remaining evidence gates. [Test migration](research/test-migration.md) explains
intentional changes from the older specification; no failures are hidden with skips.

## NASA data and credits

NASA POWER monthly values provide the time series behind charts, rates and eligible
significance results. T2M is two-metre air temperature from MERRA-2 reanalysis;
it describes a grid cell, not a city weather station. Additional catalogue variables
are exploratory/descriptive. Source documentation:
[NASA POWER](https://power.larc.nasa.gov/),
[processing and quantity semantics](https://power.larc.nasa.gov/docs/methodology/data/processing/),
[radiation sources and continuity](https://power.larc.nasa.gov/docs/methodology/data/sources_fluxes/).

These data were obtained from the NASA Langley Research Center (LaRC) POWER Project
funded through the NASA Earth Science/Applied Science Program. Evidence records
show API version, access date, retained query/source metadata and snapshot checksums.
The shipped legacy examples report API v2.10.0, accessed 2026-11-13.

Places: GeoNames cities15000, downloaded 2026-11-13, CC BY 4.0; the build script
retains cities of at least 100,000 people and selected fields. Map tiles/data:
OpenStreetMap contributors, ODbL; analysis remains useful without map tiles.

## AI assistance and submission evidence

MarshyKid's initial implementation was reviewed and revised with Codex assistance,
including source code, tests, documentation and the inference experiment. Optional
runtime planning uses the configured local or hosted model and is labelled as AI.
No AI-generated images/video are used. No commit or push is performed automatically.

Educational impact and the >=90% semantic planner target are not established by
unit tests. Run the recorded evaluation protocol with target users and the selected
model, verify the public deployment and finish the required demonstration before
claiming those criteria. A prototype cannot guarantee an award or global ranking.

The team has not selected a project licence. NASA/GeoNames/OpenStreetMap and software
dependencies retain their own applicable terms.
