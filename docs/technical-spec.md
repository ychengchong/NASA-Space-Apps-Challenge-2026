# Trend Detective: Technical Specification

Draft 3 - 13 November 2026 - Working title - Prepared with AI assistance.

Status: design only, not a working application or passing-test evidence. This
revision incorporates the full challenge, organizer criteria, resource research
and scientific/engineering review. No runtime, dataset or model has been installed.
Unresolved scientific and model-selection gates remain explicit.

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

Provide labels, keyboard access, visible focus and phone-width layout. Use text
and symbols as well as colour. Define terms in place. Say grid cell containing
the city, not exact city measurement. Label AI commentary; hypotheses are unproven.

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

| Contract | Required fields/semantics |
| --- | --- |
| AnalysisRequest | Variable ID; one/two places with finite lat/lon and optional plain-text name <=40 characters; integer from/to; season; optional pinned snapshot IDs and analysis version |
| VariableSummary | ID/name/definition; input/output/rate units; aggregation ID; product/version; supported dates; spatial support and enabled status |
| Provenance | Service separate from product ID/version; source URL and safe query; retrieval timestamp; raw SHA-256/snapshot ID; grid position/extent; temporal/spatial support; transformations/aggregation; metadata and usage URLs |
| Coverage | Requested, valid, missing and excluded year arrays |
| Trend | n/actual first and last year; Sen slope per decade; line endpoints; total fitted change; nullable sen_ci95/ci_method and mk_p; method ID/config; inference status/reason; descriptive OLS slope |
| Verdict | kind, direction or null, canonical sentence and ordered cautions |
| PlaceResult | Requested place, result ID, annual values, Coverage, Provenance, nullable Trend and Verdict |
| Investigation | Schema/analysis versions; case/result IDs; variable; original requested and effective period separately; PlaceResults; steps; app URL; optional descriptive comparison |

Verdict kinds: significant, not_significant, too_few_years, no_data and
inference_unavailable. Comparison includes common_years, fixed summary,
kind=descriptive and difference_tested=false. Unknown product versions are not
invented: unresolved metadata blocks enabling the entry.

case_id binds canonical requested settings and ordered places. result_id also
binds snapshots, actual years, schema, aggregation, method configuration and
analysis version. Each place has its own ID. Rendering timestamps do not change IDs.
Omitted snapshot/version means explicitly labelled latest, resolved to fixed IDs.

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

Preferred candidate: published Hamed-Rao modified Mann-Kendall. This is not a claim
of calibration for every climate series. Before enabling significance:

1. Review the original method. Freeze detrending, rank autocorrelation, lag selection,
   ties, numerical conventions and exact implementation/version in a method record.
2. Check independent reference cases/intermediate calculations. A pinned
   pyMannKendall implementation can be a reference; wrapping one library twice
   is not independent validation.
3. Run a preregistered calibration study with generators, seeds, source/configuration,
   commands, outputs and Monte Carlo uncertainty.
4. Declare support/limitations and freeze method/config. If inadequate, narrow
   support or review an alternative before release. Do not tune for demo significance.

Product policy: fewer than ten complete annual values -> too_few_years; ten to
nineteen -> descriptive only. Formal inference requires >=20 contiguous complete
annual values, a validated method and homogeneous source period. These are
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
Never drop failures after seeing results. No such study has been run for this draft.
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
Zero estimated Sen slope does not prove no change. Centralize precision so a tiny
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

AI_PROVIDER=disabled|ollama|anthropic; default disabled until evaluated. Local Ollama
structured output is supported as a design option. Select an exact model,
quantization/digest and licence after checking RAM/VRAM and measuring semantic
accuracy and latency. No model size/speed is promised; none has been downloaded.

A hosted backend cannot reach a laptop's localhost. Co-locate inference on suitable
hosting or separately approve a protected connection and availability plan. Never
expose an unauthenticated model endpoint to browsers. Otherwise demonstrate AI
honestly as local while the public manual interface remains functional.

Optional Anthropic mode uses a selected exact model ID and server credentials.
No silent local-to-paid fallback. Both providers share schemas and evaluation.
Existing httpx can call local HTTP; another SDK is not needed merely for syntax.

### Explanations and optional RAG

Render canonical verdicts from results. Optional explanations reference result IDs
and allowed fields; render numeric claims from those references rather than trusting
freely generated numeric prose. Validate place, period, quantity, units, direction
and cautions together. Withhold unsupported commentary or use a fixed explanation.
AI cannot overrule unavailable or non-significant outcomes.

A number matcher is only a warning heuristic. No exemptions for small integers or
in-range years: a matching number can refer to the wrong place. The planner is
tool-using AI, not RAG. Retrieval is separate optional work with cited metadata,
versioned corpus, coverage checks and matched RAG/no-RAG cases. Keep reference
answers and held-out questions out of retrieval. User/retrieved text cannot
authorize tools, network destinations or secret access.

### Bounds and evaluation

Initial bounds: 8 KiB request body; up to ten turns of <=2,000 characters each,
subject to that total body limit; one concurrent local generation; <=2 model calls
per turn (planning and optional commentary). Configure context, input/output tokens
and wall-clock deadline before activation. Client history is untrusted and cannot
enforce global quotas. Provide cancellation and manual fallback.

Hosted mode requires an owner-supplied monetary cap, pinned accounting assumptions
and conservative atomic reservations before calls. Turns are not spend caps.
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

Selected interpreter: standard 64-bit CPython 3.14.10, recorded in .python-version.
Direct runtime pins are in [requirements.txt](../requirements.txt), with development
and reference packages in [requirements-dev.txt](../requirements-dev.txt). Combined
installation/resolution remains unverified; these are not full transitive locks.

Planned core: FastAPI, Pydantic, NumPy/SciPy, httpx, SQLite, pytest/Ruff;
React/Vite/strict TypeScript, Plotly and Leaflet. Pin actual compatible versions and
generate lockfiles with one manager during implementation. Matplotlib/MCP are
deferred dependencies. Statistical references remain verification dependencies
unless deliberately adopted at runtime.

Use backend/app for models/tools/sources/adapters, backend/tests for safe checks,
and backend/data for catalogue/places/examples/manifests and small immutable NASA
fixtures. Keep reproducible example cache free of counters/secrets. Frontend owns
UI and generated client types. Create research/experiments and reports only for
real plans/evidence; no empty scaffolding or shared packages without consumers.

Shareable docs live in docs/. Personal templates/workflows stay ignored in
docs-personal/. Public documents do not reference local instruction files or link
to ignored guides. README carries actual commands, limitations, NASA and AI credits.

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

Before implementation: verify T2M product identity, grid behaviour and complete
dates with saved responses; select locations for a reason before reviewing outcomes;
freeze/review candidate inference and run its predeclared study; separately validate
optional intervals; inspect hardware and benchmark an exact local model; choose
hosting/persistent state and local/public AI; establish any hosted budget and
credentials; select an additional product only for a compatible concrete question;
choose place-list licence, formative users and demo format.

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
- [SciPy Theil-Sen](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.theilslopes.html)
- [Ollama structured output](https://docs.ollama.com/capabilities/structured-outputs)
- [Ollama tool calling](https://docs.ollama.com/capabilities/tool-calling)
- [Ollama hardware](https://docs.ollama.com/gpu)
- [Anthropic model documentation](https://platform.claude.com/docs/en/models/overview)

Primary technical references were inspected during review including 13 November
2026. Some official challenge/guide pages did not load; supplied text remains the
basis for local requirements. Recheck current rules before submission. Old live-call
and simulation claims lacking artifacts are leads to verify, not validation.
