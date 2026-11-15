# What each verdict means

This note was written by the Trend Detective project. It explains the verdicts the app gives. The verdicts and their wording are the project's own, not NASA's.

## The five verdict kinds

- no_data: there are no usable complete annual values for this place and period.
- too_few_years: fewer than ten complete annual values, so the app gives no rate. The verdict states the count and the policy threshold.
- inference_unavailable: a significance test is not justified or not available for this case. The app gives a descriptive rate where it can, and the reason the test was not run. Significance has not been assessed.
- significant: the validated test gives a p-value below 0.05. The evidence for a monotonic trend meets the stated 5% threshold.
- not_significant: the validated test gives a p-value of 0.05 or more. These data do not provide sufficient evidence for a monotonic trend under the method.

## When significance is not assessed

Many results are descriptive only. Significance is not assessed for any variable other than annual two-metre air temperature, for seasons, maps and area averages, for records of ten to nineteen years, for records with missing years or discontinuities, for periods that cross a change of data source, and when the calibration is missing. In these cases the verdict is inference_unavailable, the p-value is empty and the app says why. A descriptive rate is a summary of the data, not a test.

## How the verdict sentences are worded

A significant verdict says that the estimated change for the grid cell containing the place is a given rate per decade over the period, and that evidence for a monotonic trend meets the method's 5% threshold. A not significant verdict gives the estimated rate and says that the data do not provide sufficient evidence for a monotonic trend, adding that this does not establish that no change occurred. An unavailable verdict states its reason and that significance has not been assessed. The app writes these sentences from fixed templates; the numbers come from the analysis code.
