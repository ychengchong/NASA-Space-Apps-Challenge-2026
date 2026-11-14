# Trend Detective

Trend Detective is a web app for the 2026 NASA Space Apps challenge "Be An Earth System Trend Detective!". It lets a non-specialist test one claim about the Earth against NASA data and get a verdict they can check. A user asks a question such as "Is my city getting warmer?". The app turns it into a case: one variable, one or more places, a period and a season. It fetches monthly data from NASA POWER, draws the yearly values, computes the rate of change, tests it for significance and states the result in plain words.

The full design is in the [technical specification](docs/technical-spec.md). Rules for contributors and coding agents are in [AGENTS.md](AGENTS.md).

## What you can do

- **Case screen:** pick a variable, a place, a period and a season, then read the verdict, the chart right under it and the evidence panel beside a globe that turns to the place, with CSV downloads and a "Copy link" button, because the page's address holds the whole case.
- **Example cases:** three ready cases on the first screen, each pinned to the globe. Pointing at one in the list turns the Earth to its places and ties it to its pins with a red string; pointing at a pin shows the case's question, and a click on the pin or its card opens the case.
- **Dig deeper:** each case links related variables to cross-check and, for a place of a known region type such as desert or tundra, variables worth testing there. A link keeps the places, period and season and switches the variable.
- **Comparisons:** test one variable at two to four places over the same years, with a summary sentence above the per-place verdicts.
- **Period explorer:** see how the rate and the p-value change with the first year of the period, and pick a start year to reload the case.
- **Region map:** colour every grid cell of a box (2° to 10° a side) by its trend, with a mark on cells that pass a stricter test.
- **AI helper (optional):** type a question in plain words; the AI, on Claude or on OpenAI, picks the variable and place, runs the same tools and writes short notes labelled "Written by AI".
- **MCP server:** outside AI apps can call the same analysis tools at `/mcp`.

## Quick start

