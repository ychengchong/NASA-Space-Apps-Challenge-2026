# User study kit

Status: **deferred by the team for this submission; no observations have been made.**
This retained kit supports future validation, not an additional organizer requirement.
No participant has been
recruited or observed, and no result of this study exists yet. Any count, rate or quote
reported from it must come from sheets filled in during real sessions.

This kit turns the student interpretation study of [evaluation](evaluation.md) into
materials an observer can use as they are. It serves the impact gate of spec section 12:
at least five intended users, anonymous and non-sensitive observation, success defined
before the first session, and every attempt reported.

## What you need

- The app, opened on its first screen, with the four saved examples ("Case 1" to "Case 4").
  The tasks use only these frozen examples, so every participant sees the same numbers.
- One printed or digital copy of the observation sheet below per participant.
- A clock or timer.
- This kit's success criteria, fixed before the first session. Do not change them during
  the study. If they turn out to be wrong, finish the study as written, then report the
  problem and the change you would make.

The tasks do not use the "Ask about this investigation" panel or the AI in the question bar.
If either is shown, ask participants not to type anything into them during the study, so no
participant text is sent to an outside service.

## Who takes part

Five or more intended users: students who could use the app in class, such as upper
secondary or first-year university students. Record no names, no contact details and no
school. Give each participant a code, P01, P02 and so on, in the order they take part.

If a participant is under 18, follow the school's rules for permission from a teacher or a
guardian before the session.

## Consent script

Read this aloud before anything else, and start only after a clear yes.

> Thank you for helping. We are testing a web app that shows climate data from NASA, not
> testing you. I will ask you to do five short tasks and to think aloud while you do them.
> I will take notes on what you do and how long it takes. I will not write down your name
> or anything that identifies you, and I will not record audio or video. You can skip any
> task, ask a question, or stop at any time, and that is fine. The whole session takes about
> twenty minutes. Is it all right if we start?

Note on the sheet only that consent was given ("yes"). If the answer is not a clear yes,
thank the participant and do not observe them.

## How to run a session

1. Open the app on its first screen.
2. Read each task aloud exactly as written below. Do not explain terms in the task.
3. Start the timer when you finish reading the task, and stop it when the participant says
   they are done or gives up.
4. Help only as the assistance codes allow, and record the highest code you used.
5. Write down the participant's answer in a few words of your own. Do not record private
   conversation.
6. Between tasks, go back to the first screen unless the next task says otherwise.

## The five tasks and their success criteria

A task succeeds when the participant meets every point of its criteria with assistance code
A0 or A1 and makes no critical interpretation error (codes below). Write down the outcome
of every attempt, including skipped and abandoned tasks.

### Task 1. Source, cell, dates and units

Read aloud: "Open the example about Svalbard. Tell me where the data comes from, which area
it describes, which years it covers, and in what units."

Success needs all four:

- Source: NASA POWER (MERRA-2).
- Area: the grid cell containing Longyearbyen, not a measurement in the town itself. Either
  the words "grid cell" or the cell's centre (78.0°N, 15.6°E) or its size (0.5° by 0.625°)
  counts.
- Dates: 1981 to 2025.
- Units: °C.

### Task 2. Rate and evidence

Stay on the Svalbard case. Read aloud: "How fast is it changing, and how sure can we be that
there is a trend? Are those the same question?"

Success needs all three:

- The rate: +0.79 °C per decade.
- The evidence: the trend meets the test's 5% threshold, conditional on its assumptions
  (or the p-value is below 0.001).
- The distinction: the rate says how fast; the evidence says whether a trend can be told
  apart from year-to-year variation. They are different questions.

### Task 3. Comparing two places

Read aloud: "Open the example about rain in Athens and Helsinki. Which years does the app
use to compare the two cities?"

Success needs:

- The same years for both cities: 45 common complete years, 1981 to 2025.

### Task 4. A case without a significance result

Read aloud: "Open the example about winters in Siberia. Why is there no significance result
for this case?"

Success needs both:

- A reason the app shows: a year is missing (the 1981 winter has no value, so 44 years from
  1982 to 2025 are used), or seasonal significance has not been validated. Either counts.
- "Significance unavailable" is not the same as "not significant": no justified test was
  run.

### Task 5. The evidence lesson

Open any example. Read aloud: "Open the 'Learn' tab and do the evidence lesson. Then tell
me: does 'not significant' prove that nothing changed? And does 'significant' tell us what
caused the change?"

Success needs all three:

- The lesson is completed: the participant chooses an answer and reads the guidance.
- Not significant does not prove no change; the record may be too short or too noisy.
- Significance does not establish a cause.

## Assistance codes

Record the highest level used in each task.

| Code | Meaning |
| --- | --- |
| A0 | No help |
| A1 | Neutral prompt only: the task read again, or "What would you try next?" |
| A2 | Pointed to a place: "Look in the 'Evidence' tab" |
| A3 | Explained a term or a concept |
| A4 | The observer did the step, or the participant gave up |

A2 or higher means the task did not succeed, even if the final answer was right. Report it
as "completed with help".

## Interpretation error codes

Record every error you hear, even if the participant corrects it later. Mark an error as
critical with an asterisk: E1, E2, E3 and E5 are critical.

| Code | Error |
| --- | --- |
| E1 | Treats the rate and the evidence for a trend as the same thing |
| E2 | Reads "not significant" as proof of no change |
| E3 | Reads "significant" as proof of a cause |
| E4 | Reads the grid cell's values as a station measurement in the town |
| E5 | Reads "significance unavailable" as "not significant" |
| E6 | Reads the p-value as the probability that the claim is true |
| E7 | Reads the record years or ten-year means as a test |
| E8 | Other (describe in a few words) |

## Observation sheet

One row per task per participant. No names, no direct quotes of private talk.

| Participant | Consent | Task | Start | Time (s) | Outcome | Assistance | Errors | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P01 | yes | 1 | | | | | | |
| P01 | | 2 | | | | | | |
| P01 | | 3 | | | | | | |
| P01 | | 4 | | | | | | |
| P01 | | 5 | | | | | | |

Outcome is one of: success, completed with help, not completed, skipped. Notes are a few
words on what the participant did, such as "looked for the units in the chart first".

Also note once per session: the device (phone, tablet or computer), whether the
participant has used the app before, and anything that went wrong with the app.

## Optional baseline comparison

Spec section 12 asks to compare against a simple chart where feasible. If there is time,
give each participant the same Svalbard data as a plain chart before or after the app: the
yearly values downloaded from the "Evidence" tab ("yearly values", CSV) and drawn as a line
chart in a spreadsheet, without the verdict or any text from the app. Ask tasks 1 and 2 on
it. Alternate the order: odd-numbered participants start with the plain chart, even-numbered
ones with the app. Record these attempts on the same sheet with the task written as "1-B"
or "2-B". If the baseline is not run, say so in the report.

## How to report

Report every attempt, by task:

- The number of participants observed, and how many were invited but not observed.
- For each task: successes, completed with help, not completed and skipped, out of the
  number who attempted it, such as "4 of 5". With five participants a percentage says
  little; if you add one, give the Wilson 95% interval with it.
- Every interpretation error, by code and task, with the count.
- The median time per task, with the shortest and longest.
- Every failure in a sentence: what happened, and what in the app may have caused it.
- Every change made to the app or to this kit because of the study, and when.
- The limits: a small, non-random sample; observers who know the app; formative evidence,
  not proof of a learning effect.

If fewer than five intended users are observed, report the study as incomplete and name
the gap. Never fill a sheet or a count that was not observed.
