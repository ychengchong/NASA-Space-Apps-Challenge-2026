# What the result fields mean

This note was written by the Trend Detective project. It explains, in plain words, each field of a result that an answer can point at, such as the rate of change (sen_slope), the Mann-Kendall p-value (mk_p) or the total change (total_change). The app shows every value itself, from the analysed record; an answer only names the field. It is the project's own description, not a NASA method or a NASA statement.

## The rate of change (sen_slope)

The rate of change, labelled "Rate of change (Sen's slope)", is the field sen_slope. It says how fast the yearly values changed over the years used. For every pair of years the app takes the difference between the two yearly values divided by the difference between the two years, and the rate is the median of these pairwise rates. The app uses the real calendar years, so a missing year is not squeezed out. The rate is shown per decade, in the units of the rate: the slope per year multiplied by ten.

The rate is a description of the record, not by itself evidence of a trend. A rate of zero does not prove that nothing changed. A place has a rate only when it has at least ten complete yearly values.

## The interval of the rate (sen_ci95)

The field sen_ci95, labelled "95% confidence interval of the rate", is empty in every result: the app does not report an interval for the rate. It stays unavailable until a procedure that allows for serial dependence between years is specified and its coverage is tested. Where a confidence interval is reported, it describes how often the procedure would cover the true value if it were repeated; it is not a probability that a fixed true value lies inside it.

## The p-value of the trend test (mk_p)

The field mk_p, labelled "Mann-Kendall p-value", is the p-value of the trend test. It is the probability of a test statistic at least as extreme as the one observed if the record had no monotonic trend, under the test's assumptions. It is not the probability that a trend is real, and it does not measure how large or important a change is, or what caused it.

The app runs the test only for complete annual two-metre air temperature records of twenty to forty-five contiguous years with no change of source. For every other variable, season or record the p-value is empty and shown as "Not assessed"; it is never set to one. A p-value below the five percent threshold gives the verdict significant; a p-value at or above it gives not significant.

## The total change (total_change)

The field total_change, labelled "Total change over the years used", is the change along the drawn trend line from the first year used to the last. It is the slope per year multiplied by the number of years between the first and the last year used, in the units of the rate. It is not the difference between the first and the last yearly value. The drawn line has the rate's slope and passes through the median year and the median value of the record.

## The years used (n, first_year, last_year)

The field n, labelled "Number of years used", counts the complete yearly values the analysis used. The fields first_year and last_year, labelled "First year used" and "Last year used", are the first and last of those years. They can differ from the period asked for: a year that is missing any of the months asked for is not complete and is left out, and a record can start later than the period. Missing years are never closed up. In a comparison of places, only the years every place has in common are used, and the excluded years are reported.

## The verdict (verdict.kind and verdict.sentence)

The field verdict.kind, labelled "Verdict", is one of five kinds. Significant: the evidence for a monotonic trend meets the test's threshold. Not significant: these data do not provide sufficient evidence for a monotonic trend, which does not establish that no change occurred. Too few years: fewer than ten complete yearly values. No data: no usable yearly values for this place and period. Inference unavailable: the trend test does not apply to this case, so significance has not been assessed, and the rate is descriptive where there is one.

The field verdict.sentence, labelled "Verdict sentence", is the app's fixed sentence for that verdict, in words chosen by the app, not by an AI. For a verdict from the trend test it states the estimated change per decade over the years used and what the evidence does or does not show; for a verdict without the test it gives the reason and says that significance has not been assessed.

## The place and the variable (place.name, variable.name, variable.units, variable.rate_units)

The field place.name, labelled "Place", is the name of a place in the investigation. The values describe the grid cell containing that place, not a single point or station. The field variable.name, labelled "Variable", is the quantity analysed. The field variable.units, labelled "Units", gives the units of the yearly values, and variable.rate_units, labelled "Units of the rate", gives the units of the rate and of the total change. The two can differ, and a variable whose values or rate have no units shows "None".

## The period and the months asked for (requested.from, requested.to, requested.season)

The fields requested.from and requested.to, labelled "First year asked for" and "Last year asked for", are the period the investigation asked for, before incomplete years were left out. The field requested.season, labelled "Months", says which months each yearly value averages: all months, or one season named by its months, December to February, March to May, June to August or September to November. For December to February, December counts toward the following year, so the winter that starts in one December belongs to the next year.
