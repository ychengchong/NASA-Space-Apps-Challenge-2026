# Full-length confirmation panel

Declared after the original n=20,30,45 panel passed, and before running this
additional panel. The procedure and development tables remain frozen with SHA-256
`c79203b7cc8c74a2199e1b505a756735c74929840427ec46a1d76013faf47fdf`.
No method/configuration tuning is permitted in this follow-up.

Confirm every supported integer length 20-45 in all six original null scenarios,
4,000 independent replicates per setting. Seeds are 141000 + 100*n + scenario
index, distinct from development and original confirmation. Use the same stationary
AR(1) generator, 250-step burn-in, Gaussian/centered exponential innovations, score,
tail table and plus-one rule. Report all 156 settings, exact one-sided 95% binomial
upper bounds and failures. The same <=0.07 guardrail applies to every setting.

Also report constants and one-decimal quantization as a ties stress check at
n=20,30,45, using the follow-up draws; these are additional checks, not a claim
that all discrete distributions or dependence structures are validated.

Run `python -m scripts.confirm_lengths` from backend. Do not suppress failures or
replace a failed setting with a different seed. A failure requires an explicit
scope/method review before claiming the expanded panel passed.
