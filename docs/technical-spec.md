# Trend Detective: Technical Specification

Draft 4 - 14 November 2026 - Working title - Prepared with AI assistance.

Status: implementation on `fix/draft3-compliance`, based on MarshyKid's
`initial-app` at d42207c. Core manual workflows, immutable evidence and a bounded
confirmed AI planner are implemented. The statistical study is retained in
[the preregistered plan](../research/inference-plan.md) and
[all confirmation results](../research/inference-results.json). Automated checks
are reported separately from live-model, user-study, browser and deployment evidence.
No award or educational-impact outcome is established by implementation alone.

## 1. Product and release scope

Help a student investigate a regional Earth-system claim and understand what
the evidence supports. A question becomes confirmed settings, NASA data, chart,
rate, applicable significance result and a traceable explanation. Manual controls
always work. This is historical analysis, not forecasting or causal attribution.

The distinctive experience is a guided evidence lesson: compare the same
variable at two places and interpret the evidence, including non-significant
results. A chatbot attached to a chart is not sufficient differentiation.

Core release:

- One primary variable: NASA POWER T2M, named two-metre air temperature.
- Monthly source data, complete annual aggregation and explicit dates.
- Two locations selected for a documented scientific/educational reason before
  inspecting outcomes. Opposite or significant trends are not promised.
- One-place chart and two-place descriptive comparison over matching years.
- Sen's slope per decade; significance only after section 7's validation gate.
- Fixed verdicts, evidence panel, CSV, provenance and pinned shareable links.
- Frozen examples, public manual interface, keyboard and phone-width support.
- One bounded AI question-to-case path if evaluated successfully. Cut this before
  scientific validation, user evidence or submission preparation.

Precipitation, seasons, a second product, documentation retrieval/RAG, period
scanning, regional maps and MCP are conditional extensions. The old twelve-variable
catalogue is a research backlog, not twelve scientifically validated release promises.

All quantitative conclusions come from Python. Fixed templates own verdicts.
Frontend and AI never recompute statistics or replace canonical wording.

## 2. Challenge requirements and judging evidence

Authoritative supplied context: [full challenge](challenge-description.md) and
[organizer requirements](event-information.md). Visualization plus basic trend
analysis meets the stated challenge scope. Every listed mission, AI, forecasting
and multiple significance tests are not mandatory. One meaningfully used NASA
dataset meets the organizer's stated Global Awards data requirement: identify the
product, link sources and explain its contribution. Live APIs and a fully functional
application are not required by that message.

| Requirement | Core implementation | Acceptance evidence |
| --- | --- | --- |
| Identify variables | Supported catalogue with definitions | Users recognize the quantity and units |
| Obtain regional data | POWER adapter with explicit spatial support | Saved response, location, product metadata and coverage |
| Visualize a sufficient series | Complete annual values and fitted line | Verified aggregation and inspectable real example |
| Estimate rate and significance | Sen estimate and validated inference policy | Reference cases, calibration and honest unavailable states |
| Demonstrate NASA use | Evidence panel and credits | Product/version/query and contribution explained |

| Judging criterion | Product focus | Evidence to prepare |
| --- | --- | --- |
| Impact | Students investigate a real regional claim | Observed completion, assistance and interpretation errors |
| Creativity | Guided evidence/comparison beyond chat and charts | One memorable learning interaction and distinction from source portals |
| Validity | Correct quantity, defensible inference and provenance | Reproduction recipe, method study and limitations |
| Relevance | All four challenge objectives | Complete question-to-evidence journey |
| Presentation | One investigation explained clearly | Rehearsed 30-second video or 7-slide presentation and public materials |

Each criterion is scored 1 to 5. Feature coverage does not prove a score,
percentile, nomination or Global Winner probability.

## 3. User experience

First visit shows a question box, manual settings and two worked investigations.
Examples are chosen transparently, never forced to show a desired result.

1. Ask a question or manually choose variable and place.
2. Confirm definition, location, explicit period and annual aggregation.
3. Show actual grid cell and supported dates. Propose adjustments for confirmation;
   do not silently clamp requests or substitute quantities.
4. Draw annual values, gaps and fitted line.
5. Show the fixed verdict, slope/units, valid p-value, method and limitations.
6. Compare the second place over identical complete years.
7. Download values or copy a link pinned to snapshots and analysis version.

A short lesson asks users to interpret evidence before showing guidance. Predefine
tasks before user testing. Rate, statistical evidence, data quality and causation
are distinct. Educational impact is not established by design alone.

| State | Behaviour |
| --- | --- |
| Loading | Progress, bounded wait and retry/cancel where appropriate |
| Significant | Evidence conditional on method assumptions |
| Not significant | Insufficient evidence, without asserting no change |
| Too few years | Available count and application threshold |
| Inference unavailable | Descriptive rate where estimable; reason no valid test is reported |
| No data | No usable annual values for this place and period |
| Source unavailable | Frozen examples remain useful; no invented data |
| AI unavailable/invalid plan | Notice and manual controls; no guessed case |
| Pinned result unavailable | Explicit reproduction failure; offer a distinct new analysis |
| Globe unavailable | Without WebGL the stage says "The globe could not start, because this browser has no WebGL. Everything else works: search for a place in the case settings, and type the edges of a region's box in the map settings." "Draw a box" is disabled |

Provide labels, keyboard access, visible focus and phone-width layout. Use text
and symbols as well as colour. Define terms in place. Say grid cell containing
the city, not exact city measurement. Label AI commentary; hypotheses are unproven.

### Interface

This section and "The globe" describe the delivered interface: an atlas page with a detective's marks, and one globe behind every screen.


