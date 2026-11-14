# Inference study plan, version 1

Written before generating the tables or confirmation results for this branch.
The previous residual-lag correction failed the audit at AR(1) correlation 0.5.
We will not reuse it for MK, OLS or slope confidence intervals.

Candidate: a conservative Monte Carlo null-envelope test of the two-sided
Mann-Kendall score. This uses the ordinary tied MK score, but no independence
normal approximation. For each record length 20 through 45, generate 4,000
independent null records in each of six declared scenarios: stationary AR(1)
with phi 0, 0.2 or 0.5 and either standard Gaussian or centered standardized
exponential innovations. Initialize using a 250-step burn-in. For each absolute
score, use the largest exceedance count across scenarios, with the plus-one
Monte Carlo convention `(count + 1) / (4000 + 1)`. This is conservative across
the declared generators; it is not a distribution-free test for all climate data
or a guarantee for intermediate correlations or nonstationary processes.

Development seeds: 61000 + 100*n + scenario index. Confirmation seeds:
91000 + 100*n + scenario index. Freeze tables before confirmation; do not adjust
the procedure after seeing results. Confirm all six scenarios for n=20,30,45
with 4,000 independent records each. Acceptance: the one-sided 95% exact
binomial upper bound at nominal alpha 0.05 is <=0.07 in every setting.
Report all settings. Report detection rate for an added 0.1 standardized unit
per year, not as an acceptance criterion. Stress constants and rounded ties.

Application support additionally requires complete contiguous annual T2M,
20-45 years and no source transition. Other variables/seasons are descriptive.
Show assumptions and scope beside every assessed p-value. Do not use this
procedure to certify structural breaks, arbitrary serial dependence or causation.
Slope intervals and OLS p-values remain unavailable; OLS slope is descriptive.

The method is an explicitly reviewed alternative to the preferred Hamed-Rao
candidate in Draft 3, not a claim that Hamed-Rao was implemented or validated.
Reference: SciPy's Monte Carlo test documentation and its plus-one correction:
https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.monte_carlo_test.html

Run `python -m scripts.calibrate_inference` from backend. Tables, generator
configuration, seeds, confirmation counts, bounds and content hashes are retained.
