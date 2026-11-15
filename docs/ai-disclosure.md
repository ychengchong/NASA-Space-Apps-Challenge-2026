# AI use — Trend Detective

Half-Stack Developers used OpenAI Codex and Claude Code as coding, research and
documentation assistants for Trend Detective. Development assistance is separate
from the OpenAI model used by the application's optional AI assistant.

## Development and integration

**Our design and decisions:** We chose to build an educational Earth-system trend
investigation application using NASA data, with charts, evidence panels, place
comparisons and an interpretation lesson. We requested a Python/FastAPI and
React application, documentation-grounded AI, explicit user confirmation of
proposed investigations, and submission materials. AI assistants also proposed
technical methods, implementation details, interface designs and wording; we do
not claim that every design decision originated with the team. These contributions
and their provenance are recorded in the historical notes below.

**How we used the tools:** Codex assisted with challenge and resource research,
technical-specification revisions, code and PR reviews, backend fixes, regression
tests, corpus ingestion, retrieval filters, explanation safeguards, evaluation
scripts, configuration, documentation and branch integration. Contributor records
describe Claude Code's assistance with the initial application, scientific-method
implementation, frontend, poster-style redesign and earlier evaluation rounds.
The assistants generated substantial code and text, rather than providing advice
alone. Reported historical model identities and browser checks remain attributed
to their contributors.

**Our verification:** The combined revision merged into `main` at `c85adb6`
passed 1,621 backend tests and 767 frontend tests, alongside Ruff, ESLint,
formatting checks and the TypeScript/Vite production build. Earlier offline checks
exercised the four saved NASA investigations, pinned replay and exports without
outbound access. The subsequent environment-template update passed 43 existing
configuration tests. These are recorded automated checks performed with AI
assistance, not evidence of independent human review, educational impact or a
public deployment. The team remains responsible for reviewing the implementation,
its scientific assumptions and the claims made in the submission.
[Verification record](verification.md), [technical specification](technical-spec.md).

## In-app AI assistant and RAG

**Our design and decisions:** We selected OpenAI-hosted inference and document
retrieval rather than requiring a downloaded local language model. The assistant
proposes investigation settings for confirmation and explains datasets, methods
and limitations using retrieved documentation. Numerical analysis and canonical
verdicts remain in deterministic Python code. We approved uploading the existing
reviewed corpus and later chose to enable the experimental assistant for the
hackathon demo despite the unmet explanation-quality target.

**How we used the tools:** The evaluated runtime model was `gpt-6-luna`. Codex
helped index 173 sections from 13 NASA sources and 10 project method/variable notes,
implement citation and result-consistency checks, and build paired retrieval and
no-retrieval evaluation runs. AI tools authored evaluation questions, expected
outcomes and source-support grades. These evaluations are not independently
human-authored or human-reviewed; the latest generation and grading calls used
the same model family.

**Our verification:** A planner/discovery follow-up passed 50/50 automated cases.
The subsequent source-checked RAG sample passed 31/40 combined checks, below the
36/40 target; its matched no-retrieval condition passed 10/40 under the same
citation requirements. These separate samples are not pooled or presented as a
general accuracy guarantee. Earlier failures and grading records are retained.
The local demo's capabilities endpoint reported planning, discovery and
explanations available after activation; that readiness check made no paid model
call and does not establish answer quality. The team remains responsible for the
activation decision, reviewing generated explanations and explaining the limits
of this experimental feature.
[Evaluation report](evaluation-results.md),
[latest source-checked results](../backend/evaluation/submission-day/release-confirmation/results/combined-summary.json).

## Submission text and diagrams

**Our design and decisions:** We supplied the team name, project context,
submission requirements and reference examples, then requested revisions to the
summary, project details and diagrams. We decided to describe an intended
AI-enabled demo and to keep NASA resource entries and AI-use disclosures in their
dedicated submission fields.

