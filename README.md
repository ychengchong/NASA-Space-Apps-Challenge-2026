# Trend Detective

An educational Earth-science investigation app by **Half-Stack Developers** for
[Be an Earth System Trend Detective!](https://www.spaceappschallenge.org/2026/challenges/earth-system-trend-detective/).

Choose a location, variable and period; inspect NASA POWER time series, estimate
change and examine statistical evidence where supported. Explore a case file,
compare places, inspect sources, try the interpretation lesson and download evidence.

![Investigation workflow](docs/images/trend-detective-workflow.png)

## Start here

| Resource | What it contains |
| --- | --- |
| [Submission guide](docs/submission.md) | Copy-ready fields, demo outline, requirement/judging audit and final checklist |
| [Walkthroughs](docs/walkthroughs.md) | Saved investigations and interpretation prompts |
| [Technical specification](docs/technical-spec.md) | Architecture, data contracts, methods and inference scope |
| [Verification](docs/verification.md) | Observed software checks and their limits |
| [AI evaluation](docs/evaluation-results.md) | Actual model results, failed gates and retained evidence |
| [AI disclosure](docs/ai-disclosure.md) | Team decisions, development assistance, runtime AI and contributor history |
| [Deployment](docs/deployment.md) | Public hosting, persistent state and operational checks |

**Demo:** [Watch or download the 29-second video](demo-video/trend-detective-demo.mp4)
([subtitles and playback notes](demo-video/README.md)). It demonstrates an actual
local investigation and AI interaction; response waits are cut. The animation and
voice-over are AI-generated and disclosed in the video and metadata.

The source and demo are public supporting materials. No public interactive app
has been deployed; a local demo is not a public deployment. The assistant remains
experimental, as described in [AI evaluation](docs/evaluation-results.md).

## Run locally

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and
[Node.js](https://nodejs.org/) **22.13 or later**, but not 23 or 25: the frontend tools
support 22.13+, 24 and 26 onward. You do not need to install Python: uv reads
the root `.python-version` and downloads **Python 3.14.5** if it is missing. The
backend also runs on Python 3.12 and later, and the lockfiles pin every dependency.

Tested on Windows (Python 3.14.5, Node 22.23.5) and on an Apple Silicon Mac (Python
3.14.5 and 3.12.5). Linux was checked only as the container image (see
[Deployment](#deployment)). Apart from the first step, every command below works
unchanged in PowerShell, bash and zsh.

From the repository root, create a local environment file only if one does not exist.

On Windows (PowerShell):

```powershell
if (!(Test-Path .env)) { Copy-Item .env.example .env }
```

On macOS or Linux (bash or zsh):

```sh
[ -f .env ] || cp .env.example .env
```

Then start the backend:

```sh
cd backend
uv sync --locked
uv run --env-file ../.env uvicorn app.main:app --reload
```

In a second terminal, from the repository root:

```sh
cd frontend
npm ci
npm run dev
```

Open **http://localhost:5173**. Manual controls and the four cached examples work
without an AI key or a live NASA connection. New locations/quantities require NASA
POWER.

The backend can also serve the built app at http://localhost:8000. Run `npm run build`
in `frontend/`, then start the backend, or restart it if it is already running: it
looks for `frontend/dist` only when it starts.

If an install step fails:

- In PowerShell, the script execution policy can block `npm` ("running scripts is
  disabled on this system"). Use `npm.cmd` in its place, as in `npm.cmd ci`.
- On an Intel Mac or a Windows PC with an ARM processor, the locked `cryptography`
  package (used by the MCP library) has no prebuilt wheel, so `uv sync` compiles it,
  which needs a [Rust toolchain](https://www.rust-lang.org/tools/install). This has
  not been tried on such a machine.

### Configure the AI assistant

Everything above works without AI. Three optional AI features run on OpenAI:

| Feature | Where it appears | What it needs |
| --- | --- | --- |
| Case settings proposed from a question (the planner) | The question bar | An OpenAI API key |
| Suggested variables (guided discovery) | The question bar | The key and the uploaded documentation corpus |
| Answers about a result (RAG) | "Ask about this investigation", on every case page | The key and the uploaded corpus |

The "Ask about this investigation" panel is on every case page. While its feature is
off, it says which AI features are on and names each `.env` setting that keeps it
off, so you can see what is missing without reading any logs.

`.env.example` already holds the team's settings: the model `gpt-6-luna` and its
prices, a **USD 1 daily budget**, and every AI switch set to `true`. These switches
turn the features on; they do not claim that an evaluation target was passed. You
fill in three values in the root `.env`:

1. **Add your key.** Set `OPENAI_API_KEY=` to your own OpenAI API key, then restart
   the backend. The planner turns on.
2. **Upload the documentation corpus once.** From `backend/`:

   ```sh
   uv run --env-file ../.env python -m scripts.upload_corpus --max-bytes 1000000
   ```

   This sends 173 reviewed text sections (about 195 KB) to a new vector store in the
   OpenAI project your key belongs to. It costs a little in usage and storage, and it
   is not part of normal startup. `--max-bytes` is a safety cap: the upload refuses
   a larger corpus before sending anything. It ends by printing two lines:

   ```text
   RAG_VECTOR_STORE_ID=vs_...
   RAG_CORPUS_VERSION=...
   ```

3. **Copy both lines into `.env`**, in place of the empty `RAG_VECTOR_STORE_ID=` and
   `RAG_CORPUS_VERSION=` lines. Copy each line whole: the version has 64 characters,
   and one missing character keeps discovery and the panel off. Restart the backend.

To check, open any case: the panel now has a question box. Or open
http://localhost:8000/api/capabilities, which should report `true` for all three
features and empty `_gaps` lists. Checking never calls a model and does not test
answer quality.

If something stays off, the panel's list says why:

| The panel says | What to do |
| --- | --- |
| `OPENAI_API_KEY` is empty | Step 1. Start the backend with `--env-file ../.env`, as in [Run locally](#run-locally): without it the backend reads no `.env` and the AI stays off. |
| `RAG_VECTOR_STORE_ID` or `RAG_CORPUS_VERSION` is empty | Steps 2 and 3. |
| `RAG_CORPUS_VERSION` does not match the corpus | The version was cut short or comes from another corpus. Copy the whole line again. |
| The server did not say whether its AI assistant is set up | The backend is not running, or the frontend cannot reach it on port 8000. |

Good to know:

- **Lost the two lines?** The upload also saved them in `state/corpus-files.json` of
  the copy that ran it: the version is the top-level key, and the store ID is its
  `vector_store_id`. The upload refuses to send the same corpus version twice from
  one copy unless you add `--force`, which makes a new store.
- **Each key needs a store it can read.** A store belongs to one OpenAI project, so a
  teammate whose key is from another project runs their own upload. A fresh copy of
  the repository can reuse your store: copy the same two lines into its `.env`.
- **Unused stores expire** 30 days after their last use. If answers stop finding
  sources after a long pause, upload again with `--force` and copy the new lines.
- **Keep the root `state/` directory** across restarts: it records the day's AI
  spending, and AI requests are refused once the day's budget cannot pay for another.
  A hosted deployment must mount persistent state. See the
  [deployment and retrieval guide](docs/deployment.md).
- **Keys stay on the server.** Put them only in the backend's `.env`, never in Git
  or in frontend variables. Restart the backend after editing `.env`.

Settings you can normally leave as they are:

| Setting | What it does |
| --- | --- |
| `AI_ENABLED`, `AI_EVALUATED` | The main AI switches. |
| `AI_PROVIDER` | `openai`. With `anthropic` or `ollama` only the planner works. |
| `AI_MODEL`, `AI_INPUT_MICROUSD_PER_MILLION`, `AI_OUTPUT_MICROUSD_PER_MILLION` | The model and its prices, in microdollars (USD 1 = 1,000,000). Change the prices if you change the model. |
| `AI_DAILY_BUDGET_MICROUSD`, `AI_BUDGET_DURABLE` | The daily budget, and that its spending is kept in `state/`. |
| `RAG_SEARCH_MICROUSD_PER_CALL` | The price reserved for one documentation search. |
| `RAG_ENABLED`, `DISCOVERY_EVALUATED`, `RAG_EVALUATED` | Retrieval, suggested variables and the answers panel. Set one to `false` to turn that feature off. |

### AI scope and limitations

Natural-language planning proposes settings for user confirmation. RAG retrieves
reviewed NASA documentation and project method notes for qualitative explanations.
All numerical analysis and verdicts remain in deterministic Python code.

The assistant is **experimental**. A planner/discovery follow-up passed 50/50
automated cases; the later source-checked RAG sample passed 31/40 combined checks,
below its 36/40 target. The paired no-retrieval condition passed 10/40 under the same
citation requirements. These are separate, agent-authored samples, not independent
human validation or a general accuracy guarantee. The team chose activation despite
the unmet target. See the [full evidence](docs/evaluation-results.md).

## Scientific scope and reproducibility

- NASA POWER monthly records drive charts and rate estimates. Gridded estimates
  represent an area, not an exact observation at a street address.
- Python preserves missing values and computes calendar-day-weighted summaries.
  Missing observations are not replaced by zero.
- Sen's slope estimates change per decade. Formal significance is limited to
  eligible annual two-metre air-temperature records with 20–45 contiguous complete
  years, under the documented Monte Carlo Mann–Kendall inference policy.
- Other variables, seasonal analyses, maps and place comparisons are descriptive.
  Comparisons use common complete years. Unsupported p-values/intervals are withheld.
- The [simulation study](research/inference-plan.md) and its confirmation results
  check stated assumptions; they do not establish universal climate calibration.
- A trend alone does not establish causation or predict the future. Non-significance
  does not prove no change. Educational impact has not been measured in a user study.

The committed `backend/data/cache.sqlite` is a read-only seed copied into local
state on first startup. New downloads retain exact response bytes; legacy seed
records lacking original response bytes are labelled as normalized evidence.
Retain `state/snapshots` and operational storage for pinned investigation replay.
Exact investigation hashes have not been demonstrated identical across platforms;
local pinned replay was verified. See [verification](docs/verification.md).

## Development checks

Run in `backend/`:

```sh
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run python -m scripts.generate_types --check
```

Run in `frontend/`:

```sh
npm run test
npm run lint
npm run format:check
npm run build
```

Tests use saved data and fake providers; they require no API credits. Scientific
study scripts, corpus rebuilds and real-provider evaluations are separate owner-run
operations, not startup requirements. Retained study and evaluation artifacts must
not be treated as measured student impact or a successful public deployment.

## Deployment

The backend can serve the API and built frontend in one container:

```sh
docker compose up --build
```

Compose loads the root `.env` and mounts persistent state. Public hosting needs a
public HTTPS address, server-side secrets and deployment checks. A local demo or
recording does not expose your computer to judges. Follow the
[deployment guide](docs/deployment.md); do not upload `.env` to share AI access.

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

Places: GeoNames cities15000 and countryInfo, downloaded 2026-11-15, CC BY 4.0; the build
script retains cities of at least 100,000 people and every capital (marked as one), with
selected fields. A country's name finds its capital. Analysis remains useful without map tiles.

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

## AI assistance

OpenAI Codex and Claude Code assisted with substantial code, research, tests,
documentation and interface work. Codex also prepared the submission diagrams,
which carry visible AI-generation watermarks. Development assistance is separate
from the optional OpenAI-powered in-app assistant. The
[AI disclosure](docs/ai-disclosure.md) identifies team decisions, actual checks,
limitations and historical contributor reports. AI-assisted commits retain
co-author metadata. The team remains responsible for the final submission.

The team has not selected a project licence. Third-party data, fonts, map assets
and dependencies retain their own terms; public source access does not itself
grant a new licence.