| Part | Purpose | What it holds |
| --- | --- | --- |
| Question bar | Entry point; turns a question into a case | Free-text box; on the first screen, example prompts; one line on whether an AI or keyword matching reads the question |
| Case settings | Show exactly what is being tested, and let the user change it | Variable, place or places, period, season |
| Chart | The evidence at a glance | A sheet right under the verdict: yearly values and the trend line, one pair per place; monthly values on request. Under the plot, one line says what a point is, and a summary in words gives each trend line's ends, its rate and, where the evidence panel has one, the rate's 95% confidence interval, in the evidence panel's numbers, because the plot draws the line without its uncertainty |
| Globe | Show where, and let the user pick a place | The Earth behind the page ("The globe" below): a marker per place and, closer in, the outline of its grid cell; on the first screen, a pin for each example case; in region view, grid cells coloured by trend |
| Key to the globe | Name what the globe shows, so nothing is told by colour or position alone | The "On the globe" panel: each place with its marker and the grid cell its values describe, how to pick a point, and "Zoom in to the grid cell" |
| Verdict card | The answer in one sentence | The first sheet of the case file, tabbed "Case file". Each verdict's stamp, then the verdict sentence and the most important caution; for a comparison, the summary sentence first. A significant trend also shows its rate as a large figure above the sentence, such as "+0.79 °C per decade", with the digits and sign of the evidence panel; the sign is set in the text face, whose strokes are sturdier than the display face's. A trend that is not significant gets no figure, so a rate that year-to-year variation alone could produce is not read as the answer |
| Answer actions | Share the answer, and take it further | A row under the verdict, on a case under the verdict's chart. Actions are hidden while a new case or map loads, including while the previous answer remains visible. "Copy link" copies the page's address and answers "Link copied. Anyone who opens it sees this case." (or "this map"); where the browser has no clipboard or refuses, it answers "The link could not be copied. Copy the address from the address bar instead." On a case, "Map this region" opens the region map of a 10° by 10° box around the first place. Its explanation says the map shows rates of change and does not assess significance |
| Evidence panel | Let anyone check the method | Rate with its 95% interval, tests and p-values, number of years, every caution, data source, grid cell, a link to download the values, the steps taken |
| Dig deeper | Suggest the next variable to test | A panel under the verdict and the notes, with the note "Each link tests another variable with the same places, period and season." Under "Cross-check with a related variable", links to the variable's `related` entries. Under "Worth testing here", one line "{place names} · {region type}" for each region type known among the case's places, then links to the catalogue variables whose `region_types` include it, without the case's own variable. The panel is left out when it would hold neither |
| Example cases | Teach by showing | Three ready investigations that open instantly, numbered "Case 1" to "Case 3" in the list and on the globe |


- Detective words appear in labels only: case, case file, evidence, verdict.
- The look is a page from an atlas with a detective's marks on it, in one light theme. The page is paper. The globe is an engraving seen through a framed plate, and the verdict and the evidence are sheets of paper lying on the page, each with a soft shadow. A faint grain lies in the paper of the plate and of the sheets, under their text and never over it. A panel's heading is set as a small label in spaced capitals. Text keeps a contrast of 4.5:1 or more on its ground.
- Type is kept plain where it is read. Spaced capitals are for the labels of panels, the typed tags and the stamps only; buttons and table headings are in sentence case. Italic is for titles and the key figure's units; hints, notes and captions are upright. No text is smaller than 12px.
- The page has two voices. Printed matter is set in serif type: Bodoni Moda for the app's name, the key figure and the titles of cases, and Libre Baskerville for all running text. The detective's marks are typed, in Courier Prime: case numbers, the tab of the case file, stamps, the tags pinned to the globe and the label of text the AI wrote. The three typefaces are open-licensed and served by the app itself; the README credits them.
- Colour is kept for data. Red means rising and blue means falling: on the region map's scale, and as the ink of a verdict's stamp. Each place has an ink of its own, in this order: teal `#039b6a`, ochre `#b57a00`, violet `#6250d6` and magenta `#d55181`, each with its own marker shape. The four were chosen with the dataviz palette validator against the sheet's colour, `#f7f0de`. Every ink has a contrast of 3:1 or more on a sheet: 3.1, 3.2, 5.1 and 3.5. Neighbours in this order stay apart under the common forms of colour blindness, and so does every pair among the first three. The first and the fourth, teal and magenta, are close for people with red-green colour blindness, so a case of four places leans on the marker shapes and the names. The first two inks keep clear of the red and the blue of a direction. The one other colour is the detective's red, for the marks of the first screen where nothing rises or falls: the handle of the app's magnifying glass, the examples' case labels, the pins and the string. Links and buttons are in ink; a link is underlined.
- A verdict's stamp replaces separate labels. It prints the direction over the kind of verdict, in the words used everywhere else: "↑ Rising", "↓ Falling" or "→ Zero estimated slope", over "Significant", "Not significant", "Too few years", "No data" or "Significance unavailable". A verdict with no direction is stamped with its kind alone. The ink is red for a significant rise, blue for a significant fall, and a faded ink for every other verdict, so colour appears only where the test settled the direction. The stamp is turned a few degrees and printed with clean edges, so its words stay sharp; they are ordinary text. From 960px the stamp lies to the right of the text, which runs round it; below 960px it stands above the text.
- The case file has one tab. The verdict card of a case carries a typed tab, "Case file", which is the first thing read in its sheet. The case's `id` (section 5) is not shown: it names the case in data, and a reader can do nothing with it. No other sheet has a tab, because each has a heading that says what it holds.
- Seasons are named by their months, because "winter" means different months in each hemisphere.
- The page has exactly one `h1`: the app's name, which links to the first screen.
- An open case and the region view hold the answer first, then the settings, then the evidence, in one column at every width. On a case the answer is the verdict, its chart, the answer actions, the AI proposal and the Dig deeper panel, and the evidence is the key to the globe, the period explorer and the evidence panel. The chart follows the verdict directly, so the proof is seen with the claim: at 1440 by 900 pixels and at 1280 by 720 the chart of a single place starts on the first screen. The chart lies outside the live region that announces the verdict. In the region view the answer is the verdict for the whole box and the AI proposal, and the evidence is the "Trend in each grid cell" panel with its legend, and the map's evidence. The verdict for the whole box gives its sentence first and the note on how the box was averaged last. The page holds the parts in that order and shows them in that order, so the order on screen, the Tab order and the screen-reader order agree.
- Once a case or a map is on screen, its settings are folded behind one button, "Change this case" or "Change this map", so the evidence follows the answer closely. The settings stay in the page while folded. Every change in them waits for "Run this case", so no case runs before the user confirms it. They are shown unfolded, without the button, while the user has something to do in them: on the first screen, while settings wait for "Run this case", when a case or a map could not be made, and before a map has a box.
- The verdict leads an open case or a map: it is the first sheet on the page. There the question bar steps back: its label is set smaller, and its line on who reads the question is kept for screen readers only. Below 640px the app's tagline is left out there too. On the first screen the question bar's label is the largest line under the app's name.
- Under the question bar the first screen says "Or set up a case by hand: choose the variable, the place and the period yourself." The words "set up a case by hand" are a link to the case settings further down the page.
- A panel's label is set at 0.875rem, so it is never the smallest text in its panel.
- On a touch screen every button, input and disclosure row is at least 44px high, the stage's three buttons included. An example's pin is 17px across and takes a click or a tap within 45px.
- The page holds the header, the question bar and the case file, and then the globe's stage. From 640px, which covers tablets and phones held sideways, the case file is a column on the left and the stage fills the rest of the screen beside it. The column is 22rem to 26rem wide below 960px and 26rem to 37rem wide from 960px, which keeps its lines near 70 characters or under. From 640px to 959px, where the stage is a narrow strip, the plate takes the top of it, 1.3 times as tall as it is wide and never taller than the screen, so the Earth fills it; the view's caption or key lies on the paper under the plate. Below 640px the stage is shown between the question bar and the case file, as a window 30% of the screen high and never under 12.5rem, so the start of the case file shows on the first screen of an ordinary phone. There the globe is seen only through the stage: the header and the question bar above it, and the case file below it, lie on the page's own paper, so no text is drawn over the map. In the page the stage always comes after the case file, so Tab and screen readers meet the verdict before the globe's controls.
- Below 640px the question bar's example prompts share one row that scrolls sideways.
- A keyword match belongs to the screen it was made on. The question bar drops its question and its result line when another page opens, when the browser goes back or forward, and when the settings the match filled in are cancelled. A question that is still being typed or matched stays, and so does the line that says the AI has answered.
- The globe works by keyboard too. With the globe focused, the arrow keys turn it, + and - zoom, and Enter picks the point at its centre, which a crosshair marks while the globe has keyboard focus; a ring around the stage shows the focus. Place markers are not tab stops; the key to the globe names every place. Its note reads: "Click the globe to pick a point, or search for a place in the case settings. With a keyboard, focus the globe, turn it with the arrow keys and press Enter to pick the point at its centre."
- Opening a page from inside the app, such as an example case, a map cell, or a link in the Dig deeper panel, moves focus to the start of the main content. Choosing, removing or dismissing a place in the case settings moves focus to the place search.
- The progress line and the live regions that announce a verdict are in the page before their content arrives, so screen readers announce the content when it appears.
- Next to a `significant` or `not_significant` verdict, on the verdict card and on the region view's verdict for the whole box, a "What does “significant” mean?" disclosure shows the definition from section 7.
- The period control carries a caution: changing the period until a trend turns significant is not evidence.

