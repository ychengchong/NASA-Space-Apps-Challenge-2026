# Guided walkthroughs

Status: prepared for teachers from the frozen example cases. Nobody has tried these
walkthroughs with students yet, and no learning outcome is claimed.

These are the two guided walkthroughs of spec section 3 and stage 5 of section 12. Each one
uses a saved example that opens from the first screen and is pinned to frozen evidence, so
every number below is the same on every visit and needs no live NASA call.

Every sentence in quotation marks, and every number, was read from the app's own output for
the example: the `/api/case` response for the example's query, served from the committed
`backend/data/cache.sqlite` with analysis version `td-2026-11-v1`. Nothing was rounded or
reworded by hand. The "Ask about this investigation" panel is described, not quoted, because
its answers are written by AI and change from question to question.

## Before you start

- Open the app's first screen. The four saved examples are listed as "Case 1" to "Case 4",
  and each has a pin on the globe.
- The values describe a grid cell of 0.5° by 0.625° that contains the town, not a weather
  station in the town. Say this early, and say it again at the evidence step.
- The rate, the evidence for a trend and the cause are three different questions. The app
  answers the first, answers the second only where its test is validated, and never answers
  the third.
- The "Ask about this investigation" panel appears only when the server has its AI
  explanations switched on. They are off: the explanations did not pass their held-out
  evaluation gate (see [evaluation results](evaluation-results.md)), so the panel is not
  shown. Skip that step and use the "Evidence" and "Learn" tabs, which explain the method
  and its limits without AI. The panel steps below apply only once that gate has passed.

## Walkthrough A: Is Svalbard getting warmer?

The example is "Case 1", titled "Is Svalbard getting warmer?". It tests yearly air
temperature in Longyearbyen, a town in the high Arctic, from 1981 to 2025. In the catalogue
(`backend/data/catalogue.json`) the variable "Air temperature" is NASA POWER's parameter
T2M; the screen calls it "Air temperature".

### Step 1. The question

Read the example's title and teaser aloud before opening it. The teaser says that this case
"shows what a clear, significant trend looks like".

Ask the students:

- What would you expect to see in 45 years of Arctic air temperature?
- What would count as evidence that it is getting warmer, rather than a few warm years?

### Step 2. The settings

Open "Case 1". The settings are folded behind "Change this case". Open them and read each
field:

- Variable: "Air temperature", defined as "How warm the air is two metres above the ground,
  averaged over the month." Units: °C.
- Place: Longyearbyen, at 78.22, 15.65.
- Period: 1981 to 2025.
- Season: "Every month", so each year's value is the average of all twelve months.

The "Steps taken" list (in the "Evidence" tab) adds that the grid point used is 78.0°N,
15.6°E, in a cell of 0.5° by 0.625°, and that each year's twelve months are
calendar-day-weighted into one value. A year with a missing month has no value.

Ask the students:

- Why does the app say "the grid cell containing Longyearbyen" and not "Longyearbyen"?
- What would change if we chose only June to August?

### Step 3. The verdict

The verdict card is the first sheet. Its stamp reads "↑ Rising" over "Significant", the
large figure is "+0.79 °C per decade", and the sentence is:

> "The estimated change in Air temperature for the grid cell containing Longyearbyen is +0.79
> °C per decade from 1981 to 2025. Evidence for a monotonic trend meets the stated test's 5%
> threshold, conditional on its assumptions."

Open "What does “significant” mean?" beside the stamp and read the definition together.

Ask the students:

- Which part of the sentence is the rate, and which part is the evidence for a trend?
- What does "conditional on its assumptions" warn us about?
- Does "significant" tell us why the air is warming?

### Step 4. The chart

The "Answer" tab opens first, with the chart "Yearly values and trend" right under the
verdict. Its legend names "Yearly values", "Record years" and "Trend line". There is one
point for every year from 1981 to 2025; no year is missing. "Read the chart in words" under
the plot describes the trend line's ends and its rate in words.

Ask the students:

- Do the points sit close to the line, or scatter widely around it?
- Find two years next to each other where the temperature fell. Does that contradict a
  rising trend?

