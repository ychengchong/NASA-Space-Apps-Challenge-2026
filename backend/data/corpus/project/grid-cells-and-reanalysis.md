# Grid cells, reanalysis and data sources

This note was written by the Trend Detective project. It explains what the app's numbers describe. It is the project's own summary; for the data themselves, see the NASA POWER and GMAO documentation.

## A grid cell, not a point

The app reads NASA POWER monthly values for the grid cell that contains the chosen place. A result describes that grid cell, not the exact point or a city weather station. Two places in the same grid cell get the same values, so the difference between them is zero in every year. The place's name is only a label; it does not change the data.

## Reanalysis and model output

Two-metre air temperature (T2M) in POWER comes from MERRA-2 reanalysis. POWER supplies reanalysis values, which describe a grid cell; they are not exact local station measurements. Snow, sea ice, surface pressure, water vapour and the strongest wind in the app also come from MERRA-2. Haze is aerosol optical depth from CERES SYN1deg, available from 2001.

## Changes of data source

Some records change their source part way through. POWER's solar and cloud records come from one source up to 2000 and another from 2001, and NASA warns about source changes in radiation trend analysis. The app keeps solar and cloud records that cross the 2001 transition descriptive and shows a caution when the analysis years cross a source change.

## Yearly values

The app makes each yearly value from the twelve monthly values, weighting each month by its number of days and respecting leap years. A year with a missing month has no yearly value; a missing value is never replaced by zero. This day-weighted mean is the app's own named statistic. POWER describes its own annual values as a mean of the months, so the two need not be identical.
