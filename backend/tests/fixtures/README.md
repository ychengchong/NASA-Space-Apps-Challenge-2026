# Saved NASA POWER responses

Real responses from the NASA POWER monthly API (API version `v2.10.0`), fetched on 13 November 2026 with plain GET requests. The tests serve them through `httpx.MockTransport`, so no test touches the network. Data: NASA Langley Research Center (LaRC) POWER Project, <https://power.larc.nasa.gov/>.

Only `power_point_gap.json` is edited, as described below. The other two files are byte-for-byte what POWER sent.

## `power_point_full.json`

The full record of all twelve catalogue codes at the grid point that contains Helsinki.

```text
GET https://power.larc.nasa.gov/api/temporal/monthly/point
    ?parameters=T2M,T2M_MAX,T2M_MIN,TS,PRECTOTCORR,RH2M,QV2M,WS10M,GWETTOP,GWETROOT,ALLSKY_SFC_SW_DWN,CLOUD_AMT
    &community=AG&latitude=60.0&longitude=25.0&start=1981&end=2025&format=JSON
```

- 45 years, 1981 to 2025, with 13 keys a year per code: `YYYY01` to `YYYY12`, plus `YYYY13`, POWER's own annual value.
- `ALLSKY_SFC_SW_DWN` and `CLOUD_AMT` are `-999.0` for every month of 1981 to 1983. No other value is missing.
- `header.fill_value` is `-999.0`, `header.api.version` is `"v2.10.0"`, and `header.sources` is `["SYN1DEG", "SRB", "MERRA2", "POWER"]`.
- `geometry.coordinates` is `[25.0, 60.0, 9.17]`: longitude, latitude, elevation.
- The call took about 2 seconds.

## `power_point_gap.json`

T2M at the same grid point for 2000 to 2005, with one month replaced by the fill value. It gives the known yearly and December-to-February means of spec section 12.

```text
GET https://power.larc.nasa.gov/api/temporal/monthly/point
    ?parameters=T2M&community=AG&latitude=60.0&longitude=25.0&start=2000&end=2005&format=JSON
```

**Edit:** `"200212": -7.22` was replaced by `"200212": -999.0`. Nothing else was changed. In particular, `"200213": 5.65`, POWER's annual value for 2002, still reflects the original December; the app ignores month 13 keys.

The edit puts the missing month in December, so it removes the 2002 yearly value and the 2003 December-to-February value, but not the 2002 one.

Expected yearly means, in °C (a year with any missing month has no value):

| Year | Sum of 12 months | Mean |
| --- | --- | --- |
| 2000 | 77.19 | 6.4325 |
| 2001 | 65.49 | 5.4575 |
| 2002 | December is missing | no value |
| 2003 | 56.46 | 4.705 |
| 2004 | 66.02 | 5.50166… (66.02 / 12) |
| 2005 | 79.81 | 6.65083… (79.81 / 12) |

Expected December-to-February means, in °C (December counts toward the following year):

| Season year | Months used | Mean |
| --- | --- | --- |
| 2000 | December 1999 is not in the response | no value |
| 2001 | 1.08, −1.97, −6.23 | −2.37333… (−7.12 / 3) |
| 2002 | −5.50, −3.06, −1.27 | −3.27666… (−9.83 / 3) |
| 2003 | December 2002 is missing | no value |
| 2004 | −0.05, −5.88, −5.44 | −3.79 |
| 2005 | 0.89, 0.44, −3.69 | −0.78666… (−2.36 / 3) |

## `power_regional.json`

One regional response for T2M over a 10° by 10° box.

```text
GET https://power.larc.nasa.gov/api/temporal/monthly/regional
    ?parameters=T2M&community=AG&latitude-min=55&latitude-max=65&longitude-min=20&longitude-max=30
    &start=2020&end=2021&format=JSON
```

Shape of the response:

```text
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": { "type": "Point", "coordinates": [lon, lat, elevation] },
      "properties": { "parameter": { "T2M": { "202001": 4.61, ..., "202013": 10.17, ... } } }
    },
    ...
  ],
  "header": { "api": { "version": "v2.10.0" }, "sources": ["MERRA2"], "fill_value": -999.0, ... },
  "messages": [],
  "parameters": { "T2M": { "units": "C", "longname": "Temperature at 2 Meters" } },
  "times": { ... }
}
```

- 357 features: 21 latitudes from 55.0 to 65.0 in steps of 0.5, times 17 longitudes from 20.0 to 30.0 in steps of 0.625. Both edges of the box are included.
- Each feature holds the same `YYYYMM` keys as a point response, month 13 included. No value is missing.
- The cell at latitude 60.0, longitude 25.0 matches `power_point_full.json` exactly for 2020 and 2021.
- The app itself always asks for the full record from 1981. The tests serve this short response to that request, which the parser accepts.
- The same box with the full record, 1981 to 2025, took about 2.5 seconds on 13 November 2026.