### Step 5. The record years

The "Record years" sheet follows the chart. The app writes:

- "Highest yearly values used (°C): -3.28 in 2016, -4.85 in 2012 and -4.91 in 2023."
- "Lowest yearly values used (°C): -10.22 in 1988, -9.11 in 1982 and -8.93 in 1983."
- "The mean of the last ten years used, 2016 to 2025, was 2.57 °C higher than the mean of
  the first ten, 1981 to 1990."

Its note says: "These facts describe the yearly values used. They are not tests, and their
significance was not assessed."

Ask the students:

- All three warmest years are after 2010 and all three coldest are in the 1980s. Is that a
  test of the trend? Why does the app say it is not?
- The ten-year means differ by 2.57 °C and the trend line's total change is +3.48 °C (see
  step 6). Why are these two numbers different?

### Step 6. The "Evidence" tab

Open the "Evidence" tab, then the folded "Evidence" panel. The "Numbers" table holds:

| Measure | Longyearbyen |
| --- | --- |
| Rate of change (Sen's slope) | +0.79 °C per decade |
| 95% confidence interval of the rate | Unavailable: serial-dependence coverage has not been validated |
| Total change over the years used | +3.48 °C from 1981 to 2025 |
| Mann-Kendall p-value (stated method) | < 0.001 |
| Year-to-year memory (lag-1 autocorrelation, r1) | 0.19 |
| Least-squares slope (cross-check) | +0.77 °C per decade |
| Least-squares significance | Not assessed; OLS slope is descriptive |
| Number of years used | 45 |
| First and last year used | 1981 to 2025 |
| Grid cell | centred on 78.0°N, 15.6°E, 0.5° by 0.625° |

Under "Cautions" the panel says "No caution applies." Under "Data" it names NASA POWER
(MERRA-2), API version v2.10.0, accessed 2026-11-13, and says that the original response
bytes were not retained for this legacy example while the normalized evidence is frozen. It
also says "This case is pinned to immutable evidence." The method line names
`mk_mc_envelope_v1` and its assumptions, which end: "A significant result does not
establish causation."

Ask the students:

- Two methods estimate the rate: Sen's slope (+0.79) and least squares (+0.77). Why is it
  reassuring that they are close?
- Why is there no confidence interval for the rate, even though the trend is significant?
- Where would you find the NASA source if you wanted to check the data yourself?

### Step 7. The "Ask about this investigation" panel

This step applies only once explanations have passed their evaluation gate; today the
panel is disabled because they did not (see [evaluation results](evaluation-results.md)).
When it is shown, this panel follows the case file; on a wide screen it heads the
right-hand column, above the globe. Its line says
"Questions are sent to OpenAI. Answers are written by AI and checked against this result."
It offers five prompts as links: "Explain this simply", "What does this dataset actually
measure?", "What are the limitations here?", "What can't we conclude?" and "What could I
investigate next?".

Have a student choose "What can't we conclude?". While the AI writes, the result stays on
screen; the panel says the result does not wait for it. The answer comes under the label
"Written by AI". Any number in it is listed separately under "From this result, not written
by AI:" and is read from the result on screen, not from the AI. Each source is a link with
its publisher and title, and "Show the cited passage" opens the passage the AI was given.
If no answer passes the checks, the panel says "No checked answer." with a reason, and points
to the "Evidence" and "Learn" tabs.

Ask the students:

- Open one cited passage. Does it actually say what the AI's sentence says?
- Which parts of the answer were written by AI, and which came from the result?
- If the AI and the verdict card seemed to disagree, which one would you trust, and why?

### Step 8. The limits

The "Evidence" panel ends with "What the data can and cannot tell". Read these three
together:

- "MERRA-2 is a reanalysis: a weather model steered by observations. Changes in the
  observing system over the decades can create artificial shifts, so a trend is evidence,
  not proof."
- "Significance is not cause. The test says a pattern this strong would be unusual if
  nothing were changing. It does not say why."
- "The method fits a straight line. A curve or a sudden shift can be missed or
  misdescribed."

Then open the "Learn" tab and do "Try the evidence lesson" together: choose an answer before
reading the guidance.

Ask the students:

- Write one sentence about Longyearbyen that the evidence supports, and one that it does
  not.
- What other evidence would you need to say why the Arctic is warming?

## Walkthrough B: Rain in Athens and Helsinki

The example is "Case 3", titled "Rain in Athens and Helsinki". It compares yearly
precipitation in two cities from 1981 to 2025. In the catalogue the variable
"Precipitation" is NASA POWER's parameter PRECTOTCORR.

### Step 1. The question and why these two cities

Read the teaser before opening the case. It says climate studies often expect the
Mediterranean to get drier and northern Europe to get wetter, and that the two cities were
chosen for that reason before looking at any result, and kept whatever the data showed.

Ask the students:

- What do you expect each city's rate to be, rising or falling?
- Why does it matter that the cities were chosen before anyone looked at the result?

### Step 2. The settings

Open "Change this case" and read the fields:

- Variable: "Precipitation", defined as "How much rain and snow falls, given as the average
  amount per day over the month." Units: mm/day.
- Places: Athens (37.98, 23.73) and Helsinki (60.17, 24.94). The "Steps taken" give the grid
  points 38.0°N, 23.8°E and 60.0°N, 25.0°E, each in a cell of 0.5° by 0.625°.
- Period: 1981 to 2025. Season: "Every month".

Ask the students:

- The unit is millimetres per day, averaged over the year. How would you turn that into a
  yearly total, roughly?

### Step 3. The verdict and why precipitation stays descriptive

The verdict card gives the comparison's summary first:

> "Descriptive comparison on 45 identical complete years (1981-2025): Athens: +0.06 mm/day per
> decade; Helsinki: -0.04 mm/day per decade. This is not a statistical test of differences
> between places."

Each place's stamp reads "Significance unavailable", with no direction and no large figure.
Athens's sentence is:

> "The estimated change in precipitation for the grid cell containing Athens is +0.06 mm/day
> per decade over 1981-2025. Inference is validated only for individual annual T2M series;
> this case is descriptive. Significance has not been assessed."

Helsinki's sentence has the same form, with "-0.04 mm/day per decade". Each place carries the
caution "Rainfall trends from this model are less reliable than temperature trends."

Why precipitation stays descriptive: the app runs a significance test only where the test
has been checked to give honest answers, and that check (spec section 7) covered individual
annual air temperature series only. For precipitation the app still estimates the rate, but
it reports no p-value and no "significant" or "not significant". Unavailable significance is
not the same as "not significant": no justified test was run at all.

Ask the students:

- The rates came out the other way round from the expectation in the teaser. Does this case
  show that the expectation is wrong? What would you need to say that?
- Why does the app refuse to call either rate significant, when it did for Svalbard?
- What is the difference between "not significant" and "significance unavailable"?

### Step 4. The chart

The chart "Yearly values and trend" draws both places, each with its own colour and marker
shape. Under the plot: "Dashed lines are trend lines; rings mark record years." Both places
have a value in all 45 years.

Ask the students:

- Which city varies more from year to year? Does a trend line that is nearly flat mean the
  rain is steady?

### Step 5. The record years

The "Record years" sheet has one table per place. The app writes, for Athens:

- "Highest yearly values used (mm/day): 2.21 in 2020, 1.83 in 2019 and 1.75 in 2021."
- "Lowest yearly values used (mm/day): 0.61 in 1989, 0.72 in 2000 and 0.79 in 1990."
- "The mean of the last ten years used, 2016 to 2025, was 0.32 mm/day higher than the mean
  of the first ten, 1981 to 1990."

And for Helsinki:

- "Highest yearly values used (mm/day): 2.97 in 1981, 2.64 in 2008 and 2.63 in 2012."
- "Lowest yearly values used (mm/day): 1.28 in 2002, 1.55 in 2013 and 1.61 in 2014."
- "The mean of the last ten years used, 2016 to 2025, was 0.14 mm/day lower than the mean
  of the first ten, 1981 to 1990."

Ask the students:

- Athens's three wettest years are 2019, 2020 and 2021. Is three wet years in a row a trend?

### Step 6. The gap chart

Open the "Explore" tab. "The gap: Athens minus Helsinki" draws each year's difference,
with its trend line and a zero line. The note under it says each point is Athens's yearly
value minus Helsinki's, in a year both places have, and that above zero Athens was higher.
In this case only one point, 2002, lies above zero. The app's sentence, which also follows
the summary on the verdict card, is:

> "The difference between Athens and Helsinki, Athens minus Helsinki, changed by about +0.12
> mm/day per decade from 1981 to 2025, over 45 common years. A positive rate means Athens
> rose compared with Helsinki. The difference was not tested; this is a description."

Ask the students:

- Almost every point is below zero. What does that tell you about the two cities?
- The gap's rate is positive. Does that mean Athens is getting wetter than Helsinki? Read
  the sentence again: what does a positive rate mean here?
- The gap's rate (+0.12) is not simply Athens's rate minus Helsinki's rate (+0.06 minus
  -0.04). The app computes it from the yearly differences themselves. Why might the two
  differ?