**How we used the tool:** Codex drafted and revised submission and team text and
created workflow, capabilities and tools/technologies diagrams using Python and
Matplotlib. These are AI-assisted generated graphics, not application screenshots
or additional scientific evidence. Local exports are in the ignored
`artifacts/submission/` directory; final PNG copies are published under
`docs/images/`. They carry visible OpenAI Codex watermarks.

**Our verification:** Codex rendered and visually inspected the exported diagrams.
The team remains responsible for checking the final uploaded versions, retaining
their watermarks and ensuring that the text matches what the demo actually shows.
No observed user study, successful public deployment or completed official
submission is established by these materials.

Codex subsequently shortened the README, consolidated submission fields and the
supplied-requirements/judging audit in `submission.md`, removed the obsolete
`draft5-remaining.md` checklist, corrected current-status summaries and published
the watermarked diagrams in `docs/images/`. Full software checks were rerun with
the same 1,621 backend and 767 frontend passes. Local Markdown links, corpus hashes,
seed integrity and absence of the configured API key from submittable files were
also checked. The live challenge page returned 502 during this audit, so the
saved challenge description and organizer information supplied by the team were used.

## Historical contribution records

For PR #11, Codex added the demo links, playback notes and subtitle references,
corrected stale missing-demo statements and updated the submission checklist.
It checked the MP4's duration and AI metadata, decoded all video/audio with a
temporary FFmpeg inspection tool, inspected representative frames and measured
audio levels. Public links were checked without authentication. This is not a
listening review or an official-submission confirmation, and no application code
or recorded media was changed by this follow-up.

The records below are retained as recorded. References to features being off,
earlier test counts, budgets or "current" results describe their original stages,
not the latest status above. They distinguish contributor-reported observations
from checks performed in this session.

<details>
<summary>Earlier development, evaluation and contributor records</summary>

# AI contribution record (historical)

This record distinguishes development assistance from runtime AI.

## Submission-day follow-up

OpenAI Codex implemented Windows corpus-byte preservation, per-place explanation
checks, product/topic-aware retrieval, guard corrections and explicit season guidance.
It corrected the evaluation runner's budget override, preserving the owner's USD 1
allowance with a cumulative ledger that is never reset for another suite. After the
owner explicitly approved the payload and destination, it indexed the existing
173 NASA/project sections in the owner's OpenAI project. The key remains in local `.env`.

