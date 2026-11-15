# The Mann-Kendall trend test in Trend Detective

This note was written by the Trend Detective project. It describes the project's own significance procedure. The procedure was designed and checked by the project; it is not a NASA method and NASA has not reviewed it.

## What the Mann-Kendall test asks

The Mann-Kendall (MK) test asks whether a yearly series tends to rise or to fall over time, without assuming the change is a straight line. It compares every pair of years: a later value higher than an earlier one counts plus one, a lower one minus one, and a tie zero. The sum of these signs is the MK score. A score far from zero, in either direction, is evidence for a monotonic trend. The app uses the two-sided test, so a rise and a fall are treated alike.

## The procedure the app uses

The selected procedure is called mk_mc_envelope_v1. It evaluates the ordinary two-sided MK score against frozen Monte Carlo null distributions instead of a formula. For each record length from 20 to 45 years, simulated series without a trend were generated under six declared scenarios: a lag-one autoregressive process with correlation 0, 0.2 or 0.5, each with Gaussian or with skewed (centred, standardised exponential) random shocks. The p-value is the largest tail probability across the six scenarios, so it is conservative for these declared generators. This procedure is not the Hamed-Rao method and must not be described as that published method.

## When the test is run

Formal inference runs only for an individual, complete annual record of two-metre air temperature (T2M) with 20 to 45 contiguous complete years and no change of data source within the period. Every other variable, every season, regional maps and area averages are descriptive: they report a rate, but significance is not assessed. Ten to nineteen complete years give a descriptive rate only, and fewer than ten give too few years for a rate. These are conservative policies of this application, not universal scientific minimums. When the test cannot be justified, the p-value is left empty; an unrun test never reports a p-value of one.

## What the p-value means

A p-value is the probability of a test statistic at least as extreme as the one observed, computed under the null model and its assumptions. It is not the probability that a trend is real or that a claim is true. The app uses a 5% threshold.

## What the checks show, and what they do not

Before release the procedure was checked in predeclared simulation studies at a nominal 5% threshold, with an engineering guardrail on the false-positive rate in every declared setting; every declared setting met it. This is evidence only for the declared simulation family. It does not establish validity for all climate noise, for intermediate correlation values, for structural breaks or for arbitrary dependence, and it is not exact 5% calibration. Being conservative also costs power, especially for short records: a real trend can go undetected. Real series can violate the assumptions, and a significant result does not certify them.
