/** Fixed explanatory texts shown on screen, word for word from the spec sections named. */

// Spec 3, "Wording and accessibility": the caution that sits on the period control.
export const PERIOD_CAUTION = "Changing the period until a trend turns significant is not evidence.";

// Spec 3, "States the screen must handle": a trend that is not significant carries this note.
export const MORE_YEARS_NOTE = "More observations may improve precision; they do not guarantee significance.";

// Spec 6, "Citing the data": POWER's own acknowledgement, from its referencing page.
export const POWER_ACKNOWLEDGEMENT =
  "These data were obtained from the NASA Langley Research Center (LaRC) POWER Project funded " +
  "through the NASA Earth Science/Applied Science Program.";

export interface Definition {
  term: string;
  definition: string;
}

// Spec 7, "Definitions shown to users". This one also sits next to each verdict (spec 3).
export const SIGNIFICANCE_DEFINITION: Definition = {
  term: "Statistically significant",
  definition:
    "The result meets the stated test threshold of 5% under its null model and assumptions. It does not measure the probability that the claim is true.",
};

// Spec 7, "Definitions shown to users".
export const DEFINITIONS: readonly Definition[] = [
  { term: "Trend", definition: "A steady rise or fall over many years." },
  { term: "Rate of change", definition: "How fast the value is changing, given per decade." },
  SIGNIFICANCE_DEFINITION,
  {
    term: "p-value",
    definition: "The chance of seeing a pattern at least this strong if nothing were really changing.",
  },
  {
    term: "95% confidence interval",
    definition:
      "The range of rates that fit the data well. It is built so that it captures the true rate 95 times out of 100.",
  },
];

// Spec 6, "Caveats shown to users"; the spec's caution code is written out in words.
export const DATA_CAVEATS: readonly string[] = [
  "MERRA-2 is a reanalysis: a weather model steered by observations. Changes in the observing " +
    "system over the decades can create artificial shifts, so a trend is evidence, not proof.",
  "Values describe a grid cell, not a weather station.",
  "Sunlight and cloud values come from one satellite product up to 2000 and another from 2001. " +
    "Significance is unavailable across that join without a validated discontinuity-aware analysis.",
];

// Spec 7, "What the statistics do not claim".
export const STATISTICS_LIMITS: readonly string[] = [
  "Significance is not cause. The test says a pattern this strong would be unusual if nothing " +
    "were changing. It does not say why.",
  "“Not significant” is not proof that nothing is changing. It can also mean the record is " +
    "too short or too noisy to tell.",
  "The method fits a straight line. A curve or a sudden shift can be missed or misdescribed.",
];