Codex authored the new questions/expectations, fixed them before each prospective run,
and used automated checks. It also implemented the code, so these are not independent
blind or human-reviewed evaluations. The original failed scores were preserved.
The latest complete sample scored 50/50 planner/discovery and 33/40 explanations;
later targeted development checks are separate. No human source-support review or
student study has occurred. The owner later turned discovery and explanations on by default. See the
[current report](evaluation-results.md#submission-day-follow-up).

The final code passed 1,600 backend tests; the unchanged frontend passed 758 tests
and its production build. Lint, formatting and generated-type checks passed. Four
cached NASA examples passed replay/export/evidence checks with outbound requests
blocked and the shipped seed unchanged. Public deployment and final submission were
not performed. The evaluation ledger reserved USD 0.975993 within USD 1, including
the runner's USD 0.15 prior allowance; invoiced usage was not retrieved.

## Earlier contribution records

On 15 November 2026, Codex fixed the new-stats review findings and added regression
tests: visible settings for keyword/LLM proposals and picked-point choices from
overview/world pages, Python-rendered overview cautions, rejection of differing
same-cell evidence, and a no-common-years message instead of a claimed zero gap.
It updated the shared generated types, technical spec and README for these fixes.

Codex assisted with scientific/provenance fixes, planner integration, tests,
documentation, UI review fixes and repository/submission preparation. Claude Code
contributions reported by contributors are preserved below. The model names and
historical browser/live-call claims are contributor-reported, not independently
revalidated by the current verification run.

The app defaults to keyword matching and manual settings. Its optional configured
LLM planner proposes settings for confirmation. Statistics and verdicts come from
Python/templates. Draft 5 guided discovery and RAG explanations are implemented
([Draft 5](technical-spec.md)). After two held-out evaluation rounds on 15 November 2026,
neither passed its gate, and both stay disabled
([evaluation results](evaluation-results.md)). No local model was installed by
this cleanup. No generated images/video are included in the repository.

AI-assisted commits carry the disclosure trailer required by the repository.
Use this record when completing the submission disclosure; identify any actual
runtime provider/model separately if enabled and evaluated.

## Draft 5 round-2 held-out evaluation (15 November 2026)

- **Who did the work:** Claude Code (model Claude Opus 5.5), working as agents of one
  workflow. No person reviewed any case, response or grade.
- **The suites:** an AI wrote new planner/discovery and RAG suites for round 2, blind,
  before any model call. They are in `backend/evaluation/round2/`, with their SHA-256
  hashes in that directory's README. Round 2 added predeclared citation support for
  discovery and retrieval relevance for RAG. The hashes were checked before and after the
  run.
- **Development before the run:** general fixes for the round-1 failure causes, and tuning
  on the round-2 development files only. They are described in the README's AI-use section
  and in spec 8.
- **The frozen run:** each held-out suite ran once with OpenAI `gpt-6-luna` through
  `backend/scripts/run_evaluation.py`. No case was re-run, and nothing was changed during
  or after the run. That produced `backend/evaluation/round2/results/`.
- **Grading:** the runner's automated checks graded every case. Two AI grader agents
  (Claude Opus 5.5), each without seeing the other's output, graded every RAG case in both
  conditions, the citation support of every discovery suggestion and every planner text,
  with a reason for each item. Their grades are in `grader-1.json` and `grader-2.json`, and
  they agreed on every item. They are the same model family that wrote the suites and the
  code.
- **The report and the decisions:** the workflow's lead agent wrote the round-2
  [evaluation results](evaluation-results.md) and decided both gates. It reports that the
  owner delegated those decisions to it on 15 November 2026. Planner/discovery passed 60 of
  70 cases, with 3 critical fabricated citations. RAG passed 65 of 77 combined. Neither gate
  passed, so it set `DISCOVERY_EVALUATED=false` and `RAG_EVALUATED=false` in the uncommitted
  local `.env`.
- **Spend:** the round-2 held-out runs reserved USD 0.595980. The evaluation ledger now
  totals USD 1.761232 of the USD 5.00 cap, as reserved upper bounds.

## Draft 5 round-1 held-out evaluation (15 November 2026)

- **Who did the work:** Claude Code (model Claude Opus 5.5), working as agents of one
  workflow, ran and reported this stage. No person reviewed any case, response or grade.
- **The suites:** an AI wrote the planner/discovery and RAG suites and their expected
  outcomes before any model call (`backend/evaluation/`).
- **Offline rehearsal:** before tuning, the development agent ran the runner on the first
  six cases of each held-out suite with a fake provider that returned fixed answers. No
  model call was made, so no model saw a held-out case, but the held-out files were opened
  and run during the development phase.
- **Development tuning:** with model calls on the development suites only, the agents changed the
  instructions of the existing /api/plan (when a question may be marked ambiguous), of
  /api/discover (clarify only for an unclear variable or place) and of /api/explain (a
  request for a value references the field that holds it). They also changed one rule in
  `backend/app/ai_guard.py`, so that naming the significance test is not read as a claim
  of significance. Each change came with network-free tests.
- **The frozen run:** each held-out suite then ran once with OpenAI `gpt-6-luna` through
  `backend/scripts/run_evaluation.py`, with the code, corpus and suites frozen. That
  produced `backend/evaluation/results/`.
- **Grading:** the runner's automated checks graded every case. Two AI grader agents judged
  the support of every RAG answer in both conditions; their verdicts were transcribed,
  without their reasons, into `backend/evaluation/results/rag-grades.json`. After the runs an
  AI review agent (Claude Opus 5.5) graded the citation support of the 20 discovery
  suggestions and read the 31 planner texts left for review, recorded in
  `backend/evaluation/results/discover-review.json`.
- **The report:** the agent writing the report wrote
  [evaluation results](evaluation-results.md). It also set `DISCOVERY_EVALUATED=true` in the
  uncommitted local `.env` itself, without an owner's attestation. A later review step set it
  back to `false`: the flag is the owner's attestation, and the citation review found three
  critical errors in discovery. `RAG_EVALUATED` stayed `false`, because the RAG gate failed.
- **Runtime AI:** with the owner's AI settings, `gpt-6-luna` can write planner proposals for
  the user to confirm. Its discovery and explanation paths are evaluated but not enabled.
- **Spend:** the evaluation spend, as reserved upper bounds, was 0.916410 USD of a 5 USD cap
  in total, including earlier smoke tests and development rounds.

## Contributor-reported historical notes

Earlier AI use, recorded on the `initial-app` and `ui` branches (some of the chat files named
here were later retired on `main`, as described above):

- The [technical specification](technical-spec.md) was drafted with AI assistance.
- An AI coding assistant (Claude Code, model Claude Opus 5.5) wrote the following under the team's direction: the application code, the tests, the frontend, the Dockerfile, the catalogue texts, keywords and trend notes, the region-type suggestions (`region_types`) in `backend/data/catalogue.json`, the 21 hand-picked regions in `backend/data/places.json`, Svalbard among them, the choice of the example cases and their teaser texts, and this README.
- The same assistant wrote the fixes from each review round, with their tests. An earlier round included the chat adapter (`backend/app/adapters/chat.py`), the MCP adapter (`backend/app/adapters/mcp_server.py`) and the shared plain message for invalid input (`first_problem` in `backend/app/errors.py`); in the frontend, the number pattern of the number check, link rounding and parameters, keyboard picking on the map, focus handling, the region view's notices and definitions, and the period explorer; new component tests with their sample data (`frontend/src/components/testData.ts`); and more catalogue keywords.
- In the latest round the assistant implemented decisions the team made, with their tests. In the backend: the region-type suggestions and the `region_types` field, the Svalbard region, "the selected area" as the name of a region's area mean, the "both places" summary, the warm-up of the suggested prompt's place, the `httpx2` pin, the proxy trust default (`FORWARDED_ALLOW_IPS`), the handling of clients that disconnect, the chat adapter's handling of any failed turn or tool, the two new system-prompt rules, and an API key kept out of the settings' `repr`. In the frontend: the "Dig deeper" panel with its related-variable and "Worth testing here" links and the region-type lookup behind them, the notice under an answer that ended before its numbers were checked, the reading order of the page, the single `h1`, the switch to the basic Plotly bundle, the Prettier setup and a formatting run, and new tests, such as the one that keeps the function-word lists of backend and frontend identical. It also brought the specification, this README and `AGENTS.md` in line with the code.
- On 14 November 2026 the assistant checked POWER's grids and the region map with 22 live calls. Its findings are in [spec 6](technical-spec.md#6-data) and [spec 13](technical-spec.md#13-risks-and-open-decisions).
- After that live check showed that sunlight and cloud cover came from a neighbouring 1° cell for about a third of places, the assistant changed the app to take them from the place's own 1° cell. In the backend it wrote the grid `alignment` field of the catalogue, the changes to `resolve_place` and `fetch_point_series`, the updated comments in `backend/scripts/warm_cache.py` and `backend/tests/test_examples.py`, and their tests. In the frontend it drew the 1° cell outline on the place map, fitted the map to the places and their whole cells, removed the caption saying the 1° grid's position was not confirmed, and wrote their tests. The assistant, not the team, chose this fix, and the team has yet to confirm it.
- In the same round the assistant fixed the reading order of an open case and the region view: at every width the page now holds and shows the verdict, the notes and the Dig deeper panel first, then the settings, then the chart, maps and evidence, and the answer keeps a readable line width. It wrote the tests for the new order and brought the specification and this README in line with both changes.
- The shipped `backend/data/cache.sqlite` was produced by a script (`backend/scripts/warm_cache.py`) from live NASA POWER calls on 13 November 2026. It holds the three example cases and the Nairobi grid point of the suggested prompt. Ten sunlight and cloud cover rows that the app no longer read were deleted from it on 14 November 2026, at the team's request.
- The assistant then added OpenAI as a second provider for the AI helper, under decisions the team made: the `AI_PROVIDER` and `OPENAI_API_KEY` settings with a default model per provider, the Responses API loop in `backend/app/adapters/chat_openai.py`, the shared failure messages in `backend/app/adapters/chat_text.py`, the changes to `backend/app/adapters/chat.py` and `backend/app/config.py` that let both providers share the tools, steps and number check, the tests in `backend/tests/test_chat_openai.py` and `backend/tests/test_config.py`, and the matching changes to the specification, this README, `.env.example` and `AGENTS.md`. The OpenAI path has not yet run against the live API.
- At run time, the optional AI helper uses the Claude API or, when it is configured instead, the OpenAI API, with the model set by `AI_MODEL`. Its notes carry a visible "Written by AI" label.
- On 14 November 2026 the team asked the assistant to overhaul the interface, to make it look good and fit the challenge. The assistant chose and built the result: one dark theme, a globe behind every screen in place of the two flat maps (MapLibre GL JS on OpenFreeMap tiles, replacing Leaflet on OpenStreetMap tiles), the single-column case file with the settings folded under an open case or map, the key to the globe, the mark of a picked point, the app's own magnifying-glass mark, and the notice for a browser without WebGL. It wrote the new modules (`globeStyle.ts`, `globeGeometry.ts`, `globeContext.ts`, `cellTooltip.ts`, and the `GlobeCanvas`, `GlobeStage`, `PlaceLegend` and `SettingsFold` components), their tests, the new stylesheet, and the matching changes to the specification and this README. It checked the result in a desktop browser at 1440px and at an emulated phone width, not on a real phone. The team has yet to confirm the look.
- Later on 14 November 2026 the assistant (Claude Code, model Claude Fable 5.2) reviewed the new interface at 18 screen sizes and states, and the team asked it to fix the first five findings. It wrote the fixes, their tests and the matching changes to the specification and this README: dark sheets under the header and the question bar on a phone, a shorter phone stage with the example prompts in one scrolling row, the side-by-side layout from 640px for tablets and phones held sideways, place names on the left of their markers on a small stage, a question bar that drops a keyword match once the screen has moved on (`frontend/src/questionBarState.ts`), "click the globe" in the case settings, example prompts on the first screen only, and the `GET /api/ai` endpoint, with which the question bar says from the start that the AI is off. The last item replaces the specification's earlier rule that the browser does not know in advance whether the AI is on; the assistant chose that fix, and the team has yet to confirm it. It checked the result in emulated screens from 320px to 1280px wide with the AI off, not on a real phone and not with the AI on.
- The team then asked for the review's other fourteen findings to be fixed, and the same assistant wrote them, with their tests and the matching changes to the specification and this README. On the stage: the choices for a picked point (`PickedPoint`, moved out of the case settings), a caption for a case and a key for a region map (`StageCaption`, `StageNote` and `MapLegend`), a hint for touch screens, and a fade-in of the Earth after its first tiles. On the globe: a tilt held within 55° of the equator, region cells cut at the box, the oceans and the best known countries named evenly, and, on a phone, one finger scrolling the page while two move the globe. In the case file: "Copy link" and "Map this region" under the verdict (`CaseActions`, `clipboard.ts`), placeholders while a case loads (`Skeleton`), the rate of a significant trend as a large figure, a quieter question bar on a case or a map, the region verdict's sentence before its method note, larger panel labels and 44px touch targets. The assistant made the design choices among these; the team has yet to confirm them. It kept the mouse wheel zooming the globe on a wide screen, where the review had called that a scroll trap, because the stage there is fixed beside the page. It checked the result in emulated desktop, tablet and phone screens with the AI off, not on a real device.
- Still on 14 November 2026 the team asked whether the interface could look more creative and less machine-made. The assistant (Claude Code, model Claude Fable 5.2) drew previews over the running app, each labelled as a mock-up made with AI: three ideas, then four looks, then a mix of two of them, then the app's data in that mix. The previews are not part of this repository. A team member chose from them: the mix (an atlas page with a detective's marks), the example cases pinned to the globe, the place inks green, violet, yellow and magenta, and open-licensed typefaces in the repository. The assistant then built that look and wrote its tests and the matching changes to the specification and this README: the stylesheet, the three typefaces, the globe as an engraving in a framed plate with a ring of degree marks, the sheets and their typed tabs (`FileTab`), the verdict's stamp (`VerdictCard`, `InkFilter`), the chart colours, and the example pins with their string (`examplePins.ts`, `ExampleCases`, `GlobeCanvas`). The assistant, not the team, decided what the previews did not show: which open typefaces stand in for the ones in the previews, the names of the oceans waiting for zoom 3, the pin's card standing on the case's northernmost place, the string only from 960px, the stamp standing above the text below 960px, the hint lines of the first screen, and the look of every screen that was not previewed, such as the settings, the notices and the phone layout. It was checked in headless Chrome at four screen sizes with the AI switched off, not on a real phone, not with a screen reader, and not with the AI switched on.
- The team then asked the assistant, as a designer, for the real problems of the new look, and then to fix all seventeen it named. The assistant (Claude Code, model Claude Fable 5.2) wrote the fixes, their tests and the matching changes to the specification and this README. The chart moved right under the verdict, with its explanation under the plot and its rate and 95% interval in its summary (`App.tsx`, `TrendChart`). The question bar steps back on an open case, and the first screen links to the settings ("set up a case by hand"). The stamp lost its uneven-ink filter (`InkFilter` was removed), the tab lost the case's code, and the "Exhibit" tabs went. Capitals, italics, small text and the grain over text were cut back, and links and buttons went from red to ink (`styles.css`). The place inks became teal, ochre, violet and magenta (`placeStyles.ts`). The region map's cells became opaque under a coast line (`globeStyle.ts`). An example's pin now answers the pointer, its card can be clicked, the list waits 0.2 seconds before it turns the Earth, and the idle turn resumes (`ExampleCases`, `examplePins.ts`, `GlobeCanvas`). The stage's buttons grew to 44px for fingers, a tablet's plate fits the Earth, and a phone's hint sits on the frame. The assistant, not the team, chose every one of these remedies and their details, such as the four inks, the 0.2 and 4 second waits, the wording of the new line on the first screen and of the chart's sentence on its rate. It left three things for the team, listed in [spec 13](technical-spec.md#13-risks-and-open-decisions): a true minus sign, a drawn uncertainty band, and where a comparison's chart goes. The fixes were measured and walked through in headless Chrome at seven screen sizes with the AI switched off, not on a real phone, not with a screen reader, and not with the AI switched on.
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
- On 15 November 2026 the same assistant merged `main` (Draft 5 plan and submission documents)
  into the `new-stats` branch. It kept `main`'s plan, submission text and hidden answer actions
  while a case loads, and added the new links ("What is changing here?", "The whole world")
  and the additions' facts to the merged specification and README.
