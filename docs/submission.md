# Trend Detective: submission materials

Status: prepared text for the current prototype. No public demo or hosted app URL
has been supplied. The Draft 5 LLM/RAG plan is not implemented. Complete the final
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
questions work without an AI key. Optional LLM planning can propose settings for
confirmation; cited RAG explanations are planned future work.

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

| Current prototype | Planned, not claimed in this submission |
| --- | --- |
| Manual settings and keyword question matching | Guided AI discovery with sourced suggestions |
| NASA measurements, charts, rates and scoped significance | Hosted document corpus and RAG explanations |
| Examples, descriptive comparisons, learning question | Live-model accuracy and target-user impact evidence |
| Evidence/CSV/PNG downloads and frozen case links | Verified public deployment and recorded demo |
| Optional provider planner integration, off by default | Enabling an exact provider/model after evaluation |

If runtime AI is later enabled, update this table and the disclosure with the
actual provider/model and evaluation evidence. Screenshots of templated verdicts
are not evidence of LLM or RAG usage.

## Demonstration script

Aim for approximately 27 seconds and verify the final recording stays below
30 seconds. Record the working prototype, not a mock-up of planned RAG features.

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
> Open the sources, download the values, and test your interpretation. AI planning
> is optional; cited RAG explanations are planned.

Rehearse against the recording. Use the actual displayed results if adding numbers;
never insert a desired rate or verdict. A presentation of up to seven slides is
the alternative format; no finished recording or presentation exists in this repo.

## Links and final actions

| Submission field | Current value/status |
| --- | --- |
| Challenge | [Be an Earth System Trend Detective!](https://www.spaceappschallenge.org/2026/challenges/earth-system-trend-detective/) |
| Source repository | [NASA-Space-Apps-Challenge-2026](https://github.com/ychengchong/NASA-Space-Apps-Challenge-2026) |
| Public demo video/presentation | Pending: record and upload, then supply a public link |
| Hosted app | Not supplied; optional if accessible source/supporting materials are provided |
| Final reviewed source revision | Pending: commit/publish the selected submission changes |
| Team page and contributor details | Team must complete in the official submission form |

- [ ] Review and finalize this text against what is actually demonstrated.
- [ ] Commit/publish the intended changes so judges can access the matching source.
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
