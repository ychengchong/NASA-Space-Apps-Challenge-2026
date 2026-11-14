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
- Twenty catalogue variables, including snow depth, snowfall, snow cover, sea ice, surface
  pressure, water vapour, the strongest wind and haze, and two sea places for the
  sea-surface temperature. All but annual air temperature are descriptive.
- A fourth example, "Are Wisconsin summers getting hazier?": the challenge video's question
  as a descriptive one-place haze case at Madison, frozen in the shipped cache.
- The whole world: a variable's trend in a frozen world-mean sample of 162 grid points (every
  20°), built once by `scripts/build_world_mean.py` and read without calling NASA. It is an
  estimate from a sample, describes temperature far better than rainfall or wind, and leaves
  out land-only and sea-only variables.
- The gap between two compared places: the first place's yearly value minus the second's,
  with its own descriptive rate and a sentence saying the difference was not tested.
- "What is changing here?": every variable's descriptive rate, total change, years and
  record years at one place, grouped by theme and never ranked, from the globe's picked point
  or an open case.
- A "Compare the seasons" panel: the rate for all months and for each season side by side,
  from the case's own evidence, with only the annual air-temperature row ever assessed.
- Record years for each place: the three highest and three lowest yearly values, and the mean
  of the last ten years used against the first ten, as plain descriptions, not tests.
- Period explorer and regional maps as descriptive views; neither reports significance.
  Regional area means keep a fixed footprint rather than averaging a changing set of cells.