- On 15 November 2026 the same assistant reviewed the interface's main journey in Chrome at
  desktop and phone sizes and, at the team's request, fixed the four problems it ranked first:
  a "Ready to test" card under the question bar that runs the matched case, with years read
  from the question (`QuestionBar`, `readySummary`, `periodFromQuestion`); an "Explore
  further" sheet in place of the row of answer buttons (`CaseActions`); the record years as
  their own sheet after the chart (`RecordYears`); and, on a phone, the globe after the answer
  on every page that has one. The assistant chose the remedies and their wording.
- Later on 15 November 2026 the same assistant measured the case file of an open case (4.1
  screens tall at 1440 by 900 pixels) and, at the team's request, shortened it to 3.2 screens:
  the "Dig deeper" panel became the "Test another variable" group of the "Explore further"
  sheet, which no longer repeats the seasons and period panels as links (`CaseActions`,
  `CrossChecks`); the "On the globe" key and the evidence lesson are folded to one line under
  an answer (`PlaceLegend`, `EvidenceLesson`); and the globe's caption gained the "Zoom in to
  the grid cell" button (`StageCaption`). It wrote the tests and the specification text for
  these changes.
- Later on 15 November 2026 the same assistant, working from a brief the team reviewed and
  agreed, shortened and calmed the case file further: the chart sheet keeps a one-row legend
  and one line on what a point is, with the rest and the summary in words behind "Read the
  chart in words" (`TrendChart`, `chartLegend.ts`); the record years became a small table of the
  API's fields, keeping the API's sentence wherever the fields cannot say it (`RecordYears`,
  `recordRows.ts`, `formatRecordValue`); a one-line verdict holds at the top of the case file
  once the verdict card has scrolled away (`VerdictLine`, `verdictStamp.ts`,
  `useScrolledPast.ts`); and the case file under the verdict is split into the tabs "Answer",
  "Explore", "Evidence" and "Learn" (`CaseTabs`, `caseTabs.ts`), with folded rows set as a
  ruled list inside them and charts in hidden tabs redrawn when shown (`PlotlyChart`). It wrote
  the tests and the specification text for these changes, and chose the details the brief left
  open, such as the table's row labels "Highest", "Lowest" and "Ten-year means". It also fixed
  its earlier "Ready to test" card, which offered the open case's places when a question named
  a place the keyword matcher could not find, such as a country (`questionIsReady`).
