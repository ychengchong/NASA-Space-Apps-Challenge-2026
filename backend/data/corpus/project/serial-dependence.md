# Serial dependence and the retired lag-one correction

This note was written by the Trend Detective project. It explains how the project's method treats year-to-year dependence. It is the project's own description, not a NASA method.

## Why dependence matters

Neighbouring years of a record can be correlated with each other (lag-one autocorrelation). A trend test whose null distribution assumes independent years can then report evidence of a trend more often than its threshold suggests, which is why the project checked its procedure against correlated noise. Averaging months into years does not establish that the years are independent.

## The retired correction

An earlier draft of the project corrected for dependence with a multiplier based on the lag-one autocorrelation of the residuals, (1 + r1) / (1 - r1), applied to the Mann-Kendall test, the least squares slope and the interval. That multiplier has been retired as a universal correction. The earlier draft's reported false-positive rates and corrected fixture results had no reproducible evidence and are not accepted as validation. The retired multiplier must not be used to claim interval coverage.

## What the app does instead

The current procedure, mk_mc_envelope_v1, allows for dependence by simulation. Its null distributions were built from lag-one autoregressive series with correlation 0, 0.2 or 0.5, with Gaussian or skewed shocks, and the app takes the largest tail probability across these scenarios. This protects against false positives for the declared kinds of dependence. It does not establish validity for every form of dependence: all climate noise, intermediate correlation values, structural breaks and arbitrary dependence are outside what was checked. The price of this protection is lower power, so short records or weak trends can fail to reach the threshold even when change occurred.
