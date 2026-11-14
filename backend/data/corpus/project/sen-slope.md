# Sen's slope and the total change

This note was written by the Trend Detective project. It describes how the app estimates a rate of change. It is the project's own description, not a NASA method or a NASA statement.

## What Sen's slope is

Sen's slope is the app's estimate of how fast a yearly series changes. For every pair of years in the record, the app takes the difference between the two yearly values and divides it by the difference between the two years. Sen's slope is the median of all these pairwise rates. The app uses the real calendar years, so a missing year is not squeezed out and the remaining years are not treated as consecutive. The app reports the rate per decade: the slope per year multiplied by ten.

## The line on the chart and the total change

The line drawn on the chart has Sen's slope and passes through the median year and the median value of the series. The total fitted change is the slope per year multiplied by the span of the period in years, from the first year used to the last.

## Ordinary least squares is only a sensitivity check

The app also shows an ordinary least squares (OLS) slope. It is descriptive information about how sensitive the rate is to the choice of estimator. It is not a second significance test, and it does not vote on the verdict. Annual aggregation does not make the year-to-year errors independent.

## A zero rate

A Sen's slope of zero does not prove that nothing changed. A zero rate also does not override a valid trend test: when the median rate is zero but the trend test finds evidence below its threshold, the verdict stays significant without a rate direction, and the two quantities are explained separately. A rate that is very small but not zero is shown with more digits rather than rounded to zero.

## Intervals

The app does not report a confidence interval for the slope. Slope intervals stay empty until a procedure that allows for serial dependence is specified and its coverage is tested.