- Later on 15 November 2026, at the user's request, the same assistant made a country's name
  find its capital: it downloaded GeoNames' cities15000 and countryInfo files again with the
  user's approval, changed the build script to keep every capital (GeoNames code PPLC) whatever
  its size and mark it, rebuilt `places.json` (77 capitals added, no other place changed),
  ranked a country's capital first in `find_place`, and let the question bar's keyword matching
  accept it (`pickPlaces`). It wrote the tests and the specification and README text.
- Later on 15 November 2026 the same assistant reviewed the interface on the `draft-5` branch
  and, at the user's request, made two changes it had proposed: the evidence panel and the
  evidence lesson are open in their tabs instead of folded (`EvidencePanel`, `EvidenceLesson`),
  and the verdict card of a comparison shows each place in one row and keeps the full verdicts
  and cautions behind one fold (`VerdictCard`). It wrote the tests and the specification text.
- Later on 15 November 2026 the user supplied a poster as a model for the look, and the same
  assistant drew mock-ups of the first screen and a results page in it, labelled as made with
  AI; the mock-ups are not in this repository. At the user's request it then built them.
  - The restyle: tokens and sheets in `styles.css`, the coral case file (`VerdictCard`) and the
    globe's teal colours (`globeStyle.ts`, `GlobeCanvas`). The assistant first coloured the
    case file by its verdict; after the user found that it then did not match the mock-up, the
    case file became coral for every verdict, with the stamp in ink.
  - The two-page layout: the right-hand column of a results page (`CaseRail`,
    `caseRailContext.ts`), "Copy link" in the case file, "Change this case" beside the tabs
    (`CaseTabs`, `CaseLayout`), the settings open on the first screen under the heading "Or set
    it up by hand" (`CaseSettings`), and the example cases in a row after the globe (`App.tsx`).
  - The assistant, not the team, decided what the mock-ups did not show: the record years as
    coloured cards, the example teasers kept on the cards, and every width but 1440 pixels. It
    did not build the mock-ups' "How it works" link or "Preview" label.
  - The user found that the red string from an example to its pins ran off the page once the
    examples sat under the globe, so the assistant removed it (`ExampleCases`,
    `examplePins.ts`, `GlobeCanvas`); pointing at an example still turns the Earth to it.
  - It wrote the tests and the specification text, and checked the pages in Chrome at 1440,
    800 and 375 pixels wide, not on a real phone and not with a screen reader.