### The globe

One globe serves every screen. It fills the whole screen behind the page and is seen through the stage. The stage is drawn as a plate: a frame of a heavy line with a fine one inside it, 12px in from the stage's edges and 6px below 640px. The map shows inside the frame only; everything outside it is paper.

- **The Earth.** The Earth is drawn as an engraving in the ink and paper of the page, so that nothing on it is coloured but data. Land is pale paper, shaded in grey by the Natural Earth relief image. The sea is a darker paper under fine lines that follow the parallels, so they stay still while the Earth turns. A line of longitude and of latitude is drawn every 15°. Country borders and place names are in ink, the names in Latin script and the countries in spaced capitals. The whole-Earth view names the countries of the tiles' first rank, where their names have room; the other countries, the oceans, the seas and the bays are named from zoom 3, and the best known country keeps its name where two would overlap. An ocean's name lies near the edge of the whole Earth, where it would run under the ring, which is why it waits for zoom 3. The three longest country names are printed short: "DR Congo", "Congo" and "Central African Rep.". North is always up and the view is always from straight overhead, so a grid cell is always a plain rectangle.
- **The ring.** A ring of degree marks surrounds the whole Earth, as round a hemisphere in an atlas: a full circle just outside the Earth, a fine one further out, and a mark every 5°, longer at every 10° and longest at every 30°. It is decoration and is hidden from screen readers. The globe sizes it to the Earth's disc as the view zooms, and hides it when the Earth with its ring does not fit the stage, as on a region map.
- **The whole-Earth view.** The globe is sized so that the whole Earth fills 0.8 of the stage's shorter side, and it is centred in the stage. This is the view of the first screen and of an open case.
- **First screen.** With no place to show, the Earth turns slowly, 30° every 15 seconds, until the user touches the globe. An example case that is singled out holds the turn up; 4 seconds after the example is let go, the turn goes on from the side of the Earth then in view. With the `prefers-reduced-motion` setting it does not turn, and no view flies: each change of view is a jump.
- **Example cases on the globe.** On the first screen each example case is pinned to the globe: a red pin at each place the case tests, with a typed tag, and a red line between the places of a case that tests two. From 960px the tag holds the case's number and the place's name, such as "1 · Longyearbyen", on the pin's right. Below 960px, where the stage is narrow, it holds the number alone, on the pin's left, the side clear of the stage's buttons. A click on a pin opens its case; a pin on the far side of the Earth is not shown and cannot be pointed at or clicked. A case is singled out in three ways: by resting the pointer on its example in the list for 0.2 seconds, so that a pointer only passing over the list moves nothing; by moving keyboard focus to the example, at once; and by pointing at one of its pins. While a case is singled out, its example lifts off the page as a sheet, and from 960px the pin of its northernmost place shows a card in place of its tag, with "Case 1 · Longyearbyen", the case's title and "Open this case →". The card stands above its pin, so it covers none of the case's other pins, and it is part of the pin: the pointer can cross from the pin to the card, and a click on the card opens the case. For a case singled out in the list, the Earth turns to face its places. For one singled out by its pin, the Earth stays still, so the pin stays under the pointer. From 960px a red string runs from a pin on the example's card to each of the case's pins on the globe, hanging a little, and follows the pins while the Earth turns or the page scrolls; no string is drawn to a pin on the far side. Letting go of the case takes the card and the string away and leaves the Earth as it is; the slow turn goes on 4 seconds later ("First screen" above). The pins and the string are hidden from screen readers and are not tab stops, because the list of examples says the same.
- **A case.** As soon as a case opens, the globe turns to face its places: the middle of the smallest box that holds every place and its grid cell. The whole-Earth view never leans further than 55° toward a pole, so the continents stay the right way up; a place nearer a pole, such as Longyearbyen, is seen above the middle of the Earth. Each place has a marker in its own ink and shape, with its name on a typed tag beside it and a ring that widens and fades around it three times and then rests. The name is on the marker's right from 960px and on its left below that, the side clear of the stage's buttons, where it is cut short at the edge of the stage. When the answer arrives, the outline of each place's grid cell is added without moving the view. At the scale of the whole Earth a cell is only a few pixels wide, so "Zoom in to the grid cell", in the key to the globe, closes in until the cells can be seen (section 6, "Geographic support").
- **Picking a point.** A click on the Earth picks that point; a click on the space around it picks nothing. The picked point is marked with a dashed ring until it becomes a place or is dismissed. What to do with it is offered on the stage itself, in the top left corner inside the frame, in place of the hint: "You picked 1.3°S, 36.8°E", the buttons "Use this place", or "Use instead" and "Compare", or "Add to comparison", and "Dismiss". The buttons read their full labels to screen readers, such as "Compare with Helsinki". The card is announced when it appears, and Tab reaches it straight from the globe. Choosing moves focus to the case settings, where the point waits for "Run this case"; dismissing moves focus back to the stage.
- **A region map.** The globe flies to the box, drawn as a dashed outline of ink on a pale line, until it fills the stage. Each cell is painted in the full colour of its rate, exactly as the key shows it, so a rate looks the same over land and over sea. Coasts, borders and names are drawn over the cells. A cell is drawn only up to the edge of the box, so the map ends where the box does, although a cell whose grid point lies on an edge reaches half a cell past it; a cell without a rate is hatched in ink on paper. Regional maps are descriptive (section 7): pointing at a cell outlines it and shows its grid point and its rate, with the line "Significance not assessed for the map." A click opens it as a case. While "Draw a box" is on, a drag draws a new box, snapped to whole degrees and cut to 10° a side, instead of turning the Earth.
- **Controls.** The stage holds three buttons, "Zoom in", "Zoom out" and "Show the whole Earth", and one line on what the globe does there: "Drag to turn the Earth. Click it to pick a point."; on the first screen while example cases are pinned, "Click a pin to open an example, or pick a point."; on a region map, "Click a cell to open it as a case." From 960px the line sits in the middle of the frame's top edge, as a plate's title does. Below 640px it sits on the left of the frame's top edge, so it covers as little of a small plate as it can. From 640px to 959px it is in the stage's top left corner, inside the frame.
- **Gestures.** Where the stage is fixed beside the case file, from 640px, the globe takes every gesture: a drag turns it, and the mouse wheel zooms it while the pointer is on the stage and scrolls the page elsewhere. Below 640px the stage scrolls with the page, so a swipe that starts on the globe must not trap the page: one finger and the wheel scroll the page, and two fingers, or the wheel with Ctrl held, move and zoom the globe. A tap still picks a point. On a touch screen the line then reads "Turn with two fingers. Tap to pick a point.", "Tap a pin to open it. Turn with two fingers." while example cases are pinned, or "Tap a cell to open it. Move with two fingers." While a box is being drawn, the globe takes every gesture again.
- **Caption and key.** From 640px the stage names what the globe shows, on a card inside a double line, as a title is set on a map: in the lower left corner of the plate from 960px, and on the paper under the plate from 640px to 959px. On a case it holds three lines: the variable, each place beside its marker's shape, and the period and months, with the coordinates of a single place before them, such as "Air temperature", "Longyearbyen" and "78.2°N, 15.7°E · 1981 to 2025, all months". On a region map it holds the key to the colours: the variable, "Rate of change, {units} per decade", the scale with its two ends, the hatch as "No rate", and the period. Both are hidden from screen readers, because the case file says the same. A view that fills the stage, a region map or "Zoom in to the grid cell", stays clear of them.
- **Credit.** The stage shows the credit for the tiles at all times: "OpenFreeMap © OpenMapTiles Data from OpenStreetMap", each name a link. From 960px it sits in the middle of the frame's bottom edge. From 640px to 959px it is in the stage's bottom right corner, and below 640px in its bottom left corner, clear of the buttons on a short plate. The footer repeats it and adds Natural Earth.
- **Loading.** The globe's code loads after the first paint, so the verdict never waits for it. Until it is ready the stage shows the empty plate, and its buttons are disabled. The Earth fades in once its first tiles are drawn, or after four seconds without them, so it never shows as a bare ball on a normal connection.