### Step 7. The "Evidence" tab

The "Numbers" table has a column per place. For both places the "Mann-Kendall p-value
(stated method)" row reads "Not assessed", and the 95% confidence interval row reads
"Unavailable: serial-dependence coverage has not been validated". The other rows:

| Measure | Athens | Helsinki |
| --- | --- | --- |
| Rate of change (Sen's slope) | +0.06 mm/day per decade | -0.04 mm/day per decade |
| Total change over the years used | +0.25 mm/day from 1981 to 2025 | -0.18 mm/day from 1981 to 2025 |
| Year-to-year memory (lag-1 autocorrelation, r1) | 0.22 | -0.06 |
| Least-squares slope (cross-check) | +0.08 mm/day per decade | -0.04 mm/day per decade |
| Number of years used | 45 | 45 |

The panel lists the common complete years the comparison uses, 1981 to 2025, and the
method line for each place says "Significance unavailable" with the reason above.

Ask the students:

- Why must a comparison use the same years for both places?

### Step 8. The "Ask about this investigation" panel and the limits

This step, too, applies only once explanations have passed their evaluation gate; today the
panel is disabled. If the panel is shown, choose "What are the limitations here?" and read the answer as in
walkthrough A: AI text under "Written by AI", the result's own values under "From this
result, not written by AI:", and the cited passages behind "Show the cited passage". If a
student asks for a new calculation, such as another city, the panel proposes settings
instead; nothing runs until "Run this case".

Then read "What the data can and cannot tell" in the "Evidence" panel, including "Values
describe a grid cell, not a weather station."

Ask the students:

- Write one sentence about rain in Athens and Helsinki that this case supports, and one it
  does not.
- What would a scientist need, beyond this case, to test the teaser's expectation?

## Checked against

The IDs below are the original recorded run. The Windows submission-day check confirmed
the same evidence hashes and identical local pinned replay, but produced different
investigation IDs; see [verification](verification.md#submission-day-fixes-and-offline-checks).
Copy the current app's pinned link for the demo instead of relying on an ID from this table.

| Walkthrough | Example query | Investigation ID | Evidence IDs |
| --- | --- | --- | --- |
| A | `v=air_temp&p=78.22,15.65&label=Longyearbyen&from=1981&to=2025&s=annual` | `99cc2d40ab9465a4276527e85687ccba6e8642442678b77c6f6c9ff3c2123f1a` | `b5789d547f55e8374dff65e6010f62e4466b5f9035ebd71278f4740432c4ce08` |
| B | `v=precipitation&p=37.98,23.73&p=60.17,24.94&label=Athens&label=Helsinki&from=1981&to=2025&s=annual` | `fc16076c8bde012b4c23843f141dfd8279f53527ec5ad1831a0abe6119ebf7fa` | `3f45c6d88b113f151442240bad2e50d2057a868a7f016cd0ae02cc5ec000b6d7`, `64c1f37418e9dfe44bbc5cd4851c92bea39fe8561a1215e2bdd98aff7afb337f` |

If an analysis version or the frozen evidence changes, read the example's `/api/case`
output again and update every quotation and number here.
