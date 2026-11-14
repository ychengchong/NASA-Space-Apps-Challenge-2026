# Trend Detective: Technical Specification

Draft 5 - 14 November 2026 - Working title - Prepared with AI assistance.

Status: the implementation baseline on `main` at 1fa0cf1 includes core manual workflows, immutable evidence,
bounded confirmed AI planner integration and globe interface. Draft 5 defines the
approved next plan on `new-plan`: OpenAI-assisted discovery, documentation retrieval/RAG and
cited qualitative explanations. Their endpoints and interface are implemented, unit-tested
with fake providers and given one local live smoke check; their held-out evaluation, a user
study and a deployment are still planned. Provider tests use fakes; no live-model accuracy is
established.
The statistical study is retained in
[the preregistered plan](../research/inference-plan.md) and
[all confirmation results](../research/inference-results.json). Automated checks
are reported separately from live-model, user-study, browser and deployment evidence.
No award or educational-impact outcome is established by implementation alone.

## 1. Product and release scope

Help a student investigate a regional Earth-system claim and understand what
the evidence supports. A question becomes confirmed settings, NASA data, chart,
rate, applicable significance result and a traceable explanation. Manual controls
always work. This is historical analysis, not forecasting or causal attribution.

The complete journey is ask -> clarify -> choose -> confirm -> analyse -> inspect
-> question -> learn -> share. The distinctive experience combines sourced variable
discovery, a guided evidence lesson, comparison and cited explanations of limitations.
It must help users interpret evidence, including non-significant results.

Approved target release (existing and planned work are separated below):

- One primary variable: NASA POWER T2M, named two-metre air temperature.
- Monthly source data, complete annual aggregation and explicit dates.
- Two locations selected for a documented scientific/educational reason before
  inspecting outcomes. Opposite or significant trends are not promised.
- One-place chart and two-place descriptive comparison over matching years.
- Sen's slope per decade; significance only after section 7's validation gate.
- Fixed verdicts, evidence panel, CSV, provenance and pinned shareable links.
- Frozen examples, public manual interface, keyboard and phone-width support.
- OpenAI natural-language planning and guided variable discovery, including short
  clarification questions, supported suggestions and user confirmation.
- A reviewed documentation corpus, OpenAI-hosted retrieval and an "Ask about this
  investigation" panel with cited qualitative explanations.
- Two guided walkthroughs and a water-related precipitation case. Precipitation
  remains descriptive until its own inference validation gate passes.
- Measured planner/RAG quality, at least five target-user observations, public
  deployment checks and submission evidence, with failures and limits reported.

Temperature is the primary inferential demonstration. Precipitation is the planned
water demonstration with verified quantity/units/coverage. Seasons and maps already
have descriptive prototype paths; broader inference, a second product, additional
connectors, period scanning and MCP are outside the new critical path. The existing
twenty-variable catalogue (section 6, "Catalogue additions") is descriptive outside annual T2M,
not twenty scientifically validated release promises.

OpenAI is the selected implementation path for new AI work: Responses for language
tasks and a hosted vector store for document retrieval. No local model, Ollama,
fine-tuning or separate vector database is required. Existing alternative-provider
planner integrations may remain, but new RAG provider parity is not a release goal.

If a planned gate fails, keep that capability disabled and describe the resulting
submission as a reduced prototype. Do not claim the complete Draft 5 plan is delivered.

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

### Every potential consideration

The challenge calls these optional; the team elects to address all of them. Addressing
a consideration can mean a documented decision or learning feature, not a new connector.

| Consideration | Planned response | Acceptance evidence |
| --- | --- | --- |
| High-school/college students and interested public | Plain language, accessible manual and AI paths | At least five intended users attempt predefined tasks; record assistance/errors |
| Simple definitions | Quantity, units, source and spatial support before confirmation | Users can distinguish a grid-cell estimate from a local measurement |
| Become data detectives | Prediction/interpretation question before learning feedback | Users distinguish rate, evidence, data quality and causation |
| Short questions about what/where | Planner clarification flow and supported choices | Ambiguous goals/places do not silently become a guessed case |
| Demonstration examples | Two guided walkthroughs plus a water case | Cached evidence, documented choice of places/periods and readable steps |
| Optional AI discovery from literature or regional characteristics | Retrieve reviewed documentation to justify supported suggestions | Citations support relevance; general biome context is not presented as verified site-specific evidence |
| Daily/monthly data | Monthly inputs and explicit annual/seasonal aggregation | Missing months, weights, leap years and units verified |
| Non-significant trends remain interesting | Show descriptive rate and insufficient-evidence explanation | No assertion that non-significance proves no change; no searching dates for a favourable p-value |
| Hydrological plotting tools | Review NASA Hydrology Time Series and CUAHSI workflows; prepare a precipitation case | Resource assessment records lessons, access limits and integration decision |
| Seasonality/non-linear trends | Explain aggregation and limits of the monotonic-rate summary; exploratory seasons remain labelled | No claim that annual aggregation removes every cycle or that the method captures all non-linear change |

A longer record can improve detection but does not guarantee significance. No
causal attribution follows from a trend or regional contrast alone.

Judging evidence must include observed task completion (Impact), the connected
discovery/evidence/learning interaction (Creativity), reproducibility and scientific
and AI evaluation (Validity), all four objectives (Relevance), and one clear real
investigation in the demo (Presentation). These are evidence requirements, not scores.

## 3. User experience

The current first visit shows a question box, manual settings and four saved examples.
The planned journey adds two guided walkthroughs and a water case. Choose examples
transparently before inspecting outcomes; never force a desired result.

1. Ask a question or manually choose variable and place. Guided discovery (when
   enabled) offers supported variables with sourced reasons and short clarification questions.
2. Confirm definition, location, explicit period and annual aggregation.
3. Show actual grid cell and supported dates. Propose adjustments for confirmation;
   do not silently clamp requests or substitute quantities.
4. Draw annual values, gaps and fitted line.
5. Show the fixed verdict, slope/units, valid p-value, method and limitations.
6. Compare the second place over identical complete years.
7. Ask about the dataset, method or limitations through the cited explanation
   panel (when enabled). A request for new calculations produces settings for confirmation.
8. Complete interpretation feedback, then download values or share a pinned result.

Explanation prompts, offered as links in the panel: "Explain this simply", "What does this dataset actually
measure?", "What are the limitations here?", "What can't we conclude?" and "What could
I investigate next?" AI explanations sit below the chart and never delay the result.
Show source passages/links, an AI label and a useful unsupported-answer state.
On navigation, cancel or discard explanations for the old investigation.

Keyword/LLM proposals and picked-point choices from /map, /place or /world open
the home settings page before filling the draft, so the user can review and run it.
On /case, proposals continue to use that case's visible pending-settings form.

A short lesson asks users to interpret evidence before showing guidance. On an open
case it is in the "Learn" tab, folded to one line: "Try the evidence lesson"
with "One question on reading a result that is not significant". Predefine
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

This section and "The globe" describe the delivered interface: an atlas page with a detective's marks, and one globe behind every screen. Guided discovery in the question bar and the "Ask about this investigation" panel are built, unit-tested with fake responses and given one local live smoke check against the endpoints; their held-out evaluation, a user study and a deployment are still planned (section 8).