## 4. Architecture

One FastAPI service serves a built static frontend. REST and optional AI use the
same tools; MCP is deferred. No microservices, accounts or database server.

| Module | Boundary |
| --- | --- |
| models.py | Authoritative Pydantic schemas; generate OpenAPI/frontend types |
| sources/power.py | Only POWER caller; metadata, units and fill values |
| cache.py | Immutable snapshots/manifests and in-flight deduplication |
| stats.py | Pure aggregation/estimators on supplied values and actual years |
| tools/ | Support validation, source coordination and results; no HTTP/model SDK logic |
| verdict.py | Fixed sentences and cautions from structured results |
| adapters/rest.py | HTTP, CSV and safe errors; no scientific calculations |
| adapters/chat.py | Bounded provider calls and validated case proposals |
| Frontend | Settings, chart, evidence and lesson; no scientific recomputation |

Data flow: source adapter -> immutable raw snapshot -> validated normalized series
-> statistics -> structured result -> fixed verdict and rendered evidence.

Analysis is repeatable for identical normalized inputs, snapshots, aggregation,
method configuration and analysis version. Source refreshes and LLM generations
do not inherit that guarantee. Reads may populate a cache; read-only tools means
no external mutation of user resources, not that cache writes never occur.

## 5. Tools and contracts

| Tool | Input and output |
| --- | --- |
| search_variables | Optional query/theme -> enabled variables and definitions |
| find_place | Query -> up to five reviewed matches; ambiguity preserved |
| analyze_trend | Variable/place/dates/snapshot/version -> Investigation |
| compare_places | Same variable/dates, two places -> aligned descriptive comparison |
| get_series | Same case, monthly/yearly resolution -> values, units and provenance |

No arbitrary URLs, generated POWER codes or unchecked coordinates. Initially only
annual is supported. Metadata can suggest defaults; analysis uses explicit dates.
Create concrete Pydantic schemas before integration, generate client types and
validate unknown fields deliberately. Numeric outputs are finite or null, never NaN.

The executable contract is defined in `backend/app/models.py` and its generated
`frontend/src/generatedModels.ts`. The delivered prototype uses these names:

| Contract | Implemented fields/semantics |
| --- | --- |
| AnalyzeTrendInput / ComparePlacesInput | Variable ID; one place or 2-4 places; finite coordinates; optional plain-text labels <=40 characters; from/to/season; optional snapshot_ids and analysis_version; descriptive scan option |
| VariableSummary | ID, definition, units/rate_units, catalogue record start, related variables, spatial/source cautions; grid support is in Place.cell |
| SourceRef | Service name, API version and access date; source/query URL; product identity or explicit unknown release; snapshot_id, nullable raw_sha256 and provenance_status |
| Coverage | Original requested range, source series with missing years as null, each result's analysis_years and the comparison's common_years; excluded years are the difference |
| Trend | Actual n/first/last; Sen rate per decade; line/total change; nullable p/interval/ci_method/OLS p; method_id, inference_status/reason, aggregation and assumptions |
| Verdict | kind, direction or null, canonical sentence and ordered cautions |
| PlaceResult | Requested place plus resolved cell, source annual series, analysis_years, snapshot_id, nullable Trend and Verdict |
| Investigation | Content-derived 64-hex id; analysis_version; original supported requested range; results; source references; steps; pinned app_url; optional common_years and descriptive summary |

Verdict kinds: significant, not_significant, too_few_years, no_data and
inference_unavailable. Comparisons explicitly state that they are descriptive and
not a test of differences. No separate difference p-value or significance vote is
constructed. A zero median rate does not override valid rank-test evidence.