- One globe behind every screen (MapLibre GL JS on OpenFreeMap tiles): it turns to the places
  of a case, pins the example cases and paints a region map's grid cells. The globe needs
  WebGL; without it the rest of the app still works.

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
are exploratory/descriptive: snow, sea ice, surface pressure, water vapour and the
strongest wind also come from MERRA-2, and haze is CERES SYN1deg aerosol optical depth
(MODIS aerosol assimilated by the MATCH model) from 2001, not the MODIS Aqua product in Giovanni.
[Clouds and aerosols sources](https://power.larc.nasa.gov/docs/methodology/data/sources_clds_aerosols/). Source documentation:
[NASA POWER](https://power.larc.nasa.gov/),
[processing and quantity semantics](https://power.larc.nasa.gov/docs/methodology/data/processing/),
[radiation sources and continuity](https://power.larc.nasa.gov/docs/methodology/data/sources_fluxes/).

These data were obtained from the NASA Langley Research Center (LaRC) POWER Project
funded through the NASA Earth Science/Applied Science Program. Evidence records
show API version, access date, retained query/source metadata and snapshot checksums.
The shipped legacy examples report API v2.10.0, accessed 2026-11-13.

Places: GeoNames cities15000, downloaded 2026-11-13, CC BY 4.0; the build script
retains cities of at least 100,000 people and selected fields. Analysis remains useful
without map tiles.

Globe tiles: [OpenFreeMap](https://openfreemap.org/), in the [OpenMapTiles](https://www.openmaptiles.org/)
schema (© OpenMapTiles), with data © [OpenStreetMap](https://www.openstreetmap.org/copyright)
contributors under the ODbL. The globe shows the credit "OpenFreeMap © OpenMapTiles Data
from OpenStreetMap" at all times. The browser loads the tiles, the relief image and the label
fonts from `tiles.openfreemap.org`; no key or account is needed. The relief image is
[Natural Earth](https://www.naturalearthdata.com/) II with shaded relief (public domain), and
the globe's label font is Noto Sans (SIL Open Font License), both served by OpenFreeMap.

The page's three typefaces are in `frontend/src/fonts/`, as WOFF2 files of their Latin and Latin Extended subsets, taken from [Fontsource](https://fontsource.org/) 5.3.0 on 14 November 2026. Each is under the [SIL Open Font License 1.1](https://openfontlicense.org/); the licence texts lie beside the files.

- [Bodoni Moda](https://github.com/indestructible-type/Bodoni), © 2020 The Bodoni Moda Project Authors: the app's name, the key figure and the titles of cases.
- [Libre Baskerville](https://github.com/impallari/Libre-Baskerville), © 2012 The Libre Baskerville Project Authors: all running text.
- [Courier Prime](https://github.com/quoteunquoteapps/CourierPrime), © 2015 The Courier Prime Project Authors: typed labels, such as case numbers, stamps and the tags on the globe.

## AI assistance and submission evidence

MarshyKid's initial implementation was reviewed and revised with Codex assistance,
including source code, tests, documentation and the inference experiment. Optional
runtime planning uses the configured local or hosted model and is labelled as AI.
No AI-generated images/video are used. No commit or push is performed automatically.

Earlier AI use, recorded on the `initial-app` and `ui` branches (some of the chat files named
here were later retired on `main`, as described above):

- The [technical specification](docs/technical-spec.md) was drafted with AI assistance.
- An AI coding assistant (Claude Code, model Claude Opus 5.5) wrote the following under the team's direction: the application code, the tests, the frontend, the Dockerfile, the catalogue texts, keywords and trend notes, the region-type suggestions (`region_types`) in `backend/data/catalogue.json`, the 21 hand-picked regions in `backend/data/places.json`, Svalbard among them, the choice of the example cases and their teaser texts, and this README.
- The same assistant wrote the fixes from each review round, with their tests. An earlier round included the chat adapter (`backend/app/adapters/chat.py`), the MCP adapter (`backend/app/adapters/mcp_server.py`) and the shared plain message for invalid input (`first_problem` in `backend/app/errors.py`); in the frontend, the number pattern of the number check, link rounding and parameters, keyboard picking on the map, focus handling, the region view's notices and definitions, and the period explorer; new component tests with their sample data (`frontend/src/components/testData.ts`); and more catalogue keywords.
- In the latest round the assistant implemented decisions the team made, with their tests. In the backend: the region-type suggestions and the `region_types` field, the Svalbard region, "the selected area" as the name of a region's area mean, the "both places" summary, the warm-up of the suggested prompt's place, the `httpx2` pin, the proxy trust default (`FORWARDED_ALLOW_IPS`), the handling of clients that disconnect, the chat adapter's handling of any failed turn or tool, the two new system-prompt rules, and an API key kept out of the settings' `repr`. In the frontend: the "Dig deeper" panel with its related-variable and "Worth testing here" links and the region-type lookup behind them, the notice under an answer that ended before its numbers were checked, the reading order of the page, the single `h1`, the switch to the basic Plotly bundle, the Prettier setup and a formatting run, and new tests, such as the one that keeps the function-word lists of backend and frontend identical. It also brought the specification, this README and `AGENTS.md` in line with the code.
- On 14 November 2026 the assistant checked POWER's grids and the region map with 22 live calls. Its findings are in [spec 6](docs/technical-spec.md#6-data) and [spec 13](docs/technical-spec.md#13-risks-and-open-questions).
- After that live check showed that sunlight and cloud cover came from a neighbouring 1° cell for about a third of places, the assistant changed the app to take them from the place's own 1° cell. In the backend it wrote the grid `alignment` field of the catalogue, the changes to `resolve_place` and `fetch_point_series`, the updated comments in `backend/scripts/warm_cache.py` and `backend/tests/test_examples.py`, and their tests. In the frontend it drew the 1° cell outline on the place map, fitted the map to the places and their whole cells, removed the caption saying the 1° grid's position was not confirmed, and wrote their tests. The assistant, not the team, chose this fix, and the team has yet to confirm it.
- In the same round the assistant fixed the reading order of an open case and the region view: at every width the page now holds and shows the verdict, the notes and the Dig deeper panel first, then the settings, then the chart, maps and evidence, and the answer keeps a readable line width. It wrote the tests for the new order and brought the specification and this README in line with both changes.
- The shipped `backend/data/cache.sqlite` was produced by a script (`backend/scripts/warm_cache.py`) from live NASA POWER calls on 13 November 2026. It holds the three example cases and the Nairobi grid point of the suggested prompt. Ten sunlight and cloud cover rows that the app no longer read were deleted from it on 14 November 2026, at the team's request.
- The assistant then added OpenAI as a second provider for the AI helper, under decisions the team made: the `AI_PROVIDER` and `OPENAI_API_KEY` settings with a default model per provider, the Responses API loop in `backend/app/adapters/chat_openai.py`, the shared failure messages in `backend/app/adapters/chat_text.py`, the changes to `backend/app/adapters/chat.py` and `backend/app/config.py` that let both providers share the tools, steps and number check, the tests in `backend/tests/test_chat_openai.py` and `backend/tests/test_config.py`, and the matching changes to the specification, this README, `.env.example` and `AGENTS.md`. The OpenAI path has not yet run against the live API.
- At run time, the optional AI helper uses the Claude API or, when it is configured instead, the OpenAI API, with the model set by `AI_MODEL`. Its notes carry a visible "Written by AI" label.
- On 14 November 2026 the team asked the assistant to overhaul the interface, to make it look good and fit the challenge. The assistant chose and built the result: one dark theme, a globe behind every screen in place of the two flat maps (MapLibre GL JS on OpenFreeMap tiles, replacing Leaflet on OpenStreetMap tiles), the single-column case file with the settings folded under an open case or map, the key to the globe, the mark of a picked point, the app's own magnifying-glass mark, and the notice for a browser without WebGL. It wrote the new modules (`globeStyle.ts`, `globeGeometry.ts`, `globeContext.ts`, `cellTooltip.ts`, and the `GlobeCanvas`, `GlobeStage`, `PlaceLegend` and `SettingsFold` components), their tests, the new stylesheet, and the matching changes to the specification and this README. It checked the result in a desktop browser at 1440px and at an emulated phone width, not on a real phone. The team has yet to confirm the look.
- Later on 14 November 2026 the assistant (Claude Code, model Claude Fable 5.2) reviewed the new interface at 18 screen sizes and states, and the team asked it to fix the first five findings. It wrote the fixes, their tests and the matching changes to the specification and this README: dark sheets under the header and the question bar on a phone, a shorter phone stage with the example prompts in one scrolling row, the side-by-side layout from 640px for tablets and phones held sideways, place names on the left of their markers on a small stage, a question bar that drops a keyword match once the screen has moved on (`frontend/src/questionBarState.ts`), "click the globe" in the case settings, example prompts on the first screen only, and the `GET /api/ai` endpoint, with which the question bar says from the start that the AI is off. The last item replaces the specification's earlier rule that the browser does not know in advance whether the AI is on; the assistant chose that fix, and the team has yet to confirm it. It checked the result in emulated screens from 320px to 1280px wide with the AI off, not on a real phone and not with the AI on.
- The team then asked for the review's other fourteen findings to be fixed, and the same assistant wrote them, with their tests and the matching changes to the specification and this README. On the stage: the choices for a picked point (`PickedPoint`, moved out of the case settings), a caption for a case and a key for a region map (`StageCaption`, `StageNote` and `MapLegend`), a hint for touch screens, and a fade-in of the Earth after its first tiles. On the globe: a tilt held within 55° of the equator, region cells cut at the box, the oceans and the best known countries named evenly, and, on a phone, one finger scrolling the page while two move the globe. In the case file: "Copy link" and "Map this region" under the verdict (`CaseActions`, `clipboard.ts`), placeholders while a case loads (`Skeleton`), the rate of a significant trend as a large figure, a quieter question bar on a case or a map, the region verdict's sentence before its method note, larger panel labels and 44px touch targets. The assistant made the design choices among these; the team has yet to confirm them. It kept the mouse wheel zooming the globe on a wide screen, where the review had called that a scroll trap, because the stage there is fixed beside the page. It checked the result in emulated desktop, tablet and phone screens with the AI off, not on a real device.
- Still on 14 November 2026 the team asked whether the interface could look more creative and less machine-made. The assistant (Claude Code, model Claude Fable 5.2) drew previews over the running app, each labelled as a mock-up made with AI: three ideas, then four looks, then a mix of two of them, then the app's data in that mix. The previews are not part of this repository. A team member chose from them: the mix (an atlas page with a detective's marks), the example cases pinned to the globe, the place inks green, violet, yellow and magenta, and open-licensed typefaces in the repository. The assistant then built that look and wrote its tests and the matching changes to the specification and this README: the stylesheet, the three typefaces, the globe as an engraving in a framed plate with a ring of degree marks, the sheets and their typed tabs (`FileTab`), the verdict's stamp (`VerdictCard`, `InkFilter`), the chart colours, and the example pins with their string (`examplePins.ts`, `ExampleCases`, `GlobeCanvas`). The assistant, not the team, decided what the previews did not show: which open typefaces stand in for the ones in the previews, the names of the oceans waiting for zoom 3, the pin's card standing on the case's northernmost place, the string only from 960px, the stamp standing above the text below 960px, the hint lines of the first screen, and the look of every screen that was not previewed, such as the settings, the notices and the phone layout. It was checked in headless Chrome at four screen sizes with the AI switched off, not on a real phone, not with a screen reader, and not with the AI switched on.
- The team then asked the assistant, as a designer, for the real problems of the new look, and then to fix all seventeen it named. The assistant (Claude Code, model Claude Fable 5.2) wrote the fixes, their tests and the matching changes to the specification and this README. The chart moved right under the verdict, with its explanation under the plot and its rate and 95% interval in its summary (`App.tsx`, `TrendChart`). The question bar steps back on an open case, and the first screen links to the settings ("set up a case by hand"). The stamp lost its uneven-ink filter (`InkFilter` was removed), the tab lost the case's code, and the "Exhibit" tabs went. Capitals, italics, small text and the grain over text were cut back, and links and buttons went from red to ink (`styles.css`). The place inks became teal, ochre, violet and magenta (`placeStyles.ts`). The region map's cells became opaque under a coast line (`globeStyle.ts`). An example's pin now answers the pointer, its card can be clicked, the list waits 0.2 seconds before it turns the Earth, and the idle turn resumes (`ExampleCases`, `examplePins.ts`, `GlobeCanvas`). The stage's buttons grew to 44px for fingers, a tablet's plate fits the Earth, and a phone's hint sits on the frame. The assistant, not the team, chose every one of these remedies and their details, such as the four inks, the 0.2 and 4 second waits, the wording of the new line on the first screen and of the chart's sentence on its rate. It left three things for the team, listed in [spec 13](docs/technical-spec.md#13-risks-and-open-questions): a true minus sign, a drawn uncertainty band, and where a comparison's chart goes. The fixes were measured and walked through in headless Chrome at seven screen sizes with the AI switched off, not on a real phone, not with a screen reader, and not with the AI switched on.
- The star field of the earlier dark look was removed with it. The grain of the paper is an SVG noise filter in the stylesheet; no AI image generator made it. The globe's map style in `globeStyle.ts` was written by the assistant, with layer filters taken from OpenFreeMap's Liberty style.
- On 14 November 2026 the assistant (Claude Code, model Claude Opus 5.5) merged `main` into
  the `ui` branch. It kept `main`'s retired chat endpoint, confirm-first planner, descriptive
  regional maps and specification, and kept the `ui` interface: the question bar now asks
  `GET /api/capabilities` instead of the `ui` branch's `GET /api/ai`, which was dropped;
  settings changes on an open case wait for "Run this case"; and the region map's key no
  longer shows a mark for cells passing a stricter test.
- On 14 and 15 November 2026 the same assistant (Claude Code, model Claude Opus 5.5) built
  descriptive additions from a team brief, one at a time, with their tests and the matching
  specification text: record years (`Records` in `models.py`, `rank_years` and
  `first_and_last_means` in `stats.py`, the sentences in `verdict.py`, the record facts under
  each verdict and the rings on the chart); the seasons panel (`season_rates`, `GET
  /api/seasons`, `SeasonsPanel`, `seasonRows.ts`); the fourth example and its title and
  teaser, with three more cache rows from one live call; the place overview
  (`place_overview`, `GET /api/overview`, the /place page, `PlaceOverviewView`,
  `overviewRows.ts`); the gap between two places (`Gap`, `gap_sentence`, `GapChart`); the
  whole world (`scripts/build_world_mean.py`, `data/world-mean.json` from 324 live calls the
  team approved, `world_trend`, `GET /api/world`, `WorldView`);
  eight catalogue variables and two sea places,
  after 18 live POWER calls that confirmed their grids and their values over land and sea,
  a new saved fixture and 35 rows added to the shipped example cache. The team chose the
  additions and their limits; the assistant chose the details the brief left open, listed
  in its reports, such as the first-ten against last-ten-years rule, the units word "optical
  depth" for haze and the region types "ocean", "tundra" and "mountains" for the new
  variables.

Educational impact and the >=90% semantic planner target are not established by
unit tests. Run the recorded evaluation protocol with target users and the selected
model, verify the public deployment and finish the required demonstration before
claiming those criteria. A prototype cannot guarantee an award or global ranking.

The team has not selected a project licence. NASA/GeoNames/OpenStreetMap/OpenFreeMap,
the typefaces and software dependencies retain their own applicable terms.
