# Trend Detective: submission materials

Status: prepared text for the current prototype, updated 15 November 2026. No public
demo or hosted app URL exists yet. The Draft 5 AI paths are built; their evaluation
status is in the [evaluation results](evaluation-results.md). Complete the final
actions below before describing the submission as finished.

## Project summary

Trend Detective helps students investigate environmental claims using NASA Earth
science data. Users choose a variable, location and period, inspect a time-series
chart, and see an estimated rate of change with statistical evidence where the
method has been validated. The tool distinguishes a detectable trend from
insufficient evidence and explains why neither establishes a cause.

NASA POWER monthly measurements drive the analysis. Evidence panels identify the
source and geographic grid cell, while downloadable values, retained snapshots
and pinned case links make investigations inspectable and reproducible. Worked
examples, place comparisons and an interpretation question help users reason
about the evidence rather than merely read a chart. Manual settings and keyword
questions work without an AI key. Optional AI planning, guided discovery and cited
explanations are built and on by default (the owner's choice, although their evaluation gates
were not met); see the
[evaluation results](evaluation-results.md) for their status.

## Project details

The prototype combines a React/TypeScript interface, Plotly charts and a MapLibre
globe with a Python/FastAPI backend. Monthly NASA POWER data is cached and retained
as versioned evidence. Python computes calendar-day-weighted annual or seasonal
means, preserves missing values, estimates Sen's rate per decade, and produces
fixed verdict text. Comparisons use common complete years and are descriptive.