- Later on 15 November 2026 the user reported that guided discovery asked the same
  clarification again after they picked an answer. The same assistant found that the model is
  sent the picked answer in the draft but is not told what it means. Rather than change the
  evaluated instructions, it made the server treat a clarification whose choice the draft
  already holds as answered, and return the case ready to confirm (`_answered` in
  `backend/app/adapters/discover.py`), with tests through a fake provider. It was not checked
  against the live model.
- On the evening of 15 November 2026 the team asked the same assistant to make the 30-second
  demo video. It recorded the running app frame by frame in headless Chrome, with the AI
  switched on at the team's request (OpenAI, model `gpt-6-luna`): the question "Is Svalbard
  getting warmer?", the AI's proposal, "Run this case", the verdict, the chart, and the prompt
  "What can't we conclude?" in "Ask about this investigation" with its cited answer. The waits
  for the AI's replies are cut from the video. It wrote the animation around that footage: the
  scenes, the captions and their wording, and the timing. AI reviewers checked frames of the
  cuts and the assistant applied their findings. When it tried the panel's five fixed prompts
  once on that case, four returned "No checked answer". The team supplied the two team photos
  and the team name. Every frame carries the visible watermark "SI / AI-GENERATED VIDEO AND
  VOICE-OVER", and the file's metadata says the same, as the challenge's rule on AI use
  requires. At the team's request the voice-over is an AI voice:
  OpenAI's speech model `gpt-4o-mini-tts` (voice "coral") read the seven caption lines, and
  the assistant shortened the pauses, played the lines 1.15 times faster to fit, and mixed
  them. It checked the words and their timing with OpenAI's transcription model, and could
  not listen to the result. The video and its subtitle file are in `demo-video/`.