The investigation ID binds requested settings, ordered places, frozen evidence,
actual analysis years, aggregation, method configuration and analysis version.
A place's snapshot ID identifies its immutable normalized evidence. Rendering
clocks and descriptive scan display options do not change the investigation ID.
Omitted pins resolve the current cached data into fixed evidence IDs before sharing.
The runtime version must be bumped when changing the method or analysis contract.

Prototype provenance limitation: legacy seed records have retained normalized
values but no original response bytes or exact upstream release metadata. This is
labelled explicitly; no product release or retrieval time precision is invented.
New fetches retain exact raw bytes, query and available source metadata. Reproduction
from retained analysis inputs is implemented, while complete upstream product-release
tracing for legacy data remains a stricter publication gate from Draft 3.

Comparison uses the intersection of complete years and re-runs both analyses on
that intersection. Report excluded years. Gaps still block inference under section
7; never compress time or silently choose a favourable contiguous subperiod.

## 6. Data

### Primary source and aggregation

Use POWER monthly point JSON, T2M, community=AG, verified coordinates and supported
years. Determine the last complete supported year from response coverage. Inject a
declared cutoff into preparation/tests; statistical code never reads today's date.
POWER supplies reanalysis, not an exact local station measurement.

First entry: air_temp, Celsius input/output, Celsius per decade. Annual aggregation
calendar_day_weighted_mean_v1 is sum(month_mean * calendar_days) / sum(calendar_days).
Respect leap years; require all twelve months or the annual value is missing.
Keep monthly source values unchanged. Convert fill values to null, never zero.

This is our explicit day-weighted statistic. POWER describes its annual processing
as a mean of months, so do not claim exact agreement with YYYY13. Ignore that entry
in our derivation. API and underlying product versions are distinct metadata.

If rainfall is added, distinguish mean rate in mm/day from accumulation in mm/year.
Derive totals as sum(month_rate * calendar_days) only after verifying rate semantics.
Use separate quantity/aggregation IDs and slope units. Defer temperature extrema
until extrema versus average daily extrema are defined. MODIS land-surface
temperature cannot silently replace two-metre air temperature.

### Geographic support

MERRA-2's native grid is 0.5 degrees latitude by 0.625 degrees longitude. Verify
POWER point selection/interpolation and alignment before snapping for cache keys.
Until then cache exact coordinates; resolve spatial behaviour before release.
Handle wrapping, polar/edge cells and boundaries. Preserve canonical precision
in links; rounding must not move a point into another cell. Labels do not change data.

### Provenance and operations

- Preserve immutable raw responses, SHA-256, query, retrieval time, API/product
  identities, units, coverage and transformation configuration. No credentials.
- Freeze examples. Completed historical years can be revised; refresh creates a
  new snapshot. Keep manifests/fixtures and reproducible preparation commands.
- Pinned URLs require retained snapshots and compatible analysis versions. Missing
  versions cause reproduction errors, never silent substitution by current results.
- Fetch missing parameters only; share identical in-flight requests.
- Initial policy: 20-second timeout, one retry on timeout/5xx and at most two
  concurrent POWER calls. Honour Retry-After; 429 causes >=60 seconds cooldown.
- Cache-hit target: <=10 seconds on the named demo host, to be measured. Source
  misses have separate budgets/progress; two 20-second attempts cannot be called
  ten-second total latency.

### Source continuity and additional resources

Block inference across documented source/product discontinuities unless an explicit
adjustment is justified and validated. A badge cannot validate an artificial trend.
Solar/cloud products are deferred; future support must verify homogeneous periods,
including historical SRB/CERES and provisional low-latency source transitions.

The [resource assessment](resource-assessment.md) covers all thirteen suggestions.
Order: POWER core; one prepared Giovanni product if useful; then AppEEARS for a
specific land/vegetation question or NOAA station corroboration. Authentication,
queues, QA and scaling are separate integration work. Prefer prepared demo extracts.

Portals are not independent datasets: MERRA-2 through two portals is still MERRA-2.
Align quantity, units, period and spatial support. Even different products may
share observations; agreement is corroboration, not ground truth. Do not splice
GLDAS versions or missions simply to lengthen the record. KNMI is a manual reference;
papers/tutorials are reading. SWOT's short record and SAR imagery require different
contracts/methods and are deferred. A second product is a quality choice, not a
NASA eligibility condition.

## 7. Statistics

### Descriptive baseline

Use real years. Sen slope is the median pairwise value difference divided by year
difference, multiplied by ten. Its display line passes through median year and
median value. Total fitted change = slope per year * span. OLS slope is descriptive
sensitivity information, not a second significance vote. Annual aggregation does
not establish independent errors.

### Inference gate

Retire the old residual-lag multiplier (1+r1)/(1-r1) as a universal MK/OLS/interval
correction. The old draft reported 8.4% false positives under one nominal 5% setting
without reproducible artifacts here. Those figures and corrected fixtures are not
accepted validation evidence.

Selected implementation: `mk_mc_envelope_v1`, an explicitly reviewed alternative
to the preferred Hamed-Rao candidate. It uses the ordinary two-sided MK score
against frozen Monte Carlo null distributions, taking the maximum tail probability
across six declared AR(1) scenarios. Each scenario uses phi 0, 0.2 or 0.5 and
Gaussian or centered standardized exponential innovations, with a 250-step burn-in.
For each length 20-45, 4,000 development draws produce a table. The plus-one
Monte Carlo probability is `(max_tail_count + 1) / 4001`.

This is conservative for the declared generators. It does not establish validity
for all climate noise, intermediate correlation values, structural breaks or
arbitrary dependence. The UI states these assumptions. This is not Hamed-Rao and
must not be labelled as that published method. Method records freeze rounding to
nine decimals, all development/confirmation seeds, table checksum and configuration.
A separate independent confirmation panel covers all 18 n/phi/innovation settings
specified below; all meet the proposed guardrail. A separately predeclared full-length follow-up
confirmed all 156 length/scenario combinations (20-45 years), plus 18 tied-value
stress settings; every setting passed. See
[the follow-up plan](../research/inference-followup-plan.md) and
[all results](../research/inference-confirmation-all-lengths.json). Conservatism reduces power,
particularly for short records and independent noise; do not describe it as exact
5% calibration or peer-reviewed validation of every climate series.

Application inference is enabled only for individual complete annual POWER T2M
records with 20-45 contiguous years and no source transition. Other variables,
seasons, maps and area averages are descriptive. Constants return zero slope and
p=1 within the eligible scope; this does not prove no environmental change.
Missing/corrupt calibration fails closed. Updating the procedure, table or aggregation
requires a new analysis version and repeat validation; never silently reinterpret a
pinned result with current code.