| Part | Purpose | What it holds |
| --- | --- | --- |
| Question bar | Entry point; turns a question into a case | Free-text box; on the first screen, example prompts; one line on whether an AI or keyword matching reads the question. When a keyword match finds a variable and a place, a "Ready to test" card under the question names the case ("Air temperature · Helsinki · from 1990, all months") with "Run this case" and "Change the settings": the user still confirms, where they are looking. Years in the question fill the period: one is the first year, two are the first and the last. An incomplete match sends focus to the settings instead. When the server reports `ai_discovery_available`, a question goes to /api/discover with the settings as they stand (section 8, "Guided discovery"), and the bar's line says "An AI suggests variables from reviewed documentation, with its sources, and proposes settings. Nothing runs until you confirm." The answer appears under the question with the typed label "Written by AI": a short clarification question with its choices as buttons, each of which puts its typed patch (variable, place, years or months) into the settings and asks the same question again with them; up to three suggestion cards, each with the variable's name, the catalogue's own facts under "From the catalogue, not written by AI:" (its definition, "The record starts in {year}.", its note and the years its data source changes, in the words of the case settings and the cautions), the AI's reason as plain text under "Why, in the AI's words:", its sources (publisher, title and section, linked to the manifest's address in a new tab, with "a note by this project, not by NASA" on project notes and the cited passage behind "Show the cited passage") and "Use this variable", which fills the settings with that variable and the answer's proposed places and dates; the parts the question left open, split into those the proposal filled ("Your question left open the first year, so the settings hold the proposed defaults. Check them before you run the case.") and those still to choose ("Still to choose in the case settings: the place."); and the proposal's own notices as plain text, such as "Choose the intended location for '…' in the place search." or "Requested dates are unsupported. Available dates: …", before the server's notice. The status line then says what came: the proposal is in the settings, a clarification waits, suggestions wait, or "No suggestion; you can set up the case by hand." A clarification choice and "Match the words instead" move focus to the question box, since the answer and its buttons leave the page. A "ready" answer fills the settings at once, and when its proposal names a variable and a place the "Ready to test" card offers it; nothing runs until "Run this case". An unsupported answer shows the server's reason with "Set up the case by hand" and "Match the words instead". A failed request falls back to keyword matching with the server's message and "Try the AI again". "Stop" cancels a question on its way, and a new question cancels the last. Suggestions go with their question when another page opens, and a question still on its way is cancelled then, its text kept in the box, so its answer never fills the settings of a page the user has left. Without discovery the bar uses the planner or keyword matching exactly as before |
| Case settings | Show exactly what is being tested, and let the user change it | Variable, place or places, period, season |
| Chart | The evidence at a glance | A sheet right under the verdict, first in the "Answer" tab: yearly values and the trend line, one pair per place; monthly values on request. Its legend is one row above the plot: for one place the kinds of mark ("Yearly values", "Record years", "Trend line"), for a comparison the places, with "Dashed lines are trend lines; rings mark record years." under the plot. Under the plot one line says what a point is. The rest, what a gap means and what the rings mark, and a summary in words of each trend line's ends, its rate and, where the evidence panel has one, the rate's 95% confidence interval, lies behind the disclosure "Read the chart in words", in the evidence panel's numbers, because the plot draws the line without its uncertainty; the same summary is the plot's text alternative. The plot is 300px high and the sheet about 520px for one place at 1440 by 900 |
| Globe | Show where, and let the user pick a place | The Earth behind the page ("The globe" below): a marker per place and, closer in, the outline of its grid cell; on the first screen, a pin for each example case; in region view, grid cells coloured by trend |
| Key to the globe | Name what the globe shows, so nothing is told by colour or position alone | The "On the globe" panel: each place with its marker and the grid cell its values describe, how to pick a point, and "Zoom in to the grid cell". On the first screen the panel is open. Under an answer it is folded to one line, "On the globe" with "The grid cell behind each place, and how to pick a point", because the globe's caption names the places there and holds the zoom; on a case it is in the "Evidence" tab |
| Verdict card | The answer in one sentence | The first sheet of the case file, tabbed "Case file". Each verdict's stamp, then the verdict sentence and the most important caution; for a comparison, the summary sentence first. A significant trend also shows its rate as a large figure above the sentence, such as "+0.79 °C per decade", with the digits and sign of the evidence panel; the sign is set in the text face, whose strokes are sturdier than the display face's. A trend that is not significant gets no figure, so a rate that year-to-year variation alone could produce is not read as the answer. The record years are not on the card: they have a sheet of their own after the chart (section 7, "Record years") |
| Verdict line | Keep the answer in sight while the evidence is read | Once the verdict card of a case has scrolled out of view above the screen, one line holds at the top of the case file and repeats the card in its own words: for each place the card's figure, if it has one, and its stamp's words, such as "+0.79 °C per decade ↑ Rising · Significant". As on the card, a trend that is not significant gets no figure; the line then names the place. In a comparison every place has an entry with its marker shape and name; on a narrow screen the entries may take two lines. The line repeats the card, so it is hidden from screen readers and holds nothing focusable; while it shows, the page keeps room for it at the top (`scroll-padding-top`), so it never covers the element with keyboard focus. It slides in, and appears at once under reduced motion. It is kept on a phone: the question bar scrolls away with the page, so the line never crowds it |
| Answer actions | Share the answer, and take it further | On a case "Copy link" is under the record years in the "Answer" tab and "Explore further" leads the "Explore" tab; on a map they are under the map's answer. Actions are hidden while a new case or map loads, including while the previous answer remains visible. "Copy link" copies the page's address and answers "Link copied. Anyone who opens it sees this case." (or "this map"); where the browser has no clipboard or refuses, it answers "The link could not be copied. Copy the address from the address bar instead." On a case one "Explore further" sheet holds every way on to another page. First come three links with one line each: "What is changing here?" opens the first place's overview; "The whole world" the same variable, period and season in the world sample when it covers the variable; and "Map this region" the region map of a 10° by 10° box around the first place, whose line says the map shows rates of change and does not assess significance. The seasons and the period are folded panels of the case's own page and are not repeated as links. The sheet ends with the group "Test another variable" (next row) |
| Ask panel | Questions about the dataset, the method and the limits of one result | "Ask about this investigation", a sheet in the "Answer" tab after the record years and before "Copy link", shown only when the server reports `ai_explanation_available` and only once the case has loaded (not while a case loads, even with the previous answer on screen). It holds the line "Questions are sent to OpenAI. Answers are written by AI and checked against this result.", a labelled question box of at most 2,000 characters with "Ask" (and "Stop" while a question is on its way), and the five explanation prompts above as links. A question goes to /api/explain with the investigation's ID; the panel is keyed on that ID, so a new investigation, a reload of the case or leaving the page cancels the question on its way and discards its answer, and an answer bound to another ID is never shown. An answer sits under "Written by AI": each block's text as plain text; the result values it points at under "From this result, not written by AI:", each an allowlisted field read from the investigation on screen and written as the evidence panel writes it (a rate such as "+0.48 °C per decade", its interval, the p-value, the total change, the years, the verdict's kind and sentence, the place, the variable, its units, the period asked for and its months; a place's name is added to the label in a comparison); and its sources as in the question bar. No checked answer says why in plain words (no matching documentation, the AI declined or did not finish, the answer failed the checks against this result, or the question is outside what can be explained) and points to the "Evidence" and "Learn" tabs. A question that needs a new analysis shows the proposed settings in words, with the proposal's notices as plain text, and "Put these in the case settings", which fills the settings and moves focus there; nothing runs until "Run this case". The panel's status line says "The AI is writing an answer. The result above does not wait for it." while a question is on its way, then "The answer is below.", "There is no checked answer; the reason is below." or "This needs a new analysis; see below."; a failure is announced by its alert. The numerical result never waits for the panel |
| Evidence panel | Let anyone check the method | Rate with its 95% interval, tests and p-values, number of years, every caution, data source, grid cell, a link to download the values, the steps taken |
| Test another variable | Suggest the next variable to test | The last group of the "Explore further" sheet, headed "Test another variable", with the note "Each link tests another variable with the same places, period and season." Each line of links has its reason above it: "Cross-check with a related variable" for the variable's `related` entries, and "Worth testing here ({place names} · {region type})" for each region type known among the case's places, with links to the catalogue variables whose `region_types` include it, without the case's own variable. The group is left out when it would hold neither |
| Example cases | Teach by showing | Four ready investigations that open instantly, numbered "Case 1" to "Case 4" in the list and on the globe |


- Detective words appear in labels only: case, case file, evidence, verdict.
- The look is a page from an atlas with a detective's marks on it, in one light theme. The page is paper. The globe is an engraving seen through a framed plate, and the verdict and the evidence are sheets of paper lying on the page, each with a soft shadow. A faint grain lies in the paper of the plate and of the sheets, under their text and never over it. A panel's heading is set as a small label in spaced capitals. Text keeps a contrast of 4.5:1 or more on its ground.
- Type is kept plain where it is read. Spaced capitals are for the labels of panels, the typed tags and the stamps only; buttons and table headings are in sentence case. Italic is for titles and the key figure's units; hints, notes and captions are upright. No text is smaller than 12px.
- The page has two voices. Printed matter is set in serif type: Bodoni Moda for the app's name, the key figure and the titles of cases, and Libre Baskerville for all running text. The detective's marks are typed, in Courier Prime: case numbers, the tab of the case file, stamps, the tags pinned to the globe and the label of text the AI wrote. The three typefaces are open-licensed and served by the app itself; the README credits them.
- Colour is kept for data. Red means rising and blue means falling: on the region map's scale, and as the ink of a verdict's stamp. Each place has an ink of its own, in this order: teal `#039b6a`, ochre `#b57a00`, violet `#6250d6` and magenta `#d55181`, each with its own marker shape. The four were chosen with the dataviz palette validator against the sheet's colour, `#f7f0de`. Every ink has a contrast of 3:1 or more on a sheet: 3.1, 3.2, 5.1 and 3.5. Neighbours in this order stay apart under the common forms of colour blindness, and so does every pair among the first three. The first and the fourth, teal and magenta, are close for people with red-green colour blindness, so a case of four places leans on the marker shapes and the names. The first two inks keep clear of the red and the blue of a direction. The one other colour is the detective's red, for the marks of the first screen where nothing rises or falls: the handle of the app's magnifying glass, the examples' case labels, the pins and the string. Links and buttons are in ink; a link is underlined.
- A verdict's stamp replaces separate labels. It prints the direction over the kind of verdict, in the words used everywhere else: "↑ Rising", "↓ Falling" or "→ Zero estimated slope", over "Significant", "Not significant", "Too few years", "No data" or "Significance unavailable". A verdict with no direction is stamped with its kind alone. The ink is red for a significant rise, blue for a significant fall, and a faded ink for every other verdict, so colour appears only where the test settled the direction. The stamp is turned a few degrees and printed with clean edges, so its words stay sharp; they are ordinary text. From 960px the stamp lies to the right of the text, which runs round it; below 960px it stands above the text.
- The case file has one tab. The verdict card of a case carries a typed tab, "Case file", which is the first thing read in its sheet. The case's `id` (section 5) is not shown: it names the case in data, and a reader can do nothing with it. No other sheet has a tab, because each has a heading that says what it holds.
- Seasons are named by their months, because "winter" means different months in each hemisphere.
- The page has exactly one `h1`: the app's name, which links to the first screen.
- An open case and the region view hold the answer first, then the settings, then the evidence, in one column at every width. On a case the verdict comes first and the rest of the case file lies under it in four tabs ("Case file tabs", next), then the AI proposal, then "Change this case", which is reachable whatever tab is chosen. A place's overview (section 7, "What is changing here?") holds its answer, the variables by theme, then its data sources. The chart follows the verdict directly, so the proof is seen with the claim: at 1440 by 900 pixels and at 1280 by 720 the chart of a single place starts on the first screen. The chart lies outside the live region that announces the verdict. In the region view the answer is the verdict for the whole box and the AI proposal, and the evidence is the "Trend in each grid cell" panel with its legend, and the map's evidence. The verdict for the whole box gives its sentence first and the note on how the box was averaged last. The page holds the parts in that order and shows them in that order, so the order on screen, the Tab order and the screen-reader order agree.
- Case file tabs. Under the verdict of an open case a row of four tabs splits the case file, each about one screen: "Answer" holds the chart, the record years, the "Ask about this investigation" panel when explanations are available, and "Copy link"; "Explore" holds "Explore further", the seasons panel, the period explorer and, for a comparison, the gap between the places; "Evidence" holds the evidence panel and the key to the globe; "Learn" holds the evidence lesson. "Answer" is chosen when a case opens. The tabs follow the ARIA tabs pattern: the row is one Tab stop, the arrow keys move along it and wrap round, Home and End go to the first and last tab, and the chosen tab shows its panel at once. Every panel stays in the page while its tab is hidden, so what was opened or typed in it is kept, and a chart drawn in a hidden tab is redrawn to its width when shown. The tab chosen is not part of the address: a link reproduces the case, not the view. The tabs are typed labels standing on an ink rule, the chosen one joined to the page, and each is at least 44px high. Inside a tab the seasons panel, the period explorer, the evidence panel, the key and the lesson are each folded to one line under a rule, with no gap or shadow between consecutive rows; "The gap" stays open, as a ruled panel. The chart lies outside the live region that announces the verdict, and the answer actions are hidden while a case loads.
- Once a case or a map is on screen, its settings are folded behind one button, "Change this case" or "Change this map", so the evidence follows the answer closely. The settings stay in the page while folded. Every change in them waits for "Run this case", so no case runs before the user confirms it. They are shown unfolded, without the button, while the user has something to do in them: on the first screen, while settings wait for "Run this case", when a case or a map could not be made, and before a map has a box.
- The verdict leads an open case or a map: it is the first sheet on the page. There the question bar steps back: its label is set smaller, and its line on who reads the question is kept for screen readers only. Below 640px the app's tagline is left out there too. On the first screen the question bar's label is the largest line under the app's name.
- Under the question bar the first screen says "Or set up a case by hand: choose the variable, the place and the period yourself." The words "set up a case by hand" are a link to the case settings further down the page.
- A panel's label is set at 0.875rem, so it is never the smallest text in its panel.
- On a touch screen every button, input and disclosure row is at least 44px high, the stage's three buttons included. An example's pin is 17px across and takes a click or a tap within 45px.
- The page holds the header, the question bar and the case file, and then the globe's stage. From 640px, which covers tablets and phones held sideways, the case file is a column on the left and the stage fills the rest of the screen beside it. The column is 22rem to 26rem wide below 960px and 26rem to 37rem wide from 960px, which keeps its lines near 70 characters or under. From 640px to 959px, where the stage is a narrow strip, the plate takes the top of it, 1.3 times as tall as it is wide and never taller than the screen, so the Earth fills it; the view's caption or key lies on the paper under the plate. Below 640px the first screen shows the stage between the question bar and the case file, as a window 30% of the screen high and never under 12.5rem, so the start of the case file shows on the first screen of an ordinary phone. On every page with an answer (a case, a map, an overview, the whole world) the stage follows the case file instead, so the answer comes straight after the question bar. There the globe is seen only through the stage: the header and the question bar above it, and the case file below it, lie on the page's own paper, so no text is drawn over the map. In the page the stage always comes after the case file, so Tab and screen readers meet the verdict before the globe's controls.
- Below 640px the question bar's example prompts share one row that scrolls sideways.
- A keyword match belongs to the screen it was made on. The question bar drops its question and its result line when another page opens, when the browser goes back or forward, and when the settings the match filled in are cancelled. A question that is still being typed or matched stays, and so does the line that says the AI has answered.
- The globe works by keyboard too. With the globe focused, the arrow keys turn it, + and - zoom, and Enter picks the point at its centre, which a crosshair marks while the globe has keyboard focus; a ring around the stage shows the focus. Place markers are not tab stops; the key to the globe names every place. Its note reads: "Click the globe to pick a point, or search for a place in the case settings. With a keyboard, focus the globe, turn it with the arrow keys and press Enter to pick the point at its centre."
- Opening a page from inside the app, such as an example case, a map cell, or a link under "Explore further", moves focus to the start of the main content. Choosing, removing or dismissing a place in the case settings moves focus to the place search.
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
- **A case.** As soon as a case opens, the globe turns to face its places: the middle of the smallest box that holds every place and its grid cell. The whole-Earth view never leans further than 55° toward a pole, so the continents stay the right way up; a place nearer a pole, such as Longyearbyen, is seen above the middle of the Earth. Each place has a marker in its own ink and shape, with its name on a typed tag beside it and a ring that widens and fades around it three times and then rests. The name is on the marker's right from 960px and on its left below that, the side clear of the stage's buttons, where it is cut short at the edge of the stage. When the answer arrives, the outline of each place's grid cell is added without moving the view. At the scale of the whole Earth a cell is only a few pixels wide, so "Zoom in to the grid cell", on the globe's caption and in the key to the globe, closes in until the cells can be seen (section 6, "Geographic support").
- **Picking a point.** A click on the Earth picks that point; a click on the space around it picks nothing. The picked point is marked with a dashed ring until it becomes a place or is dismissed. What to do with it is offered on the stage itself, in the top left corner inside the frame, in place of the hint: "You picked 1.3°S, 36.8°E", the buttons "Use this place", or "Use instead" and "Compare", or "Add to comparison", and "Dismiss". The buttons read their full labels to screen readers, such as "Compare with Helsinki". The card is announced when it appears, and Tab reaches it straight from the globe. Choosing moves focus to the case settings, where the point waits for "Run this case"; dismissing moves focus back to the stage.
- **A region map.** The globe flies to the box, drawn as a dashed outline of ink on a pale line, until it fills the stage. Each cell is painted in the full colour of its rate, exactly as the key shows it, so a rate looks the same over land and over sea. Coasts, borders and names are drawn over the cells. A cell is drawn only up to the edge of the box, so the map ends where the box does, although a cell whose grid point lies on an edge reaches half a cell past it; a cell without a rate is hatched in ink on paper. Regional maps are descriptive (section 7): pointing at a cell outlines it and shows its grid point and its rate, with the line "Significance not assessed for the map." A click opens it as a case. While "Draw a box" is on, a drag draws a new box, snapped to whole degrees and cut to 10° a side, instead of turning the Earth.
- **Controls.** The stage holds three buttons, "Zoom in", "Zoom out" and "Show the whole Earth", and one line on what the globe does there: "Drag to turn the Earth. Click it to pick a point."; on the first screen while example cases are pinned, "Click a pin to open an example, or pick a point."; on a region map, "Click a cell to open it as a case." From 960px the line sits in the middle of the frame's top edge, as a plate's title does. Below 640px it sits on the left of the frame's top edge, so it covers as little of a small plate as it can. From 640px to 959px it is in the stage's top left corner, inside the frame.
- **Gestures.** Where the stage is fixed beside the case file, from 640px, the globe takes every gesture: a drag turns it, and the mouse wheel zooms it while the pointer is on the stage and scrolls the page elsewhere. Below 640px the stage scrolls with the page, so a swipe that starts on the globe must not trap the page: one finger and the wheel scroll the page, and two fingers, or the wheel with Ctrl held, move and zoom the globe. A tap still picks a point. On a touch screen the line then reads "Turn with two fingers. Tap to pick a point.", "Tap a pin to open it. Turn with two fingers." while example cases are pinned, or "Tap a cell to open it. Move with two fingers." While a box is being drawn, the globe takes every gesture again.
- **Caption and key.** From 640px the stage names what the globe shows, on a card inside a double line, as a title is set on a map: in the lower left corner of the plate from 960px, and on the paper under the plate from 640px to 959px. On a case it holds three lines: the variable, each place beside its marker's shape, and the period and months, with the coordinates of a single place before them, such as "Air temperature", "Longyearbyen" and "78.2°N, 15.7°E · 1981 to 2025, all months". Once the grid cells are drawn, a button under the three lines reads "Zoom in to the grid cell", or "Zoom in to the grid cells" for a comparison, so the zoom is offered on the globe it acts on. On a region map it holds the key to the colours: the variable, "Rate of change, {units} per decade", the scale with its two ends, the hatch as "No rate", and the period. The words of both are hidden from screen readers, because the case file says the same; the button is not. A view that fills the stage, a region map or "Zoom in to the grid cell", stays clear of them.
- **Credit.** The stage shows the credit for the tiles at all times: "OpenFreeMap © OpenMapTiles Data from OpenStreetMap", each name a link. From 960px it sits in the middle of the frame's bottom edge. From 640px to 959px it is in the stage's bottom right corner, and below 640px in its bottom left corner, clear of the buttons on a short plate. The footer repeats it and adds Natural Earth.
- **Loading.** The globe's code loads after the first paint, so the verdict never waits for it. Until it is ready the stage shows the empty plate, and its buttons are disabled. The Earth fades in once its first tiles are drawn, or after four seconds without them, so it never shows as a bare ball on a normal connection.

## 4. Architecture

One FastAPI service serves a built static frontend. REST and AI use the same
analysis tools. Planned retrieval is an external OpenAI service, not a new local
microservice. No accounts or self-managed database server are required.

| Module | Boundary |
| --- | --- |
| models.py | Authoritative Pydantic schemas; generate OpenAPI/frontend types |
| sources/power.py | Only POWER caller; metadata, units and fill values |
| cache.py | Immutable snapshots/manifests and in-flight deduplication |
| stats.py | Pure aggregation/estimators on supplied values and actual years |
| tools/ | Support validation, source coordination and results; no HTTP/model SDK logic |
| verdict.py | Fixed sentences and cautions from structured results |
| adapters/rest.py | HTTP, CSV and safe errors; no scientific calculations |
| adapters/planner.py | Existing bounded provider extraction and validated case proposals |
| Planned retrieval service | Fixed-corpus search, source mapping and evidence checks; no scientific calculations |
| Planned discovery/explanation adapters | HTTP and bounded model orchestration; never execute an unconfirmed analysis |
| Frontend | Settings, chart, evidence and lesson; no scientific recomputation |

Data flow: source adapter -> immutable raw snapshot -> validated normalized series
-> statistics -> structured result -> fixed verdict and rendered evidence.

Planned discovery flow: question -> supported catalogue + relevant documentation
-> structured suggestions/clarification -> resolved settings -> user confirmation.
Planned explanation flow: question + investigation ID -> server-loaded evidence
-> fixed-corpus search -> bounded qualitative generation -> validated citations
and result-field references -> labelled explanation beside the canonical result.
Climate measurements and document passages remain distinct evidence types.

Analysis is repeatable for identical normalized inputs, snapshots, aggregation,
method configuration and analysis version. Source refreshes and LLM generations
do not inherit that guarantee. Reads may populate a cache; read-only tools means
no external mutation of user resources, not that cache writes never occur.

## 5. Tools and contracts

| Tool | Input and output |
| --- | --- |
| search_variables | Optional query/theme -> enabled variables and definitions |
| find_place | Query -> up to five reviewed matches; ambiguity preserved. A country's name, as GeoNames writes it, finds the country's capital first ("Finland" finds Helsinki, "Armenia" finds Yerevan before Armenia in Colombia), then places whose name equals, starts with or contains the query. The places are the GeoNames cities of 100,000 people or more, every capital whatever its size (GeoNames feature code PPLC), and the hand-picked regions; a town a region names as one of its names is left out, as Svalbard stands for Longyearbyen. GeoNames marks no capital for Israel, the Palestinian Territory or Western Sahara, so their names find none. The question bar's keyword matching takes a capital found this way as the place the question names |
| analyze_trend | Variable/place/dates/snapshot/version -> Investigation |
| compare_places | Same variable/dates, two places -> aligned descriptive comparison |
| get_series | Same case, monthly/yearly resolution -> values, units and provenance |
| season_rates | Same case parameters -> SeasonRates: every place's descriptive rate for all months and each season (section 7, "All seasons at once") |
| place_overview | One place and a period -> PlaceOverview: every catalogue variable's descriptive rate there (section 7, "What is changing here?") |
| world_trend | Variable and period -> WorldTrend: the trend of the frozen whole-world sample mean (section 7, "The whole world") |

No arbitrary URLs, generated POWER codes or unchecked coordinates. Annual
temperature is the inferential core; other supported seasons remain descriptive
under section 7. Metadata can suggest defaults; analysis uses explicit dates.
Create concrete Pydantic schemas before integration, generate client types and
validate unknown fields deliberately. Numeric outputs are finite or null, never NaN.

The executable contract is defined in `backend/app/models.py` and its generated
`frontend/src/generatedModels.ts`. The delivered prototype uses these names:

| Contract | Implemented fields/semantics |
| --- | --- |
| AnalyzeTrendInput / ComparePlacesInput | Variable ID; one place or 2-4 places; finite coordinates; optional plain-text labels <=40 characters; from/to/season; optional snapshot_ids and analysis_version; descriptive scan option |
| VariableSummary | ID, definition, units/rate_units, catalogue record start, related variables, spatial/source cautions, whether the world-mean sample covers it (`world_mean`); grid support is in Place.cell |
| SourceRef | Service name, API version and access date; source/query URL; product identity or explicit unknown release; snapshot_id, nullable raw_sha256 and provenance_status |
| Coverage | Original requested range, source series with missing years as null, each result's analysis_years and the comparison's common_years; excluded years are the difference |
| Trend | Actual n/first/last; Sen rate per decade; line/total change; nullable p/interval/ci_method/OLS p; method_id, inference_status/reason, aggregation and assumptions |
| Verdict | kind, direction or null, canonical sentence and ordered cautions |
| PlaceResult | Requested place plus resolved cell, source annual series, analysis_years, snapshot_id, nullable Trend and Verdict, nullable Records |
| Records | Descriptive record years of the analysis years (section 7, "Record years"): highest/lowest with their ties, first_ten/last_ten means and their change, fixed sentences and a fixed note; null when there is no rate |
| Investigation | Content-derived 64-hex id; analysis_version; original supported requested range; results; source references; steps; pinned app_url; optional common_years, descriptive summary and descriptive gap of a two-place comparison (not part of the ID) |
| Gap | First place's yearly value minus the second's over the common years; n, first/last year, Sen rate per decade, total change, line, same_cell and a fixed sentence (section 7, "The gap between two places") |

Verdict kinds: significant, not_significant, too_few_years, no_data and
inference_unavailable. Comparisons explicitly state that they are descriptive and
not a test of differences. No separate difference p-value or significance vote is
constructed. A zero median rate does not override valid rank-test evidence.

The investigation ID binds requested settings, ordered places, frozen evidence,
actual analysis years, aggregation, method configuration and analysis version.
A place's snapshot ID identifies its immutable normalized evidence. Rendering
clocks, descriptive scan display options and record years do not change the investigation ID:
record years are derived from evidence and analysis years the ID already binds, so adding them
needed no new analysis version and leaves existing IDs and pinned links unchanged.
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

### Planned discovery and explanation contracts

These contracts are implemented once in models.py and generated into
frontend/src/generatedModels.ts. The /api/discover and /api/explain endpoints that
return them, and their interface (section 3), are implemented, unit-tested with fake
providers and given one local live smoke check; their held-out evaluation is still planned.

| Planned contract | Required semantics |
| --- | --- |
| DiscoveryRequest | One question <=2,000 characters; optional typed unconfirmed draft; no arbitrary URLs or raw chat history |
| DiscoveryResponse | Status ready/clarify/unsupported; up to three supported variable suggestions with cited qualitative reasons; optional resolved Proposal; explicit missing fields/clarification question |
| ExplanationRequest | One question <=2,000 characters and a 64-hex investigation ID; never trust client-supplied statistics |
| ExplanationResponse | Status answered/insufficient_evidence/new_investigation_required; investigation ID; corpus version; qualitative blocks, validated citation IDs and allowlisted result-field references; optional proposal awaiting confirmation |
| DocumentSource | Stable source ID and section ID, publisher, title, canonical URL, section title, accessed date, available version and content SHA-256; project notes distinguished from agency sources |
| RetrievedPassage | Source ID, section ID, passage text (<=1,200 characters), provider file identity, content hash and retrieval score; not itself a claim of factual support |
| Citation | Built by the server from one retrieved passage and its manifest section: source and section IDs, title, publisher, HTTPS URL, section title, kind and the cited passage text; never from model text |

Reject unknown source IDs, mismatched investigation IDs, invalid result-field
references and unsupported variable IDs. Citation URLs come from the reviewed
manifest, never model-generated URLs. A provider response failing these checks is
not displayed as an answer. The schemas distinguish retrieval absence, provider
refusal/incomplete output and unsupported questions from a valid finding with a
typed `reason`: no_evidence, provider_refused, provider_incomplete (also an empty
output), validation_failed or unsupported_question. An insufficient_evidence
explanation and an unsupported discovery must carry a reason; every other status
carries null.

The checks are implemented in `backend/app/ai_guard.py` as pure functions over the
provider's strict JSON (`ProviderDiscovery`, `ProviderExplanation`), which is internal
to the AI boundary and never leaves the server. Each failure has a typed guard reason:
unknown_source (an ID the manifest does not know), unretrieved_source (a manifest ID
this request did not retrieve), missing_citation (a suggestion or block that cites
nothing), wrong_investigation, unknown_reference (a place index outside the
investigation), unsupported_variable, inconsistent_status (for example "ready" with no
suggestion), number_in_text, url_in_text, markup_in_text, hidden_characters (control,
format, private-use or unassigned characters), obfuscated_text (a word mixing scripts,
or a checked word spread out with separators), place_query_too_long (a model-written
place query longer than a place label may be, 40 characters), contradicts_verdict,
causal_claim and forecast_claim. Any guard reason gives the contract reason
validation_failed and the provider's text is not returned. Text is checked after NFKC
normalisation, and digits also in their raw form. A digit is allowed only in a
four-digit year (alone or in a range) of the investigation's period, the variable's
record start, the question or draft (discovery), or the retrieved passages, and not
when a unit or rate follows it ("1990 mm", "2010 per decade"); inside an identifier
that starts with a letter and holds no decimal number, such as MERRA-2, T2M or GEOS-5,
that a retrieved passage uses verbatim (so "2C", "10m" or "0.14E-1" in a passage are
never allowed); or inside a trusted catalogue text the model was shown and quotes
verbatim, such as "Wind speed at 10 m". A bare number in a passage is never allowed;
spelled quantities with units ("two degrees"), spelled decimals ("point zero three"),
runs of number words, factors ("a factor of two"), odds ("one in twenty") and percent
signs count as numbers. URLs include any dotted name ending in two or more letters and
"dot gov" forms. Claims of significance are read with their negation (a negator
followed by "denying", "mistaking", "wonder" or a comparative such as "never more
significant" affirms): affirming significance, also in other words ("strong evidence",
"unlikely to be chance", "below the threshold", "a robust trend"), is rejected unless
some place's verdict kind is significant; denying it is rejected when every place's
kind is significant, except in a conditional or definitional clause ("if the result
were not significant"); discovery text may never affirm it; "significance has not been
assessed", the canonical wording of a verdict without inference, is neutral; and
asserting "no change" is always rejected, except in the trend test's null hypothesis
("if there were no trend") and "no change of source". In an explanation, a direction
word (rising, increase, warming; falling, decline, cooling) not negated and not
describing the method or a hypothetical ("how fast values tend to rise", "whether it is
warming") is rejected unless some place's canonical direction matches it, so any
direction claim is rejected when no place has a tested direction; discovery checks no
direction. Causal claims are rejected unless negated ("cannot say what caused"): a
causal connector, a named cause (human activity, emissions, industry and others)
followed by a result word or with a verb such as "produced", "comes from", "reflects"
or "a sign of", and adjectives such as "anthropogenic". Forecasts are rejected unless
negated, including "will persist", "going to rise", "should continue", "ahead" and
"years to come", but not advice such as "you could continue". Every model-written
place query (discovery, and an explanation's plan) gets these text checks too, since
an unresolved one is echoed in a proposal notice; an explanation plan's query equal to
one of the investigation's own place labels stands for that place and is not checked.
These are defensive filters; they do not establish that an answer is supported, and
they reject some correct sentences, which then go unanswered.

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

Draft 5 plans a precipitation demonstration using an explicitly identified POWER
parameter/product. Verify metadata, continuity, support and rate-versus-total
semantics before enabling that case. Its chart and descriptive rate do not acquire
temperature's inference validation. New products require their own source and
analysis contracts; reading the same product through two portals is not independent
validation. Freeze the demonstration inputs and preserve honest provenance limits.

### Resource decisions and demonstrations

Maintain the detailed [resource assessment](resource-assessment.md), with current
access checks and a reason for each decision. No additional connector is implied
by listing a portal, paper or tutorial. Runtime source integrations require the
same quality, unit, spatial-support and provenance review as POWER.

| Resource | Planned consideration/deliverable |
| --- | --- |
| Giovanni | Evaluate one prepared export and its product/region metadata; integrate only if it adds a defined useful investigation |
| NASA Hydrology Time Series | Review a water-variable time-series workflow and access/coverage limits |
| AppEEARS | Assess a concrete land product, scaling/QA and extraction tasks before choosing integration |
| NOAA CDO | Assess suitable observations for corroboration; station and grid-cell quantities are not interchangeable |
| KNMI Climate Explorer | Review discovery/plotting/comparison workflow and source identities |
| SeaWiFS time-series paper | Review its example workflow and caveats; it does not certify our statistical method |
| Trend-testing article and significance guide | Review educational usefulness; verify technical claims against primary references before adopting them |
| CUAHSI | Review hydrological discovery, plotting and export; record lessons for the water case |
| RCM data | Assess a specific derived quantity, access and comparable imagery before any SAR trend work |
| GEO.ca | Assess contextual layers only for a defined location/question |
| SWOT mission | Assess surface-water questions and record length; do not substitute sampling frequency for years of evidence |
| CSA ecosystem overview | Background/use-case discovery; verify product-specific claims separately |
| CSA SAR tutorial | Learning reference for a future imagery pipeline, not an automatic release dependency |

Demonstrations: (1) full temperature investigation, (2) aligned two-place
comparison, (3) water-related descriptive investigation. Include insufficient or
unavailable inference in the learning journey. Opposite/significant trends are not
selection requirements. Explain quantity differences and cross-product disagreement.

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

### Catalogue additions

Eight descriptive variables answer the challenge video's list (snow, the sea, pressure,
water vapour, wind and haze). Each gets a chart, rate, total change and record years; its
verdict is inference_unavailable with the standing reason, which is the intended result.

| id | POWER code | Units | Record | Grid | Theme |
| --- | --- | --- | --- | --- | --- |
| snow_depth | SNODP | cm | 1981 | MERRA-2 0.5° x 0.625° | snow and ice |
| snowfall | PRECSNOLAND | mm/day (water) | 1981 | MERRA-2 | snow and ice |
| snow_cover | FRSNO | fraction 0-1 | 1981 | MERRA-2 | snow and ice |
| sea_ice | FRSEAICE | fraction 0-1 | 1981 | MERRA-2 | snow and ice |
| surface_pressure | PS | kPa | 1981 | MERRA-2 | air |
| water_vapour | TQV | kg/m² | 1981 | MERRA-2 | water |
| max_wind_speed | WS10M_MAX | m/s | 1981 | MERRA-2 | wind |
| haze | AOD_55_ADJ | optical depth | 2001 | 1° x 1°, bounded by whole degrees | air |

Live checks on 14 November 2026 (18 POWER calls for these variables):
- Grids: one regional response per MERRA-2 code (POWER's regional endpoint takes one
  parameter per request) over 60-62°N, 24-26°E returned points on the 0.5° x 0.625° grid.
  Haze came back on 1° cells centred on half degrees in a team-saved regional response, and
  is in `CODES_ON_ONE_DEGREE_GRID`, so a haze box is never answered from MERRA-2 cache points.
- Point calls: the 17 MERRA-2 codes go in one call, the three 1° codes in another; POWER's
  limit is 20 codes per point call. A 20-code response at Helsinki is the test fixture
  `power_point_all_codes.json`; its twelve older codes equal the earlier fixture exactly.
- Land-only and sea-only quantities: over open sea (Gulf of Maine, equatorial Pacific) POWER
  sends its fill value for snow depth, snowfall and snow cover, so a snow case at sea is
  no_data. Snow over snow-free land (Nairobi) is a real zero. Sea ice is a real zero inland
  (Nairobi) and over the ice-free Gulf of Maine. A constant record gives a zero rate and the
  record-years sentence "Every year used has the same value".
- Sea ice has an artificial step. At coastal Helsinki it reads about 0.2 in every May until
  2004 (and 0.25 in July 2006), then about zero; Longyearbyen shows ice in August 2005 and
  2006 only. This fits a change in the satellite-based ocean analyses MERRA-2 takes sea ice
  (and sea-surface temperature) from, but the documented switch year was not verified here,
  so `source_changes` stays empty and the sea-ice trend note states what the data show. It is
  the caution of every sea-ice case. Whether to keep sea ice is a question for the team.
- Strongest wind is each month's highest hourly 10 m wind; the yearly value is the
  day-weighted mean of those monthly highs, not POWER's own annual maximum and not a storm count.
- Haze is CERES SYN1deg Ed4.2 aerosol optical depth at 550 nm, from MODIS retrievals
  assimilated by the MATCH transport model and adjusted toward AERONET. It starts in 2001
  and POWER documents no source change or provisional tail for it, so `source_changes` is
  empty; its trend note says changes in the assimilated satellite data could not be ruled
  out. It is not the MODIS Aqua (MYD08_M3) product Giovanni shows.
- Snow, water vapour and wind carry the standing model caution. Surface pressure is at the
  ground's height in the grid cell, so it differs from a weather map's pressure.
- New region-type suggestions: snow depth for mountains and tundra, snow cover for tundra,
  and water vapour, strongest wind and surface (sea) temperature for "ocean". Haze is not
  suggested: a "Worth testing here" link keeps the case's period, and haze starts in 2001.
- Surface temperature (TS) over open sea is the sea-surface temperature the model is given;
  its definition says so and its keywords include ocean, sea and SST. Two sea places,
  Gulf of Maine (43.0, -68.0) and Equatorial Pacific (0.0, -145.0), region type "ocean",
  were added to REGIONS and places.json without re-downloading the city file.
- The shipped seed gained the seven new MERRA-2 codes at its five example grid points
  (35 rows from five live calls), so the examples still open offline. Its 50 earlier rows
  are byte-identical. Like the earlier rows, the new ones are normalized values without the
  response bytes, so they are labelled as legacy cache evidence. At startup the app adds any
  seed row its state cache lacks (never replacing one), so a state copied from an older seed
  still opens the examples offline.

The fourth example is the challenge video's own question, summer haze in Wisconsin. An
example must be a frozen case query that opens without NASA, and a map is a latest-data view
that cannot be pinned (a haze box is never answered from the cache), so the example is the
brief's fallback: a one-place haze case at Madison (43.07, -89.40), June to August, 2001-2025,
whose 1° cell (43.5, -89.5) is in the shipped seed (three rows, one live call). It is
descriptive: rate +0.004 per decade, haziest summers 2023, 2021 and 2025. Its teaser says it
is descriptive and not the video's chart, because the video uses MODIS Aqua through Giovanni.
The regional form remains available as a map: 42.5-47°N, 93-87°W (30 cells) for June to
August gives an area-mean rate of +0.014 per decade and the same three haziest summers.

Left out and raised as questions: FROST_DAYS (a count per month needs its own aggregation
and units), T2M_MAX_AVG and T2M_MIN_AVG (temperature extremes are deferred until defined;
today's maximum temperature is the month's single hottest hour), GDD10 (POWER answered with
an error), IMERG_PRECTOT and RZMC (no data).

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

### Record years

Every PlaceResult with a rate (ten or more analysis years) carries Records: plain
descriptions of the years the analysis used, never tests. In a comparison these are the
common years; for an area mean, the area-mean series.

- Highest and lowest: up to three years with the highest yearly values, highest first, and up
  to three with the lowest, lowest first. Values are compared at nine decimals, as the trend
  test compares them. Only years above the record's lowest value can be among the highest,
  and only years below its highest value among the lowest, so a record that is zero in most
  years (snow, sea ice) never calls its minimum a high. The lowest list skips the years
  already listed as highest, so no year is in both lists, even when many years share a
  middle value. Equal values are listed earliest year first;
  `highest_tied` and `lowest_tied` count the years neither listed nor skipped whose value
  equals the last one listed, and the sentence adds "1 more year has" or "N more years have
  the same value as {year}". When every year used has the same value nothing is ranked and one
  sentence says so: "Every year used has the same value ({units}): {value}." A value that is
  not zero but rounds to zero at the variable's decimals gets more digits, as a rate does.
- First and last ten: with at least twenty analysis years, the plain mean of the first ten
  analysis years and of the last ten, and their change (last minus first) in the rate units.
  The windows never share a year. A missing year is skipped, so a window then spans more than
  ten calendar years; its sentence names its first and last year. Fewer than twenty years
  leaves this comparison out. A fixed 1981-2010 baseline was rejected because records such
  as aerosol optical depth start in 2001 and a requested period may start later.
- Sentences come from verdict.py: "Highest yearly values used ({units}): {value} in {year},
  ...", the same for lowest, and "The mean of the last ten years used, {a} to {b}, was
  {change} {higher|lower} than the mean of the first ten, {c} to {d}." (or "was the same as"
  when the two means are equal at nine decimals). The fixed note reads: "These facts describe the yearly values used.
  They are not tests, and their significance was not assessed."
- The record years are a sheet of their own, "Record years", right after the chart (and after the region's and the world's verdicts). The sheet shows the fields, not the sentences, as a small table under the heading, with "yearly values used ({units})" beside it: a row "Highest" and a row "Lowest", each listing year and value, and a row "Ten-year means" holding "{a} to {b}: {mean} · {c} to {d}: {mean} · change {change} {rate units}". Values use the frontend's number format with the digits of the sentences, so a value that rounds to zero gets more digits as the sentence's does. Where the fields cannot say what a sentence says, the row shows that sentence as written: a list with tied years (`highest_tied` or `lowest_tied` above zero) shows its sentence, and a record where every year has the same value shows the one sentence "Every year used has the same value" in a row "Every year". With fewer than twenty years the "Ten-year means" row is left out. In a comparison each place has its own table, captioned with its marker shape and name. The note follows once, unchanged. One place takes about 190px at 1440 by 900. The chart rings the listed years, drawn from the API's lists, and says so in its text. In a
  comparison the chart plots each place's whole series while the rings and the table cover
  the common years, and the chart text says so.

### All seasons at once

A folded "Compare the seasons" panel on an open case asks GET /api/seasons with the case's own
parameters and pins. The tool `season_rates` analyses each place exactly as the case would
for all months, December to February, March to May, June to August and September to
November, from the same evidence (the same snapshots for a pinned case; in a comparison,
each season's common complete years). It needs no NASA call beyond the case's own fetch.

- Each row (`SeasonRate`) gives the season, the complete years used (n, first, last), the
  Sen rate per decade and the total change, the verdict kind, whether the row was assessed,
  and a fixed sentence from verdict.py. No interval, p-value or test of the difference
  between seasons is returned.
- Only the all-months row of annual T2M can be assessed, as the inference gate allows; it
  names that test's verdict ("The trend test for all months finds it significant."). Every
  other row with a rate ends "Significance was not assessed." A season with fewer than ten
  complete years has no rate ("{season}: N complete years, too few for a rate.").
- The fixed note reads: "Each rate is descriptive. Rates for different seasons can differ by
  chance alone, and no difference between seasons was tested."
- The panel draws the five rates against a zero line, lists the sentences as its text, and
  links every other season as an ordinary case. The default answer of /api/case is unchanged.

### What is changing here?

A person usually arrives with a place, not a variable. GET /api/overview (tool
`place_overview`) gives every catalogue variable at one place, on the /place page, reached
from the picked point on the globe ("What is changing here?") and from an open case's
actions (its first place, over the case's period).

- Each variable runs over its own record within the requested period: from the later of
  `from` and its record start, to `to`. A missing `from` is the earliest record start (1981)
  and a missing `to` the last complete year. A variable whose record starts after `to` gets a
  row without years ("Its record starts in {year}, after the period ends.").
- Each row (`OverviewRow`) gives the variable, its grid cell, the complete years used, the
  rate per decade, the total change, the verdict kind, whether it was assessed, its highest
  and lowest year (from section 7, "Record years") and one fixed sentence: "{rate} per decade
  from {first} to {last}, {total} in all, over {n} complete years; highest in {year}, lowest
  in {year}." followed by "Significance was not assessed." or, for annual T2M alone, "The trend
  test finds it {significant|not significant}."
- Each row also carries `caution_sentences`, a list of fixed Python-rendered texts
  for every applicable verdict caution, in priority order. Display them beside the
  row, including variable notes and source changes crossed by the actual analysis
  years. The general descriptive-view note does not replace these cautions.
- Rows keep the catalogue's order, grouped by theme on the page; nothing is sorted by rate
  and no combined score exists, because rates in different units cannot be compared.
- The fixed note reads: "This view cannot say which of these changes are real. Every rate is
  descriptive, except that annual air temperature reports its trend test. Rates in different
  units cannot be compared by size, so the variables keep the catalogue's order."
- One fetch per grid serves every variable on it: a new place costs one call per grid (two),
  a cached place none. The overview is a latest-data view that pins no snapshots; each
  variable's name opens it as an ordinary, pinned case.

### The gap between two places

A comparison of exactly two places carries `gap`: the first place's yearly value minus the
second's in each common complete year, the years the comparison already uses. Its Sen rate
per decade, total change and line come from the gap series itself, not from subtracting the
two places' rates (the two differ). Ten or more common years are needed for a rate.

- Sentence: "The difference between {A} and {B}, {A} minus {B}, changed by about {rate}
  per decade from {first} to {last}, over {n} common years. A positive rate means {A} rose
  compared with {B}. The difference was not tested; this is a description." It holds for
  every combination of signs, including both places falling.
- Two places in the same grid cell with consistent retained values read: "{A} and {B}
  are in the same grid cell, so the difference between them is zero in every year."
  Same-cell snapshots that differ on any common complete year are rejected with
  bad_request (HTTP 400): differing evidence versions are not a spatial contrast.
  No common complete years uses the no-data gap sentence, never the zero-difference
  sentence. Too few common years otherwise retains its fixed sentence.
- No difference p-value is constructed (section 5). The existing summary sentence is
  unchanged; the gap's sentence follows it on the verdict card, and a small chart draws the
  API's gap series, its trend line and a zero line. Comparisons of three or four places have
  no gap. The gap is an Investigation field, outside the hashed evidence, so IDs and pinned
  links are unchanged.

### The whole world

POWER's regional call takes a 10° box at most, so the whole world is a frozen sample. The
script `scripts/build_world_mean.py` reads 162 points, one every 20° of latitude from 80°S to
80°N and of longitude from 180°W, each on every variable's grid as a case would read a place
(one call per point and grid, 324 calls, through the app's POWER client, resumable from its
cache file in state/). For each variable it writes the monthly mean of the sample cells,
weighted by the cosine of latitude, with the fixed footprint of an area mean (a month missing
at any point is missing), to `data/world-mean.json` with the sample, API versions, access
dates and build date. It was built on 14 November 2026 from POWER API v2.10.0, through 2025.
World air temperature gives +0.17 °C per decade over 1981-2025, near published estimates of
about 0.2 °C; a sample that stops at 80° misses the fastest-warming polar caps.

- Cloud cover is missing in the polar-night months of 1984-2000 at 79.5°S, so under the
  fixed footprint the world cloud cover has complete years only from 2001; haze starts in 2001.
- Covered: the fourteen catalogue entries marked `world_mean`. Snow depth, snowfall, snow
  cover, sea ice and both soil wetness variables are left out, because they exist only on
  land or only at sea; asking for them gives 422 unsupported_request.
- GET /api/world (tool `world_trend`) reads the file, never NASA, and analyses the series like
  an area mean: Sen rate, total change, record years, no p-value, verdict kind
  inference_unavailable. Its sentence names the sample instead of a grid cell: "The estimated
  change in {variable} averaged over a sample of {N} grid points across the whole world is
  {rate} per decade over {first}-{last}. This is an estimate from a sample, and significance has
  not been assessed."
- The page, the steps and the source line say it is an estimate from a sample of {N} points.
  The fixed note adds: "A sample describes world temperature far better than world rainfall or
  wind, which change over short distances." Its source is marked `prepared_sample_mean`.
- An open case links "The whole world" for the same variable, period and season when the
  sample covers the variable. The chart offers no monthly values, which no place stands behind.

## 8. Built-in AI

### Status and selected path

Existing: question-to-settings extraction and manual confirmation; AI is disabled
by default. Implemented for retrieval: the discovery/explanation contracts, the
retrieval settings and separate capability flags, the bounded vector-store search,
the investigation lookup, and the owner-run corpus build and upload scripts. The owner
has uploaded the reviewed corpus to an OpenAI vector store. The /api/discover and
/api/explain endpoints and their interface (guided discovery in the question bar and
the "Ask about this investigation" panel) are implemented, unit-tested with fake
providers and given one local live smoke check. Planned: their held-out evaluation, a
user study and a deployment. No discovery or explanation quality or live provider
evaluation is claimed by this document. The target is OpenAI-only for these new
features; existing Ollama/Anthropic planner support is an alternative, not a required
installation. Choose an exact model after semantic, latency and cost evaluation.

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

### Planned guided discovery

Keep /api/plan for extraction. Add /api/discover for broad goals such as investigating
environmental change around Singapore or a rainforest. Offer up to three enabled
variables with definitions, data availability, relevant source citations and limits.
Suggestions concern scientific relevance, not a promise of a trend or significance.
General regional context must not become an unsupported claim about a specific site.

Clarify quantity, ambiguous place, dates or unsupported requests using short typed
questions/choices. The browser resubmits the current question and typed draft, not
unbounded history. Location resolution remains deterministic and catalogue-backed.
No investigation or NASA call executes from a model proposal. Confirmation is
required even when every setting is filled automatically.

Implemented (`backend/app/adapters/discover.py`): POST /api/discover takes a
DiscoveryRequest, searches the vector store once with the question (at most four
passages; a hit whose source and section the manifest does not list, or whose text is not
part of that section's reviewed file, is dropped), and,
only when a citable passage remains, makes one strict-schema generation. The model
returns a status, up to three catalogue variable IDs each with a reason and cited
passage IDs (a passage's section ID, or a source ID naming every retrieved passage of
that source), up to two place queries, from/to/season or null, missing fields and an
optional clarification with up to four choices, each a typed patch (variable, place
query, from, to, season). After the checks of section 5, "ready" builds the Proposal
with the planner's resolve_plan from the first suggestion, the place queries and the
dates, keeping the draft's dates and season where the question gave none; a choice's
place query resolves to one exact reviewed find_place match, and a choice left with
nothing to set is dropped. Citations are built by the server from the manifest and
the retrieved text. No retrieved evidence returns "unsupported" with no_evidence and
no generation; a refusal or incomplete output returns provider_refused or
provider_incomplete; failed checks return validation_failed; a model "unsupported"
returns unsupported_question; each with a manual-fallback notice. The instructions say
that the question, draft and passages are untrusted data; draft coordinates are not
sent to the provider.

### Planned corpus and retrieval

Use reviewed NASA POWER methodology, variable/source/validation and resolution
documentation, relevant MERRA-2 documentation and documents for actually supported
products. Include the project's method/limitations notes with explicit project
authorship; never attribute our custom method to NASA. News, arbitrary uploads and
unreviewed web search are outside the release corpus.

An owner-run ingestion command prepares section-based documents, preserves original
source metadata and hashes, uploads them to an OpenAI vector store and waits for
indexing completion. Hosted indexing handles chunking/embeddings; no local embedding
model is required. Keep a versioned source manifest, file-ID mapping and content
snapshots in protected deployment storage; public docs contain only approved
redistributable passages/metadata. Do not upload secrets, private documents or tests.

Query the fixed vector store explicitly from the backend before generation. Start
with at most four returned passages, each capped at 1,200 characters, filtered to the
relevant source/product/variable where possible. Tune these starting bounds only
against development questions, then freeze them before held-out evaluation. Preserve
enough section context; do not remove qualifiers to meet a length cap. Retrieval
scores are ranking signals, not probabilities that an answer is correct.
Both endpoints search with the question as asked and no attribute filter: the corpus has
no attribute that ties a source to a variable, and prefixing the variable's name pulled
in that variable's catalogue sections ahead of the notes on interpretation in a local
development check (a causal-premise question then found no project note). Revisit this on
development questions before the held-out evaluation. A retrieved passage is citable only
when its whitespace-normalised text is part of the reviewed section file that the
manifest lists by path and SHA-256 (checked when the manifest is read), so a stale or
foreign file in the vector store carrying a section's attributes is never shown or cited.

Source IDs resolve to canonical links in the manifest. Show the cited passage and
its source context. Persist corpus/retrieval provenance separately from numerical
snapshots without storing user questions or generated chat text. A numerical share
link reproduces the numerical investigation, not a nondeterministic AI answer.
If no relevant evidence is available, return insufficient_evidence; citations alone
do not establish support. Keep evaluation questions and reference answers out of
the corpus and record a matched RAG/no-RAG evaluation.

### Planned explanations and result protection

Add /api/explain for "Ask about this investigation". Load the investigation by ID
on the server, verify its frozen evidence and bind the response to that ID. If the
result is unavailable, fail explicitly instead of analysing fresh data. Navigation
cancels/discards the old response; the numerical result never waits for AI.
Implement a server-owned result lookup/manifest as part of this path; an ID alone
is not assumed to reconstruct settings. Bind it to retained snapshots and analysis
version without storing user questions or model responses. Implemented as the
`investigations` table of the operations database: investigation ID, pinned case
query (with `snap=` and `av=`), analysis version and record time. GET /api/case
records a pinned case only while explanations are available. Because a case query
holds user-typed place labels, a record is kept for 24 hours and the table keeps at
most the newest 10,000 rows; opening the case again records it afresh.

Render canonical verdicts and numbers directly. Generated blocks explain concepts,
dataset context, limitations and evidence-supported next questions. They must not
calculate, paraphrase or replace the statistical verdict or introduce numerical
findings. Any displayed rate/date/unit/result reference is an allowlisted field
rendered by application code from the trusted investigation. Check place, period,
quantity, direction, inference status and cautions together. Withhold unsupported
commentary; AI cannot overrule unavailable/non-significant outcomes or infer causes.

Validate cited source IDs against the actual retrieved passages and validate their
relationship to each answer block. Schema/citation/number checks are defensive
filters, not proof of truth; assess entailment and factual support in human-reviewed
evaluation. A number matcher alone cannot protect against the wrong place or claim.
Questions requiring new calculations create a new proposal for confirmation.

Implemented (`backend/app/adapters/explain.py`): POST /api/explain takes an
ExplanationRequest and looks the ID up with `Cache.find_investigation`. The recorded
case query is rebuilt with the shared tools on a data source that refuses every fetch,
after checking that it pins one snapshot per place with the recorded analysis version
and that every snapshot is retained and passes its checksum; the rebuilt ID must equal
the requested ID. An ID that is not on record (or whose record is older than 24
hours), a missing or corrupt snapshot, or a different rebuilt ID fails with 409
`investigation_unavailable` before any paid call, and NASA is never called. Retrieval
then searches once with the question (at most four passages); no citable passage
returns insufficient_evidence with no_evidence and no generation. The model receives
the variable's catalogue name, definition and note, the period, place labels, each
place's canonical verdict kind, direction and caution codes, the allowlisted field
names it may reference, and the passages. It receives no value of the result: no rate,
p-value, interval or count, and not the canonical verdict sentence, which states the
rate (a block references verdict.sentence to show it). The catalogue texts can hold
fixed numbers of a definition, such as "550 nm", which text may quote verbatim. It
returns a status, blocks of text with cited passage IDs and field references, and for
"new_investigation_required" a plan that resolve_plan turns into a proposal awaiting
confirmation. The proposal changes only what the plan names (no silent substitution): a
variable or year the plan leaves open is the investigation's own, and a plan that names
no place, or one of the investigation's own place labels, keeps those places at their
exact coordinates; only other place queries go to find_place. The plan's season is
always given by the model. Every block of an answer must cite a
retrieved passage. A model abstention returns no_evidence; refusals, incomplete
output and failed checks return their reasons; no provider text is returned then.

User and retrieved text are untrusted evidence, never instructions authorizing
tools, URLs, uploads, secret access or source changes. Render plain text and curated
links. No model-controlled Python/SQL execution or open-ended tool loop is allowed.

### Bounds and evaluation

Existing /api/plan bounds: 8 KiB body containing one question of <=2,000 characters;
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

/api/discover and /api/explain use independent readiness/evaluation flags
so a working planner does not imply working RAG. Each accepts <=8 KiB and one
question <=2,000 characters, performs at most one explicit retrieval and one model
generation, has a 30-second total deadline and a 1,024-token output cap, and shares
the operational generation lease/rate limits. No automatic retry or agent loop.
The typed current draft and server-loaded investigation are separately size-bounded.
Future changes to these limits need recorded latency/cost evaluation.

Configuration (all off by default): RAG_ENABLED, RAG_VECTOR_STORE_ID (must have
the shape of an OpenAI vector store ID, `vs_` and up to 128 letters, digits, `_`
or `-`), RAG_CORPUS_VERSION (must equal the manifest's corpus_version),
RAG_SEARCH_MICROUSD_PER_CALL (owner-supplied integer price per search call),
RAG_EVALUATED (enables explanations) and DISCOVERY_EVALUATED (enables discovery),
on top of the planner's hosted OpenAI settings. /api/capabilities reports
ai_planner_available, ai_discovery_available and ai_explanation_available
separately. Absent or mismatched corpus/model/configuration disables only the
affected AI path.

Extend the existing atomic budget accounting before activating RAG: reserve model
and retrieval charges, separately cap ingestion/indexing and storage costs, define
vector-store expiry/cleanup, and reconcile actual usage. The upload script takes a
required owner-supplied `--max-bytes` cap and refuses, before any call, a corpus
whose section files exceed it. It records the uploaded bytes, the store's reported
usage bytes and every attempt (earlier attempts at a version under `superseded`)
in state/corpus-files.json, and the store expires 30 days after its last use.
Uploaded files do not expire; delete them from the IDs in that state file. Daily turn counts are not
spend controls. Unknown prices or insufficient durable budget state disable paid
operations. Owner-run ingestion is separate from public requests and is not enabled
merely by setting a runtime AI flag. Keep credentials server-side and inform users
that questions go to OpenAI. Use store=false for Responses; this does not imply
zero provider retention, and uploaded vector-store files persist separately.

Evaluate semantic case accuracy, clarification/abstention, latency and critical
factual errors separately from schema compliance. Include invalid JSON/types,
ambiguity, unsupported requests, injection and misleading premises. Predeclare a
practical >=90% correct resolution or appropriate clarification target on a fixed
confirmation suite, with zero critical unsupported numerical/verdict claims.
Report suite size, failures and uncertainty; sample success is not a population
guarantee. Manual mode is the baseline. The expanded release gates in section 12
supersede the earlier minimum planner suite size in the evaluation protocol.

## 9. MCP

Deferred until core validity, learning experience and submission materials are
complete. MCP can expose the shared tools and optional chart PNGs; it adds reach,
not scientific validity or mandatory NASA usage. Verify/pin actual SDK/protocol and
prove transport/lifespan/session behaviour with a real client before claiming
support. The old draft's protocol dates/class names are not executable evidence.
Validate origin/host, access, inputs and work limits. Read-only fetches still cost
resources; share source limits/cache across adapters.

## 10. API and URLs

The core numerical routes, /api/plan, /api/discover and /api/explain exist. The
discovery and explanation routes are tested with fake providers only; they answer 503
until their evaluation flags are set (section 8).

| Core route | Purpose |
| --- | --- |
| GET /api/variables | Enabled catalogue and definitions |
| GET /api/places | Reviewed matches |
| GET /api/case | One/two-place Investigation |
| GET /api/series | JSON/CSV with units, coverage and provenance |
| GET /api/seasons | SeasonRates for the case query; /api/case and its ID are unchanged |
| GET /api/overview | PlaceOverview for p (one place), optional label, from, to and s |
| /place | A place's overview page: what is changing here |
| GET /api/world | WorldTrend for v, from, to and s; 422 unsupported_request for a variable the sample does not cover |
| /world | A variable's whole-world page |
| GET /api/examples | Frozen example titles and pinned queries |
| GET /api/capabilities | Separate planner, discovery and explanation availability |
| POST /api/plan | Existing bounded question-to-settings proposal; user confirms |
| POST /api/discover | DiscoveryRequest -> DiscoveryResponse: supported variable suggestions, cited reasons, clarification and a proposal; no execution |
| POST /api/explain | ExplanationRequest -> ExplanationResponse: cited qualitative blocks bound to a recorded pinned investigation, or an explicit unanswered state with its reason |
| GET /healthz | Liveness without external calls |
| GET /readyz | Catalogue/example manifest/schema loadability |
| /case | Shareable static application route |

The retired /api/chat refuses requests; new discovery/explanations do not restore
the old free-running loop. Existing /api/chart.png, /mcp and /api/map have separate
scope/status and are not prerequisites for the new AI paths. Disabled capabilities
return clear unsupported responses. SPA fallback must not turn unknown /api/ routes
into successful HTML. No public ingestion/upload route is planned.

Case query fields: v; one/two p=lat,lon; paired optional label; explicit from/to;
s=annual; snapshot IDs and av=analysis_version. Validate counts, finite numbers,
ranges, order and support. Preserve canonical precision. Latest analyses resolve
to fixed identities. Unavailable pinned identities cause reproduction errors.

Error shape: {error:{code,message,details?}}. Invalid inputs 400; valid unsupported
product/dates/season 422 unsupported_request with support details; unavailable
snapshot/version 409; an explanation whose investigation is not on record, has
missing retained evidence or rebuilds to another ID 409 `investigation_unavailable`;
rate limit or AI budget/turn/busy limits 429 `rate_limited`; source failure 502;
unavailable AI/not-ready service 503 `ai_unavailable`. An over-8-KiB or invalid AI
request body is 400 `bad_request`. Short records/unsupported inference return normal Investigations with
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
generate lockfiles with one manager during implementation. Matplotlib/MCP already
exist in the dependency set; their broader release role is separate from the AI
plan. Statistical references remain verification dependencies
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

Planned RAG adds an owner-managed corpus manifest and citation mapping alongside
protected document snapshots. Use existing httpx for OpenAI HTTP calls unless a
separately justified SDK dependency is approved. Keep numerical-source fetching,
document ingestion and model calls in distinct modules. No local model install is
needed. Deploy one HTTPS app with persistent /app/state, verified proxy settings
and configured public URL. Test container replacement, evidence links and AI cost
state. Document ingestion and hosted vector-store retention are separate operations.

## 12. Build plan and submission

Organizer deadline supplied by the team: 15 November 2026, 11:59 PM SGT. Team
finishing cutoff: Sunday 7:30 PM SGT, leaving over four hours. This planning context
does not expand the intentionally trimmed event-information document.

| Stage | Deliverable | Done when |
| --- | --- | --- |
| 1 | Scope/contracts and existing scientific baseline | Draft 5 planned/implemented status is explicit; numerical/reproduction checks pass; inference domain is preserved |
| 2 | OpenAI planner and guided clarification | Exact model selected using development evaluation; clear requests resolve, ambiguous requests clarify, every proposal waits for confirmation |
| 3 | Reviewed corpus and hosted retrieval | Manifest/source mapping, hashes, indexed files, relevant retrieval and missing-evidence behaviour verified |
| 4 | Cited discovery and explanation UI | Bounded /api/discover and /api/explain meet section 5/8 contracts; citations and result binding checked; failures preserve manual results |
| 5 | Guided temperature/comparison/water demonstrations | Two walkthroughs and a precipitation case use frozen evidence; quantity/support/units verified; no extra inference implied; every resource/consideration has a recorded decision |
| 6 | Scientific, AI, accessibility and user evaluation | Release gates below run on frozen suites; report failures, uncertainty, latency/cost and at least five intended-user observations |
| 7 | Deployment and submission | HTTPS/container/persistence journey checked; video/deck, NASA/AI attribution, public materials and submission completion verified |

Preserve the working manual/statistical foundation throughout this sequence. Begin
the demo narrative and deployment preparation early, but do not claim a later stage
is complete before its dependencies and checks pass. Additional connectors, broader
inference, model training and provider parity are outside the critical path. Reassess
at each working milestone; rough hours do not establish feasibility. If time runs
out, disable failed AI features and disclose reduced scope rather than compromising
scientific validity, user evidence or the submission. Such a prototype does not
constitute completion of all Draft 5 features.

Acceptance evidence:

- Software: fills, leap years, gaps, slopes, constants, coordinate boundaries,
  errors, identities and aligned comparison. Unit tests are network-free.
- Science: section 7's references/calibration, including failed conditions.
  Data preparation and statistical calibration are separate evidence.
- Integration: labelled real NASA smoke check and public manual journey, distinct
  from fixture-only passes. Exercise NASA/AI/map-tile outages.
- AI planner/discovery: at least 50 held-out prompts spanning exact requests, broad
  goals, missing dates, comparisons, ambiguous places, unsupported quantities,
  seasons, forecasting, misleading premises, injection and failures. Predeclare
  expected resolution/clarification and a >=90% pass target. JSON validity alone
  is not success; record counts, errors and uncertainty for the exact model/version.
- RAG: at least 40 held-out questions spanning definitions, source/grid context,
  limitations, absent/conflicting evidence and adversarial premises. Review
  retrieval relevance separately from answer support and citation correctness;
  predeclare a >=90% fully supported-answer-or-appropriate-abstention target.
  Compare the same questions with/without retrieval under matched settings; report
  regressions as well as improvements. Do not ingest test questions or answer keys.
- Critical AI gate: zero invented numerical findings, unsupported verdict changes,
  fabricated citations or successful tool/secret authorization injections in the
  release suite. This is an observed suite result, not a general safety guarantee.
- Impact: observe at least five intended users. Observe anonymous, non-sensitive
  completion, assistance and interpretation of rate/non-significance against a
  simple chart/manual baseline. Counterbalance tasks where feasible. Report
  denominator, errors and limits. This is formative evidence, not proof of a
  population learning effect. Obtain agreement before observing tasks. Predefine
  success, report every attempt and changes made. Disclose a smaller/absent study
  as a release-evidence gap; never invent observations.
- Performance: separately measure cache hits, source misses, planning, retrieval
  and explanations on the named host with exact model/prompt/schema/corpus/context
  identities. Report latency distributions, timeouts and cost per completed/failed
  operation against predeclared practical limits and the configured budget.
- Deployment: test real browser, keyboard/mobile and WebGL fallback, copied pinned
  link in a fresh session, exports, NASA/OpenAI/tile outages, cancellation, rate and
  budget exhaustion, Linux container build and persistent-volume replacement.

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

Draft 5 additionally requires implementation and held-out evaluation of discovery,
corpus ingestion/retrieval, cited explanation contracts/UI and expanded cost
accounting. Open decisions: exact OpenAI model and current prices; reviewed corpus
sections/version; content retention/redistribution; relevant retrieval thresholds;
precipitation product/aggregation; practical latency/cost limits; and deployment
resources. Resolve these using recorded checks before enabling the affected path.
No paid API calls, document uploads or new connectors are performed by this spec update.

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
- [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- [OpenAI retrieval and vector stores](https://developers.openai.com/api/docs/guides/retrieval)
- [OpenAI hosted File Search](https://developers.openai.com/api/docs/guides/tools-file-search)
- [OpenAI data controls](https://developers.openai.com/api/docs/guides/your-data)
- [POWER data FAQ](https://power.larc.nasa.gov/docs/faqs/data/)
- [NASA MERRA-2 overview](https://gmao.gsfc.nasa.gov/gmao-products/merra-2/)
- [CUAHSI hydrological information system](https://www.cuahsi.org/data-services/hydrologic-information-system)
- [Local-event reproduction of challenge/resources](https://hackathlone.com/challenges/earth-system-trend-detective)

Primary technical references were inspected during review on 13-14 November 2026,
including OpenAI retrieval/structured-output/data-control docs and NASA/CUAHSI
sources for Draft 5 planning. The production challenge and current judging-guide
pages did not fully load; the supplied statement/organizer criteria and local-event
reproduction inform the requirement mapping. Do not substitute an older judging
guide as current evidence. Recheck current rules before submission. Old live-call
and simulation claims lacking artifacts are leads to verify, not validation.

## Existing implementation baseline (Draft 4 and UI fixes)

- Coordinates preserve the original floating-point precision through URL round trips;
  resolve the original coordinate before choosing the grid cell. No two-decimal snapping.
- Reject unsupported dates with requested/available ranges; require the user to choose
  supported dates. AI/date defaults are visible proposals and never silently execute.
- Compare exact common complete years; expose the list and fit only those years.
  The comparison is descriptive, not a between-place significance test.
- Annual and seasonal means use calendar-day weights, including leap years and DJF.
- Fewer than ten complete values yields too_few_years and no fitted rate. Ten to
  nineteen yields a descriptive rate with unavailable inference.
- GET /api/world and the /world page (section 7, "The whole world") read a frozen 162-point
  world-mean sample, descriptive only, built by scripts/build_world_mean.py.
- A two-place comparison carries a descriptive gap (section 7, "The gap between two
  places"), never tested; the summary sentence is unchanged.
- GET /api/overview and the /place page (section 7, "What is changing here?") list every
  variable's descriptive rate at one place, unranked, with only annual T2M assessed.
- GET /api/seasons (section 7, "All seasons at once") gives every season's descriptive rate
  beside all months; only the annual T2M row can carry an assessed verdict.
- Record years (section 7) list the three highest and lowest yearly values and compare the
  last ten analysis years with the first ten; they are descriptive and leave IDs unchanged.
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

## Draft 5 planned delivery checklist

These boxes remain unchecked until implementation and observed evidence exist.
Specification approval alone does not activate AI or complete a release gate.

- [ ] Implement guided clarification/discovery and source-backed variable suggestions.
- [ ] Select and evaluate an exact OpenAI model; retain manual confirmation/fallback.
- [ ] Review/version the corpus, ingest/index it and verify retrieval/source mapping.
- [ ] Implement cited qualitative explanations bound to server-loaded investigations.
- [ ] Render numerical references from Python fields; reject invalid citations/claims.
- [ ] Verify ingestion/retrieval/storage accounting and independent capability flags.
- [ ] Prepare two walkthroughs and a truthful water-related demonstration.
- [ ] Record a decision for every consideration and listed resource.
- [ ] Run >=50 planner/discovery and >=40 RAG held-out cases plus matched no-RAG cases.
- [ ] Observe >=5 target users and report completion, assistance and interpretation errors.
- [ ] Verify public HTTPS, browser/mobile/keyboard, outages and persistent redeploy.
- [ ] Publish accurate NASA/AI credits and complete the demo/submission requirements.