Formal significance is restricted to eligible annual two-metre air-temperature
records of 20-45 contiguous complete years under the documented inference policy.
Other quantities, seasonal results and maps remain descriptive. Unvalidated
intervals and p-values are unavailable rather than guessed. The method's simulation
assumptions and limits are in the [technical spec](technical-spec.md#7-statistics)
and [verification record](verification.md).

The intended benefit is accessible, traceable environmental investigation for
students and interested members of the public. Educational impact has not yet
been established by an observed user study.

## NASA data and contribution

- [NASA POWER monthly API](https://power.larc.nasa.gov/docs/services/api/temporal/monthly/): numerical monthly time series behind the plots and estimated changes.
- [POWER meteorological sources](https://power.larc.nasa.gov/docs/methodology/data/sources_meteorology/): product context for supported meteorological quantities.
- [NASA MERRA-2](https://gmao.gsfc.nasa.gov/gmao-products/merra-2/): underlying reanalysis for the primary T2M investigation; a grid-cell estimate, not an exact local weather-station measurement.
- [POWER processing](https://power.larc.nasa.gov/docs/methodology/data/processing/): source-processing context; our named day-weighted statistic need not equal POWER's supplied annual value.

These data were obtained from the NASA Langley Research Center (LaRC) POWER Project
funded through the NASA Earth Science/Applied Science Program. The app is an
independent prototype and does not imply NASA endorsement. Sources, available
versions, access dates and provenance limits are exposed with the evidence.

## What works and what is planned

Status on 15 November 2026:

| Area | Status |
| --- | --- |
| Manual settings, keyword question matching, NASA data, charts, rates and scoped significance | Works, with AI off |
| Examples, descriptive comparisons and the learning question | Works |
| Evidence, CSV and PNG downloads and pinned case links | Works |
| Draft 5 AI paths: planner, guided discovery with cited suggestions, cited explanations over the reviewed document corpus | Built; discovery and explanations on by default by the owner's decision, although neither evaluation gate was met (see [evaluation results](evaluation-results.md)) |
| Observations of intended users | None yet. The [user study kit](user-study-kit.md) is prepared. |
| Container image | Builds for linux/arm64 and linux/amd64; runtime checked on arm64 only ([verification](verification.md#draft-5-stage-7-container-and-browser-checks)) |
| Public deployment | None yet. The [deployment guide](deployment.md) exists. |
| Demo video or slides | Not made |

If an AI path is turned on for the submission, update this table and the
[AI disclosure](ai-disclosure.md) with the provider, the exact model and the evaluation
evidence. Screenshots of templated verdicts are not evidence of LLM or RAG usage.

## Demonstration script

Aim for approximately 27 seconds and verify the final recording stays below
30 seconds. Record the working prototype with AI off. Do not show discovery or
explanations unless an AI path is turned on for the submission.

| Time | Screen action |
| --- | --- |
| 0-5 seconds | Show the title and open the Svalbard example |
| 5-12 seconds | Show its actual location, dates and chart |
| 12-20 seconds | Show rate, conditional significance explanation and source/grid context |
| 20-27 seconds | Show a download and the interpretation question; finish on the project name |

Suggested narration:

> Is the Arctic warming? Trend Detective lets students investigate environmental
> questions using NASA POWER data. Choose a place and period, inspect the time
> series, and see the estimated change and conditional statistical evidence.
> Open the sources, download the values, and test your interpretation.

Rehearse against the recording. Use the actual displayed results if adding numbers;
never insert a desired rate or verdict. A presentation of up to seven slides is
the alternative format; no finished recording or presentation exists in this repo.

## Links and final actions

| Submission field | Current value/status |
| --- | --- |
| Challenge | [Be an Earth System Trend Detective!](https://www.spaceappschallenge.org/2026/challenges/earth-system-trend-detective/) |
| Source repository | [NASA-Space-Apps-Challenge-2026](https://github.com/ychengchong/NASA-Space-Apps-Challenge-2026) |
| Public demo video/presentation | Pending: record and upload, then supply a public link |
| Hosted app | Not deployed; optional if accessible source/supporting materials are provided. Steps are in the [deployment guide](deployment.md). |
| Final reviewed source revision | Pending: commit/publish the selected submission changes |
| Team page and contributor details | Team must complete in the official submission form |

- [ ] Review and finalize this text against what is actually demonstrated.
- [ ] Commit/publish the intended changes so judges can access the matching source.
- [ ] Observe at least five intended users with the [user study kit](user-study-kit.md), with their agreement, and record the results; or disclose that no study was run.
- [x] Decide whether any AI path is turned on: the owner turned discovery and explanations on by default on 15 November 2026, with the [evaluation results](evaluation-results.md) showing their gates were not met. Say so in the submission.
- [ ] Deploy the image from the submitted commit with a persistent `/app/state` volume, following the [deployment guide](deployment.md), or decide not to host the app.
- [ ] Run the deployment checks of the guide on the public HTTPS address and record them in [verification](verification.md).
- [ ] Record and upload the video, or prepare and publish up to seven slides.
- [ ] Open final project and demo links in a private browser without special access.
- [ ] Complete project details, NASA attribution and [AI disclosure](ai-disclosure.md).
- [ ] Recheck the official rules and submit through the team page before the supplied Singapore deadline: 15 November 2026, 11:59 PM SGT.
- [ ] Observe the successful submission confirmation; do not rely on saved drafts.

The organizer's supplied requirements are in [event information](event-information.md).
Official-repository clarifications cover [submission](https://github.com/nasa/spaceapps/discussions/1973)
and [hosting/demo links](https://github.com/nasa/spaceapps/discussions/1991).
The complete official submission-guide page could not be fetched in this audit;
the team should check the final form and current guide before submitting.

## Limitations and disclosure

No live-model accuracy, RAG capability, educational impact, browser/device testing,
public deployment or award outcome is established by automated unit tests. Legacy
seed records lack original response bytes and exact upstream release metadata;
their retained normalized evidence is labelled accordingly. Numerical claims remain
conditional on the documented method assumptions. See [verification](verification.md)
for the actual checks and [AI disclosure](ai-disclosure.md) for development assistance.

The team has not selected a project licence; no new licence is implied by this
submission text. Third-party data, fonts, map assets and dependencies retain their
own terms, with credits in the [README](../README.md#nasa-data-and-credits).