Product policy: fewer than ten complete annual values -> too_few_years; ten to
nineteen -> descriptive only. Formal inference requires 20-45 contiguous complete annual T2M
values, annual aggregation, the frozen method and a homogeneous source period. These are
conservative application policies, not universal scientific minimums or guarantees.
Missing years, discontinuities, unvalidated methods or failed diagnostics produce
inference_unavailable with a reason and descriptive rate where possible. Do not
compress gaps into consecutive years. Offer new subperiods explicitly. Unrun
p-values are null, not 1.

At least one supported case must pass the inference gate to demonstrate the full
significance objective. Descriptive fallback alone is incomplete. Slope intervals
remain null until a separate serial-dependence-compatible procedure is specified
and coverage-tested. Rate plus a valid significance test meets the basic challenge;
an interval is not additionally mandatory. Do not reuse the retired multiplier
to assert coverage. P-values alone do not describe every form of uncertainty.

### Calibration and numerical checks

Predeclare n=20,30,45; independent and AR(1) noise with correlations 0,0.2,0.5;
Gaussian/skewed innovations; and controlled trend alternatives. Use >=4,000 null
replicates per setting, fixed development seeds and separate confirmation seeds.
Check constants, ties, exact lines, abrupt steps and numerical extremes separately.
Missing years exercise unavailable inference.

Proposed nominal-alpha-0.05 release guardrail: the one-sided 95% binomial upper
bound on false-positive probability must be <=0.07 in every declared supported
null setting. This 7% ceiling is an engineering guardrail, not exact 5% calibration.
Record matrix/criteria before running; report every setting, uncertainty and power.
Never drop failures after seeing results. The retained study covers all 18 confirmation settings with 4,000 independent
replicates each; every upper bound is <=0.07. This evidence is conditional on the
declared generators, not a guarantee for real series. See the linked plan and results.
Optional intervals need a separately predeclared coverage evaluation.

Retain the old fixture inputs:
- A: years 2001-2010; values 2,4,3,5,7,6,8,9,11,10.
- B: years 2001-2012; values 1,3,4,5,4.5,3.5,2.5,5.5,7,8,7.5,6.5.

These are arithmetic/reference inputs only. Independently recompute method-specific
answers; their 10/12-year lengths do not qualify for formal inference. Do not freeze
old corrected outputs or force a desired verdict. Check the Sen estimator against
SciPy using actual years and the chosen intercept. Arithmetic agreement is distinct
from statistical calibration.

### Verdicts and interpretation

| Condition | Verdict |
| --- | --- |
| No complete annual values | no_data: no usable annual values for this place/period |
| Fewer than ten | too_few_years: count and policy threshold |
| Test unjustified/unavailable | inference_unavailable: descriptive rate if possible and reason |
| Validated p < 0.05 | significant: evidence meets the stated threshold |
| Validated p >= 0.05 | not_significant: insufficient evidence for a monotonic trend |

Significant template: "The estimated change in {variable} for the grid cell
containing {place} is {signed rate} {units} per decade over {first}-{last}.
Evidence for a monotonic trend meets the {method} test's 5% threshold."

Non-significant template: "The estimated change is {signed rate} {units} per
decade over {first}-{last}. These data do not provide sufficient evidence for a
monotonic trend under {method}. This does not establish that no change occurred."

Unavailable: "{Reason}. Significance has not been assessed for this case."
Code selects the reason. Handle constants explicitly: no NaNs or spurious evidence.
Zero estimated Sen slope does not prove no change and must not override a valid
rank-test result. With a zero median rate and p below the threshold, retain the
significant kind without a rate direction and explain the two quantities separately. Centralize precision so a tiny
nonzero rate is not falsely reported as exactly zero.

Expose coverage, reanalysis/grid-cell context and method limitations. A p-value is
a probability of a statistic at least as extreme under the null model/assumptions,
not the probability a claim is true. A 95% interval describes repeated-procedure
coverage, not a probability assigned to a fixed true value. Significance is not
practical importance or cause.

Comparison is descriptive with a fixed statement that no between-place difference
test was performed. One significant and one non-significant result does not
establish different rates. A future difference test must handle paired dependence.
Period scans are deferred; if added, label selection/multiple-testing effects and
never promote a favourable scan to confirmation. Regional maps need valid cell
p-values and justified spatial/FDR/coverage policies. FDR cannot fix invalid inputs.

## 8. Built-in AI

### Planner and provider boundary

Begin with schema-constrained extraction, not a free-running agent. The model
proposes a variable ID, place query, explicit/unspecified dates and ambiguity.
Server validation/resolution and user confirmation precede the shared tools.
Never invent coordinates or silently replace unsupported inputs. Missing dates
offer supported defaults for confirmation. No training/fine-tuning is required.

AI_PROVIDER=disabled|ollama|anthropic|openai; default disabled until evaluated. Local Ollama
structured output is implemented with a loopback HTTP endpoint and verified model digest. Select an exact model,
quantization/digest and licence after checking RAM/VRAM and measuring semantic
accuracy and latency. No model size/speed is promised; no model was downloaded or benchmarked as part of this change.

A hosted backend cannot reach a laptop's localhost. Co-locate inference on suitable
hosting or separately approve a protected connection and availability plan. Never
expose an unauthenticated model endpoint to browsers. Otherwise demonstrate AI
honestly as local while the public manual interface remains functional.

Optional Anthropic mode uses a selected exact model ID and server credentials.
No silent local-to-paid fallback. Both providers share schemas and evaluation.
Existing httpx can call local HTTP; another SDK is not needed merely for syntax.

### Explanations and optional RAG

Render canonical verdicts from results. Free-form AI explanations are disabled. Canonical result fields and verdicts
are rendered directly; a model proposes settings only and cannot introduce numeric claims. Validate place, period, quantity, units, direction
and cautions together. Withhold unsupported commentary or use a fixed explanation.
AI cannot overrule unavailable or non-significant outcomes.

A number matcher is only a warning heuristic. No exemptions for small integers or
in-range years: a matching number can refer to the wrong place. The planner is
tool-using AI, not RAG. Retrieval is separate optional work with cited metadata,
versioned corpus, coverage checks and matched RAG/no-RAG cases. Keep reference
answers and held-out questions out of retrieval. User/retrieved text cannot
authorize tools, network destinations or secret access.

### Bounds and evaluation

Implemented bounds: 8 KiB body containing one question of <=2,000 characters;
one concurrent generation across workers sharing the operational DB; one provider
generation per proposal, plus a local model-identity lookup for Ollama. No client
history is accepted and no free-form numeric commentary is displayed. The output
bound is 512 tokens, local context is 8,192 tokens with a conservative input-size
check, and the whole provider operation has a 30-second deadline. Configure context, input/output tokens
and wall-clock deadline before activation. Client history is untrusted and cannot
enforce global quotas. Provide cancellation and manual fallback.