Requirements: Python 3.12 or later with [uv](https://docs.astral.sh/uv/), and Node.js 22.13 or later. Node 23 and 25 fall outside the engine range of the pinned Vitest.

Start the backend:

```sh
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

In a second terminal, start the frontend:

```sh
cd frontend
npm ci
npm run dev
```

Open <http://localhost:5173>. The Vite dev server proxies `/api`, `/mcp` and `/healthz` to the backend at <http://localhost:8000>.

The three example cases on the first screen answer offline from the pre-warmed cache in `backend/data/cache.sqlite`. The cache also holds the Nairobi grid point of the question bar's suggested prompt, "Is Nairobi getting warmer?", so its case needs no NASA call either. Sunlight and cloud cover are not warmed at those places, so a case of either there, such as the cloud cover cross-check that the "Rain in Athens and Helsinki" example offers, calls NASA POWER once per place. A case at a place that is not cached calls NASA POWER once for that place and adds the values to that file. To keep the shipped file unchanged, point `CACHE_PATH` at a copy.

After `npm run build`, the backend also serves the built web app itself at <http://localhost:8000>.

## Configuration

The backend reads its settings from environment variables. Copy [.env.example](.env.example) to `.env` to start. The backend does not load `.env` by itself: for a local run, export the variables in the shell that starts uvicorn, for example with `set -a; . ../.env; set +a` from `backend/`. An empty value means the default.

| Variable | Default | Meaning |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | None | Key for the AI helper on Claude. Server only, never sent to the browser |
| `OPENAI_API_KEY` | None | Key for the AI helper on OpenAI. Server only, never sent to the browser |
| `AI_PROVIDER` | None: Claude when `ANTHROPIC_API_KEY` is set, otherwise OpenAI when `OPENAI_API_KEY` is set | The AI helper's provider, `anthropic` or `openai`. Any other value stops the server at start |
| `AI_ENABLED` | `true` | Turns the AI helper on or off. `1`, `true`, `yes` and `on` mean on; any other value means off |
| `AI_MODEL` | `claude-opus-5-5` on Claude, `gpt-6-luna` on OpenAI | Model id for the AI helper, on the provider in use |
| `AI_MAX_ITERATIONS` | `6` | Model round trips in one AI turn |
| `AI_MAX_TURNS` | `20` | User turns in one conversation |
| `AI_DAILY_TURNS` | `500` | AI turns per day, across all users. The counter lives in the SQLite file |
| `AI_RATE_PER_MINUTE` | `10` | AI turns per client address per minute |
| `RATE_LIMIT_PER_MINUTE` | `120` | Other requests per client address per minute, on `/api` (except `/api/chat`) and `/mcp` |
| `PUBLIC_BASE_URL` | None | Public address, such as `https://trend-detective.example.org`. Used to build case links and the `/mcp` hostname allowlist |
| `CACHE_PATH` | `backend/data/cache.sqlite` | Location of the SQLite file with the NASA values and the usage counters |
| `FORWARDED_ALLOW_IPS` | `127.0.0.1` in the container; uvicorn's own default, `127.0.0.1,::1`, elsewhere | Addresses or ranges, comma-separated, whose `X-Forwarded-For` header uvicorn trusts for the visitor's address. Read by uvicorn, not by the app. Unlike the app's settings, an empty value makes uvicorn trust no address |

The AI helper runs on Claude when `ANTHROPIC_API_KEY` is set, and otherwise on OpenAI when `OPENAI_API_KEY` is set; `AI_PROVIDER` picks one of them when both keys are set. It stays off when `AI_ENABLED` is off, when no key is set, or when the provider that `AI_PROVIDER` names has no key. The app works fully without it: the question bar falls back to keyword matching, and every other feature is unchanged. The page asks `GET /api/ai` when it opens, so the question bar says from the start whether an AI or keyword matching reads the question.

On OpenAI the helper uses the Responses API, with the same rules, tools, limits and number check as on Claude. Every request sends `store: false`, so OpenAI does not keep the responses for later retrieval ([spec 8, "The OpenAI path"](docs/technical-spec.md#the-openai-path)). That path has not yet run against the live OpenAI API.

## Command line

The verdict CLI prints a case as plain text. Run it in `backend/`:

```sh
uv run python -m app.cli air_temp 60.17,24.94 --label Helsinki
```

It prints the verdict sentence, the rate with its 95% interval, the p-values, the cautions, the data source with its version and access date, the case link and the steps taken. The first argument is a catalogue id. Then come one to four places as `LAT,LON`.

| Option | Meaning |
| --- | --- |
| `--label NAME` | Name of each place, in order. Repeat it for each place |
| `--from YEAR`, `--to YEAR` | First and last year. Years outside the record are clamped to it |
| `--season` | `annual` (default), `DJF`, `MAM`, `JJA` or `SON` |
| `--scan` | Include the period scan |

When a latitude is negative, put the options first and `--` before the places, so the place is not read as an option. The CLI uses the same cache as the server, so a place that is not cached calls NASA POWER.

## Container

The [Dockerfile](Dockerfile) builds one image. It compiles the web app, installs the backend from `uv.lock`, and ships the pre-warmed cache. The backend then serves the API, `/mcp` and the web app at one address. From the repository root:

```sh
docker build -t trend-detective .
docker run --rm -p 8000:8000 --env-file .env trend-detective
```

- The server listens on `PORT`, default `8000`. To use another port, pass both, for example `-e PORT=8080 -p 8080:8080`.
- Run the container behind an HTTPS proxy that sets `X-Forwarded-For` and passes the original `Host` header, because `/mcp` checks the `Host` header.
- The server trusts `X-Forwarded-For` only from the addresses in `FORWARDED_ALLOW_IPS`, which the image sets to `127.0.0.1`. Set it to the address range of the platform's proxy, for example `-e FORWARDED_ALLOW_IPS=10.0.0.0/8`, so each visitor gets their own rate limit. Otherwise every visitor shares the proxy's address. `*` trusts every address, so use it only when nothing but the proxy can reach the container.
- `PUBLIC_BASE_URL` is required in production. Without it, `/mcp` answers only on localhost, and case links in API and MCP results have no host.
- The access log is off, because it would record client addresses and query strings.

The image build has not been run yet.

## Using the MCP server

The server speaks the Model Context Protocol over Streamable HTTP, in stateless mode, at:

```text
https://<host>/mcp
```

Locally it is <http://localhost:8000/mcp>. Each message is a `POST` and gets a JSON answer; any other method returns 405 with `Allow: POST`. There is no login, and the per-address rate limit applies. A request with an `Origin` header must come from the `PUBLIC_BASE_URL` origin or from localhost.

The seven tools:

- `search_variables`: search the catalogue of climate variables with plain words.
- `find_place`: find a city or region by name and return up to five candidates with coordinates.
- `analyze_trend`: test one variable for a trend at one place; returns an Investigation.
- `compare_places`: test one variable at two to four places over the same years, with a summary.
- `get_series`: return the raw monthly or yearly values of one variable at one place.
- `map_trends`: map the trend of one variable across a box of 2° to 10° a side.
- `get_chart`: draw a PNG chart of a case with one to four places.

Each tool except `get_chart` returns structured data. The analysis tools add a text block with the app's fixed verdict sentence and a link to the case in the web app.

Field names differ between clients. Most accept a server entry with a name, the transport and the URL, such as:

```json
{
  "mcpServers": {
    "trend-detective": {
      "type": "http",
      "url": "https://<host>/mcp"
    }
  }
}
```

## Tests and checks

All commands are in [AGENTS.md, section 13](AGENTS.md#13-commands). The checks to run before calling a change done:

| Check | Run in | Command |
| --- | --- | --- |
| Backend tests | `backend/` | `uv run pytest` |
| Backend lint | `backend/` | `uv run ruff check .` |
| Backend format | `backend/` | `uv run ruff format --check .` |
| Frontend lint | `frontend/` | `npm run lint` |
| Frontend format | `frontend/` | `npm run format:check` |
| Frontend tests | `frontend/` | `npm run test` |
| Frontend build | `frontend/` | `npm run build` |

To format the code instead of checking it, run `uv run ruff format .` in `backend/` and `npm run format` in `frontend/`. The frontend uses Prettier 3.10.1, a development dependency, with a line width of 110, set in `frontend/.prettierrc.json`; `frontend/.prettierignore` leaves out build output and generated files.

The tests never touch the network. They use saved NASA POWER responses in [backend/tests/fixtures/](backend/tests/fixtures/README.md) and fakes for the Claude and OpenAI APIs.

To rebuild the example cache from live NASA POWER calls, run `uv run python -m scripts.warm_cache` in `backend/`. It warms the three example cases and the place of the suggested prompt "Is Nairobi getting warmer?" (grid point 1.5° S, 36.875° E), so a rebuild reproduces the committed cache row for row. It writes to `CACHE_PATH`, or to the file given with `--cache PATH`.

## How it works

- Six tool functions in `backend/app/tools/`, with `stats.py` and `verdict.py`, do all the analysis ([spec 5](docs/technical-spec.md#5-tool-layer)).
- Three thin adapters expose them: REST at `/api` (`rest.py`), the AI chat at `/api/chat` (`chat.py`, with `chat_openai.py` for the OpenAI API; `/api/ai` says whether the AI is on) and MCP at `/mcp` (`mcp_server.py`). They translate inputs and outputs and never compute ([spec 4](docs/technical-spec.md#4-architecture)).
- Only `sources/power.py` calls NASA POWER. It fetches the full monthly record of every catalogue variable on the same grid in one call, at the centre of the place's cell: one call for the ten MERRA-2 variables and one for sunlight and cloud cover. It stores the values in SQLite. Everything else reads through that cache ([spec 6](docs/technical-spec.md#6-data)).
- A trend is tested on yearly values: the Mann-Kendall test corrected for year-to-year memory, Sen's slope with a 95% interval, and a least-squares cross-check ([spec 7](docs/technical-spec.md#7-statistics)).
- The one rule: every number a user sees comes from the analysis code. Verdict and summary sentences come from fixed templates. The AI and the frontend never calculate or reword a statistic ([spec 1](docs/technical-spec.md#the-one-rule)).
- Results are recomputed from the cache on every request, and the page address holds the whole case, so every case is a shareable link ([spec 10](docs/technical-spec.md#10-api-and-urls)).
- The frontend is React with TypeScript, built with Vite and formatted with Prettier. Plotly.js, in its basic bundle, draws the charts. MapLibre GL JS draws one globe behind every screen: it turns to the places of a case, and a region map paints its grid cells onto it ([spec 3, "The globe"](docs/technical-spec.md#the-globe)). The globe needs WebGL; without it the rest of the app still works.
- The look is a page from an atlas with a detective's marks on it ([spec 3, "Wording and accessibility"](docs/technical-spec.md#wording-and-accessibility)): the globe is an engraving in a framed plate, the verdict and the evidence are sheets of paper, the verdict under a typed "Case file" tab, and each verdict carries a stamp. Colour is kept for data: red rises, blue falls, and each place has its own ink. The three typefaces are open-licensed and served by the app itself, so the page calls no font service.

## Data and credits

### NASA POWER

All climate data comes from the [NASA POWER](https://power.larc.nasa.gov/) monthly API. POWER asks for an acknowledgement and a data reference naming the service, its version and the access date ([spec 6, "Citing the data"](docs/technical-spec.md#citing-the-data)). The evidence panel shows both.

Acknowledgement:

> These data were obtained from the NASA Langley Research Center (LaRC) POWER Project funded through the NASA Earth Science/Applied Science Program.

Data reference: the app records the API version and the access date with every value it caches, and shows them with each case. Every value in the shipped cache came from API version v2.10.0 on 2026-11-13, so the evidence panel of the first example reads:

> NASA POWER (MERRA-2), version v2.10.0, accessed 2026-11-13.

A case built from newly fetched values shows its own access date.

Behind POWER:

- MERRA-2 reanalysis for temperature, precipitation, humidity, wind and soil wetness.
- GEWEX SRB up to 2000 and CERES from 2001 for sunlight reaching the surface and cloud cover.

### Places and map

- City list: [GeoNames](https://www.geonames.org/), file `cities15000`, downloaded 2026-11-13, licensed [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Changed: only places of 100,000 people or more are kept, with fewer fields and coordinates rounded to 4 decimals. `backend/scripts/build_places.py` rebuilds the list.
- Globe tiles: [OpenFreeMap](https://openfreemap.org/), in the [OpenMapTiles](https://www.openmaptiles.org/) schema (© OpenMapTiles), with data © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors under the Open Database License (ODbL). The globe shows the credit "OpenFreeMap © OpenMapTiles Data from OpenStreetMap" at all times. The browser loads the tiles, the relief image and the label fonts from `tiles.openfreemap.org`; no key or account is needed.
- Relief image on the globe: [Natural Earth](https://www.naturalearthdata.com/) (Natural Earth II with shaded relief), public domain, served by OpenFreeMap.
- Label fonts on the globe: Noto Sans, under the SIL Open Font License, served by OpenFreeMap.

### Typefaces

The page's three typefaces are in `frontend/src/fonts/`, as WOFF2 files of their Latin and Latin Extended subsets, taken from [Fontsource](https://fontsource.org/) 5.3.0 on 14 November 2026. Each is under the [SIL Open Font License 1.1](https://openfontlicense.org/); the licence texts lie beside the files.

- [Bodoni Moda](https://github.com/indestructible-type/Bodoni), © 2020 The Bodoni Moda Project Authors: the app's name, the key figure and the titles of cases.
- [Libre Baskerville](https://github.com/impallari/Libre-Baskerville), © 2012 The Libre Baskerville Project Authors: all running text.
- [Courier Prime](https://github.com/quoteunquoteapps/CourierPrime), © 2015 The Courier Prime Project Authors: typed labels, such as case numbers, stamps and the tags on the globe.

### Libraries

Licence names are taken from each installed package's metadata.

| Library | Version | Used for | Licence |
| --- | --- | --- | --- |
| FastAPI | 0.162.6 | Web service | MIT |
| MCP Python SDK (`mcp`) | 2.3.0 | MCP server | MIT |
| Anthropic Python SDK (`anthropic`) | 2.8.0 | AI helper on Claude | Apache-2.0 |
| OpenAI Python SDK (`openai`) | 3.51.0 | AI helper on OpenAI | Apache-2.0 |
| Matplotlib | 3.11.2 | PNG charts | Matplotlib license agreement (classifier: Python Software Foundation License) |
| NumPy | 2.5.4 | Statistics | BSD-3-Clause, with bundled parts under 0BSD, MIT, Zlib and CC0-1.0 |
| SciPy | 1.18.1 | Statistics | BSD |
| MapLibre GL JS (`maplibre-gl`) | 6.18.0 | The globe | BSD-3-Clause |
| Plotly.js, basic bundle (`plotly.js-basic-dist-min`) | 4.3.0 | Interactive charts; the app draws only scatter traces | MIT |
| React | 19.3.1 | Web interface | MIT |

## Limitations

- Significance is not cause. The test says a pattern this strong would be unusual if nothing were changing. It does not say why.
- "Not significant" is not proof that nothing is changing. The record may be too short or too noisy to tell.
- The method fits a straight line. A curve or a sudden shift can be missed or misdescribed.
- Values describe a grid cell of 0.5° by 0.625°, roughly 50 km across, not a weather station. Sunlight and cloud cover sit on a coarser 1° grid.
- Sunlight and cloud cover come from the 1° cell, bounded by whole degrees, that holds the place, and the globe outlines that cell and fits it in view on "Zoom in to the grid cell". From 55° to 65° N neighbouring 1° cells can share values, because the real longitude resolution there is about 2° (seen from 20° to 30° E, [spec 6](docs/technical-spec.md#6-data)).
- MERRA-2 is a reanalysis: a weather model steered by observations. Changes in the observing system can create artificial shifts. Rainfall, humidity, wind and soil wetness carry a standing caution.
- The record starts in 1981, and in 1984 for sunlight and cloud cover. Only complete years are used.
- Sunlight and cloud cover change source in 2001. A trend across that year carries a `source_change` caution.
- A period needs at least 10 complete years for a test. Under 20 years, the result carries a `short_record` caution.
- The AI helper can be wrong. Its notes are labelled as written by AI, and the number check marks any number in its text that it cannot match to the tool results or the case on screen as "unverified" ([spec 8](docs/technical-spec.md#the-number-check)). Verdict sentences never come from the AI.

## AI use

The hackathon asks teams to show where AI was used.

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
- No AI-generated images or video are used.
- Commits that contain AI-written code or text carry a `Co-Authored-By` trailer naming the AI tool.

## Licence

The team has not chosen a licence for this project yet.

These terms apply anyway:

- NASA POWER data: the acknowledgement and data reference above.
- GeoNames city list: CC BY 4.0, with attribution and the changes listed above.
- OpenFreeMap tiles: © OpenMapTiles, with OpenStreetMap data under the ODbL; the credit "OpenFreeMap © OpenMapTiles Data from OpenStreetMap" is shown on the globe at all times.
- Natural Earth relief image: public domain.
- Bodoni Moda, Libre Baskerville and Courier Prime: SIL Open Font License 1.1; the licence texts are in `frontend/src/fonts/`.
- Each library keeps its own licence, as listed above.