- On 15 November 2026, at the user's request, the same assistant checked the README's setup
  steps on Windows, macOS and Linux and rewrote them. It followed them in a fresh copy of the
  repository on an Apple Silicon Mac, where the app, its proxy, a cached example and every
  listed check worked, and the backend tests also passed on Python 3.12. It did not run them on
  Windows or Linux. The new text gives macOS and Linux their own command for copying `.env`,
  states the Node versions the lockfile supports, says to start the backend after building the
  frontend, and adds two install notes: the PowerShell `npm` block, and the Rust toolchain that
  the locked `cryptography` package would need on an Intel Mac or an ARM Windows PC, which was
  read from `uv.lock` and not tried.
- Later on 15 November 2026 the user found that a fresh copy of the repository with their key
  showed no "Ask about this investigation" panel: its `.env` lacked the corpus upload's
  `RAG_VECTOR_STORE_ID` and `RAG_CORPUS_VERSION`. At the user's request the same assistant made
  the panel appear on every case. While explanations are off it takes no question, says which
  AI features are on, and names each setting that keeps it off. The server reports these as
  fixed codes in `/api/capabilities` (`AiSetupGap`, and `planner_gaps`, `rag_gaps` and the
  path gaps in `backend/app/config.py`), never as values; availability is now read from those
  lists, and the earlier availability tests pass unchanged. It chose the panel's wording and
  the codes, rewrote the README's "Configure the AI assistant" section as numbered steps with
  a table of what the panel can say, and wrote the tests and the specification and walkthrough
  text. It checked the panel in Chrome, not with a screen reader.

</details>