Hosted mode requires AI_EVALUATED=true, an explicit exact model, a daily integer
microdollar cap, owner-supplied input/output microdollar prices per million tokens,
and AI_BUDGET_DURABLE=true. SQLite atomically reserves conservative input-byte/token
and output-token upper bounds before each call. Failed/cancelled/uncertain calls
retain the reservation. No retries or paid fallback are performed. Owners must
keep model identity and accounting rates current; activation is off by default. Turns are not spend caps.
Keep hosted mode off if accounting is unavailable. Counters need durable storage
and concurrency/restart/redeployment checks. Local mode also needs compute bounds.
No chat text is stored server-side.

Evaluate semantic case accuracy, clarification/abstention, latency and critical
factual errors separately from schema compliance. Include invalid JSON/types,
ambiguity, unsupported requests, injection and misleading premises. Predeclare a
practical >=90% correct resolution or appropriate clarification target on a fixed
confirmation suite, with zero critical unsupported numerical/verdict claims.
Report suite size, failures and uncertainty; sample success is not a population
guarantee. Manual mode is the baseline.

## 9. MCP

Deferred until core validity, learning experience and submission materials are
complete. MCP can expose the shared tools and optional chart PNGs; it adds reach,
not scientific validity or mandatory NASA usage. Verify/pin actual SDK/protocol and
prove transport/lifespan/session behaviour with a real client before claiming
support. The old draft's protocol dates/class names are not executable evidence.
Validate origin/host, access, inputs and work limits. Read-only fetches still cost
resources; share source limits/cache across adapters.

## 10. API and URLs

All endpoints are planned until implemented.

| Core route | Purpose |
| --- | --- |
| GET /api/variables | Enabled catalogue and definitions |
| GET /api/places | Reviewed matches |
| GET /api/case | One/two-place Investigation |
| GET /api/series | JSON/CSV with units, coverage and provenance |
| GET /api/examples | Frozen example titles and pinned queries |
| GET /healthz | Liveness without external calls |
| GET /readyz | Catalogue/example manifest/schema loadability |
| /case | Shareable static application route |

Conditional: /api/chat, /api/chart.png, /mcp, /api/map. Disabled capabilities return
clear unsupported responses. SPA fallback must not turn unknown /api/ routes into
successful HTML.

Case query fields: v; one/two p=lat,lon; paired optional label; explicit from/to;
s=annual; snapshot IDs and av=analysis_version. Validate counts, finite numbers,
ranges, order and support. Preserve canonical precision. Latest analyses resolve
to fixed identities. Unavailable pinned identities cause reproduction errors.

Error shape: {error:{code,message,details?}}. Invalid inputs 400; valid unsupported
product/dates/season 422 unsupported_request with support details; unavailable
snapshot/version 409; rate limit 429; source failure 502; unavailable AI/not-ready
service 503. Short records/unsupported inference return normal Investigations with
honest verdicts. No raw exceptions. Quote CSV and protect filenames from labels.

If AI streaming is added, define step/case_plan/case/text/error/done payloads first.
A later tool loop must preserve provider-required within-turn messages; plain-text
history cannot replace the tool protocol.

## 11. Stack, structure and deployment

Selected interpreter for this implementation: standard 64-bit CPython 3.14.5,
recorded in .python-version and Dockerfile; the branch's original Python >=3.12
package constraint remains. Windows automated checks use 3.14.5. The Linux image
is a separate verification target and must not be called tested without a build.
Backend direct pins/transitive resolution are in backend/pyproject.toml and uv.lock;
frontend dependencies are pinned in package-lock.json. Use uv and npm ci.

Planned core: FastAPI, Pydantic, NumPy/SciPy, httpx, SQLite, pytest/Ruff;
React/Vite/strict TypeScript, Plotly and MapLibre GL JS (the globe, on OpenFreeMap tiles). Pin actual compatible versions and
generate lockfiles with one manager during implementation. Matplotlib/MCP are
deferred dependencies. Statistical references remain verification dependencies
unless deliberately adopted at runtime.

Use backend/app for models/tools/sources/adapters, backend/tests for safe checks,
and backend/data for catalogue/places/examples/manifests and small immutable NASA
fixtures. The shipped example cache is copied once into state/power.sqlite; do not modify
the committed seed during operation. Mutable counters and generation leases live
in a separate state/operations.sqlite. Content-addressed snapshots live in
state/snapshots; normalized legacy seed evidence is explicitly distinguished from
new downloads with original raw bytes. Retain state using the named Compose volume. Frontend owns
UI and strict client types. Shared result types are generated from Pydantic;
check the generator output when contracts change. Create research/experiments and reports only for
real plans/evidence; no empty scaffolding or shared packages without consumers.

Shareable docs live in docs/. Personal templates/workflows stay ignored in
docs-personal/. Public documents do not reference local instruction files or link
to ignored guides. README carries actual commands, limitations, NASA and AI credits. An evidence
download endpoint exposes checksum-verified retained snapshot bytes. Missing pins
or unsupported analysis versions fail explicitly; CSV/monthly downloads reuse the
viewed snapshot. Maps are descriptive latest views and are labelled accordingly.

Configuration includes public URL, source deadlines/concurrency, snapshot root,
separate persistent operational DB, analysis version, validated method config,
provider, exact model identity, local URL, context/output/concurrency/deadline
bounds and optional hosted budget. No fabricated model defaults. AI stays off if
required configuration is absent.

Deploy a minimal path early in one HTTPS container serving the built frontend.
Immutable examples ship with the image; mutable usage counters use separate
persistent storage. Image-local SQLite writes do not survive container replacement.
Disable paid AI without durable budget state.

No accounts, stored chat or analytics. Logs contain path/status/duration, not
questions/credentials. Apply validation, plain-text rendering, trusted-proxy
handling, work bounds and deadlines. Tiles require attribution; static coordinates/
cell context keep analysis useful without tiles. Secrets never reach browsers.

## 12. Build plan and submission

Organizer deadline supplied by the team: 15 November 2026, 11:59 PM SGT. Team
finishing cutoff: Sunday 7:30 PM SGT, leaving over four hours. This planning context
does not expand the intentionally trimmed event-information document.

| Stage | Deliverable | Done when |
| --- | --- | --- |
| 1 | Frozen T2M case, manifests, aggregation/estimator, method review/calibration and minimal public health route | Numerical/reproduction checks pass; inference domain validated or explicitly blocked |
| 2 | Manual chart, evidence, fixed verdict, download and pinned links | Supported full journey works; errors/gaps visible; examples survive source outage |
| 3 | Aligned two-place comparison, lesson and small formative study | Correct common years and observed completion/interpretation evidence |
| 4 | Bounded AI and one local/hosted provider | Confirmation gate passes; failures/ambiguity handled; hosting availability explicit |
| 5 | One additional product if useful/feasible | Meaning, period, support, provenance and disagreements documented |
| 6 | Public materials, demo and submission | Required fields/credits complete; public link works; submission confirmed |

Begin science and demo narrative early. Protect stages 1,2,3,6; reduce a study
honestly if access/time is limited. Cut extra sources/AI before validity or
presentation. Maps, scanning, extra variables and MCP are outside the critical path.
Rough hour estimates do not establish feasibility; reassess at working milestones.

Acceptance evidence:

- Software: fills, leap years, gaps, slopes, constants, coordinate boundaries,
  errors, identities and aligned comparison. Unit tests are network-free.
- Science: section 7's references/calibration, including failed conditions.
  Data preparation and statistical calibration are separate evidence.
- Integration: labelled real NASA smoke check and public manual journey, distinct
  from fixture-only passes. Exercise NASA/AI/map-tile outages.
- AI: frozen semantic/abstention/attribution/injection cases, aligned across providers.
  RAG comparison only if retrieval exists.
- Impact: aim for 3-5 intended users if available. Observe anonymous, non-sensitive
  completion, assistance and interpretation of rate/non-significance against a
  simple chart/manual baseline. Counterbalance tasks where feasible. Report
  denominator, errors and limits. This is formative evidence, not proof of a
  population learning effect. Disclose absent users; never invent observations.
- Performance: separately measure cache hits, source misses and model planning
  on named hardware/host with exact model/prompt/schema/context identities.

No outcome is claimed until run. Full significance scope remains incomplete if
only descriptive fallback exists. Label illustrative screens and unbuilt features.

Demo story: student question -> importance -> NASA source/region -> rate/evidence
-> limitation -> what the student understands. Seven slides can cover audience,
case, NASA data, result, distinctive interaction, validation/limits and impact/team/
next step. A thirty-second video shows the same core, not every optional feature.

- [ ] Summary states users, problem and concrete benefit.
- [ ] Demo fits supplied 30-second video or 7-slide format.
- [ ] Public project/supporting-material link works without login.
- [ ] Details match actual approach, tools, data and limitations.
- [ ] NASA sources, versions/access dates and contribution are explicit.
- [ ] Additional data/software/map assets credited where applicable.
- [ ] AI assistance disclosed accurately in project/repository records.
- [ ] Team rechecks current official rules beyond the organizer summary.
- [ ] Submission completed before deadline and completion observed.

Competitiveness is a goal, not a guaranteed award. More connectors or a larger
model do not themselves establish better science, creativity or impact.

## 13. Risks and open decisions

Completed implementation evidence includes the day-weighted data path, original
coordinate selection, strict dates, common-year comparison, frozen snapshots and
versioned links, the predeclared inference studies, scoped unavailable states,
confirmed provider integration with fake transports and atomic cost reservations.

Still required before claiming the corresponding release evidence: original bytes
and complete upstream release metadata for legacy seed records; real-model semantic
and latency evaluation on selected hardware; visual/phone-width browser inspection;
Linux container build and persistent-volume replacement check; public HTTPS deployment;
observed student tasks; and the final submission demonstration. Optional intervals
remain unavailable until independently coverage-tested. No extra source is mandatory.

Main risks are invalid inference sounding authoritative, mismatched quantities,
data revisions, unsupported local hosting, overstated comparison, weak user
interpretation, unbounded costs/compute and excessive scope. The gates above are
release conditions, not issues to conceal with a badge or polished interface.

## 14. Sources and evidence limits

- [Supplied challenge](challenge-description.md)
- [Organizer criteria](event-information.md)
- [Resource assessment](resource-assessment.md)
- [POWER monthly API](https://power.larc.nasa.gov/docs/services/api/temporal/monthly/)
- [POWER processing](https://power.larc.nasa.gov/docs/methodology/data/processing/)
- [POWER meteorology](https://power.larc.nasa.gov/docs/methodology/data/sources_meteorology/)
- [POWER flux continuity](https://power.larc.nasa.gov/docs/methodology/data/sources_fluxes/)
- [POWER referencing](https://power.larc.nasa.gov/docs/referencing/)
- [Hamed and Rao, 1998](https://doi.org/10.1016/S0022-1694(97)00125-X)
- [pyMannKendall](https://github.com/mmhs013/pyMannKendall)
- [SciPy Monte Carlo test and plus-one convention](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.monte_carlo_test.html)
- [Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs)
- [SciPy Theil-Sen](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.theilslopes.html)
- [Ollama structured output](https://docs.ollama.com/capabilities/structured-outputs)
- [Ollama tool calling](https://docs.ollama.com/capabilities/tool-calling)
- [Ollama hardware](https://docs.ollama.com/gpu)
- [Anthropic model documentation](https://platform.claude.com/docs/en/models/overview)

Primary technical references were inspected during review including 13 November
2026. Some official challenge/guide pages did not load; supplied text remains the
basis for local requirements. Recheck current rules before submission. Old live-call
and simulation claims lacking artifacts are leads to verify, not validation.

## Implementation notes for Draft 4

- Coordinates preserve the original floating-point precision through URL round trips;
  resolve the original coordinate before choosing the grid cell. No two-decimal snapping.
- Reject unsupported dates with requested/available ranges; require the user to choose
  supported dates. AI/date defaults are visible proposals and never silently execute.
- Compare exact common complete years; expose the list and fit only those years.
  The comparison is descriptive, not a between-place significance test.
- Annual and seasonal means use calendar-day weights, including leap years and DJF.
- Fewer than ten complete values yields too_few_years and no fitted rate. Ten to
  nineteen yields a descriptive rate with unavailable inference.
- Period scans and regional maps show descriptive rates without p-values or significance
  marks. Area means require a fixed footprint: a missing cell-month makes that month missing.
- /api/plan returns resolved catalogue settings for confirmation. It cannot run NASA
  tools or produce free-form explanations. /api/chat is a compatibility refusal.
- The interpretation lesson asks a question before giving guidance. Actual educational
  impact, real-model semantic accuracy and public deployment remain separate evidence.
- /api/capabilities reports whether the configured planner is available; the default
  UI uses keyword matching and manual confirmation without attempting disabled AI.
- The interface of the `ui` branch (section 3, "Interface" and "The globe") replaces the
  flat Leaflet maps with one MapLibre globe. The question bar learns from /api/capabilities
  whether to offer the AI; the `ui` branch's /api/ai endpoint was dropped in the merge.
- The old free-running provider loops are removed. Contract/test migration rationale
  is recorded in research/test-migration.md; no failures are hidden with skips/xfails.
