# Variables in Trend Detective

This note was written by the Trend Detective project from the app's variable catalogue. It lists every variable the app can test for a trend: the catalogue ID, the name shown in the app, the NASA POWER parameter code the app requests, the app's plain-language definition, the units, the grid and the cautions the app attaches to the variable. The definitions and cautions are the project's own wording, not NASA definitions or NASA statements.

## Air temperature (T2M)

Air temperature (T2M): How warm the air is two metres above the ground, averaged over the month.

- Catalogue ID: air_temp
- NASA POWER parameter code: T2M
- Units: °C
- Rate of change shown in: °C per decade
- Data source: NASA POWER (MERRA-2)
- Record starts in: 1981
- Grid: cells of 0.5° latitude by 0.625° longitude; each cell is centred on a grid point, a multiple of the cell size, with its edges halfway between grid points. A place takes the nearest grid point.

## Maximum temperature (T2M_MAX)

Maximum temperature (T2M_MAX): The highest hourly air temperature two metres above the ground during the month.

- Catalogue ID: max_temp
- NASA POWER parameter code: T2M_MAX
- Units: °C
- Rate of change shown in: °C per decade
- Data source: NASA POWER (MERRA-2)
- Record starts in: 1981
- Grid: cells of 0.5° latitude by 0.625° longitude; each cell is centred on a grid point, a multiple of the cell size, with its edges halfway between grid points. A place takes the nearest grid point.

## Minimum temperature (T2M_MIN)

Minimum temperature (T2M_MIN): The lowest hourly air temperature two metres above the ground during the month.

- Catalogue ID: min_temp
- NASA POWER parameter code: T2M_MIN
- Units: °C
- Rate of change shown in: °C per decade
- Data source: NASA POWER (MERRA-2)
- Record starts in: 1981
- Grid: cells of 0.5° latitude by 0.625° longitude; each cell is centred on a grid point, a multiple of the cell size, with its edges halfway between grid points. A place takes the nearest grid point.

## Surface (skin) temperature (TS)

Surface (skin) temperature (TS): How warm the very top of the ground or of the sea is, averaged over the month. Over open sea this is the sea-surface temperature, which the model is given rather than calculates.

- Catalogue ID: surface_temp
- NASA POWER parameter code: TS
- Units: °C
- Rate of change shown in: °C per decade
- Data source: NASA POWER (MERRA-2)
- Record starts in: 1981
- Grid: cells of 0.5° latitude by 0.625° longitude; each cell is centred on a grid point, a multiple of the cell size, with its edges halfway between grid points. A place takes the nearest grid point.

## Precipitation (PRECTOTCORR)

Precipitation (PRECTOTCORR): How much rain and snow falls, given as the average amount per day over the month.

- Catalogue ID: precipitation
- NASA POWER parameter code: PRECTOTCORR
- Units: mm/day
- Rate of change shown in: mm/day per decade
- Data source: NASA POWER (MERRA-2)
- Record starts in: 1981
- Grid: cells of 0.5° latitude by 0.625° longitude; each cell is centred on a grid point, a multiple of the cell size, with its edges halfway between grid points. A place takes the nearest grid point.

Caution: Rainfall trends from this model are less reliable than temperature trends.

## Relative humidity (RH2M)

Relative humidity (RH2M): How close the air two metres above the ground is to being saturated with water vapour, as a percentage, averaged over the month.

- Catalogue ID: relative_humidity
- NASA POWER parameter code: RH2M
- Units: %
- Rate of change shown in: percentage points per decade
- Data source: NASA POWER (MERRA-2)
- Record starts in: 1981
- Grid: cells of 0.5° latitude by 0.625° longitude; each cell is centred on a grid point, a multiple of the cell size, with its edges halfway between grid points. A place takes the nearest grid point.

Caution: Humidity trends from this model are less reliable than temperature trends.

## Specific humidity (QV2M)

Specific humidity (QV2M): How many grams of water vapour each kilogram of air two metres above the ground holds, averaged over the month.

- Catalogue ID: specific_humidity
- NASA POWER parameter code: QV2M
- Units: g/kg
- Rate of change shown in: g/kg per decade
- Data source: NASA POWER (MERRA-2)
- Record starts in: 1981
- Grid: cells of 0.5° latitude by 0.625° longitude; each cell is centred on a grid point, a multiple of the cell size, with its edges halfway between grid points. A place takes the nearest grid point.

Caution: Humidity trends from this model are less reliable than temperature trends.

## Wind speed at 10 m (WS10M)

Wind speed at 10 m (WS10M): How fast the wind blows ten metres above the ground, averaged over the month.

- Catalogue ID: wind_speed
- NASA POWER parameter code: WS10M
- Units: m/s
- Rate of change shown in: m/s per decade
- Data source: NASA POWER (MERRA-2)
- Record starts in: 1981
- Grid: cells of 0.5° latitude by 0.625° longitude; each cell is centred on a grid point, a multiple of the cell size, with its edges halfway between grid points. A place takes the nearest grid point.

Caution: Wind trends from this model are less reliable than temperature trends.

## Surface soil wetness (GWETTOP)

Surface soil wetness (GWETTOP): How wet the top 5 cm of soil is, from 0 for completely dry to 1 for completely soaked, averaged over the month.

- Catalogue ID: surface_soil_wetness
- NASA POWER parameter code: GWETTOP
- Units: fraction, 0 to 1
- Data source: NASA POWER (MERRA-2)
- Record starts in: 1981
- Grid: cells of 0.5° latitude by 0.625° longitude; each cell is centred on a grid point, a multiple of the cell size, with its edges halfway between grid points. A place takes the nearest grid point.

Caution: Soil wetness is calculated by the model from its own rainfall, so its trends are less reliable than temperature trends.

## Root-zone soil wetness (GWETROOT)

Root-zone soil wetness (GWETROOT): How wet the soil is down to where plant roots reach, from 0 for completely dry to 1 for completely soaked, averaged over the month.

- Catalogue ID: root_zone_soil_wetness
- NASA POWER parameter code: GWETROOT
- Units: fraction, 0 to 1
- Data source: NASA POWER (MERRA-2)
- Record starts in: 1981
- Grid: cells of 0.5° latitude by 0.625° longitude; each cell is centred on a grid point, a multiple of the cell size, with its edges halfway between grid points. A place takes the nearest grid point.

Caution: Soil wetness is calculated by the model from its own rainfall, so its trends are less reliable than temperature trends.

## Sunlight reaching the surface (ALLSKY_SFC_SW_DWN)

Sunlight reaching the surface (ALLSKY_SFC_SW_DWN): How much energy from sunlight reaches flat ground each day, counting cloudy days, averaged over the month.

- Catalogue ID: sunlight
- NASA POWER parameter code: ALLSKY_SFC_SW_DWN
- Units: MJ/m²/day
- Rate of change shown in: MJ/m²/day per decade
- Data source: NASA POWER (GEWEX SRB to 2000, CERES from 2001)
- Record starts in: 1984
- Grid: cells of 1° latitude by 1° longitude; each cell's edges are multiples of the cell size, such as whole degrees, so its centre lies halfway between them. A place takes the cell that holds it, and a place on an edge the cell north or east of it.

Caution: The data source for this variable changes in 2001, which can create an artificial step.

## Cloud cover (CLOUD_AMT)

Cloud cover (CLOUD_AMT): How much of the sky is covered by cloud, as a percentage, averaged over the month.

- Catalogue ID: cloud_cover
- NASA POWER parameter code: CLOUD_AMT
- Units: %
- Rate of change shown in: percentage points per decade
- Data source: NASA POWER (GEWEX SRB to 2000, CERES from 2001)
- Record starts in: 1984
- Grid: cells of 1° latitude by 1° longitude; each cell's edges are multiples of the cell size, such as whole degrees, so its centre lies halfway between them. A place takes the cell that holds it, and a place on an edge the cell north or east of it.

Caution: The data source for this variable changes in 2001, which can create an artificial step.

## Snow depth (SNODP)

Snow depth (SNODP): How deep the snow lying on the ground is, averaged over the month. Snow-free land reads zero, and over open sea POWER has no value.

- Catalogue ID: snow_depth
- NASA POWER parameter code: SNODP
- Units: cm
- Rate of change shown in: cm per decade
- Data source: NASA POWER (MERRA-2)
- Record starts in: 1981
- Grid: cells of 0.5° latitude by 0.625° longitude; each cell is centred on a grid point, a multiple of the cell size, with its edges halfway between grid points. A place takes the nearest grid point.

Caution: Snow trends from this model are less reliable than temperature trends.

## Snowfall (PRECSNOLAND)

Snowfall (PRECSNOLAND): How much snow falls on land, given as the average amount of melted water per day over the month. Snow-free land reads zero, and over open sea POWER has no value.

- Catalogue ID: snowfall
- NASA POWER parameter code: PRECSNOLAND
- Units: mm/day
- Rate of change shown in: mm/day per decade
- Data source: NASA POWER (MERRA-2)
- Record starts in: 1981
- Grid: cells of 0.5° latitude by 0.625° longitude; each cell is centred on a grid point, a multiple of the cell size, with its edges halfway between grid points. A place takes the nearest grid point.

Caution: Snow trends from this model are less reliable than temperature trends.

## Snow cover (FRSNO)

Snow cover (FRSNO): How much of the land is covered by snow, from 0 for none to 1 for all of it, averaged over the month. Snow-free land reads zero, and over open sea POWER has no value.

- Catalogue ID: snow_cover
- NASA POWER parameter code: FRSNO
- Units: fraction, 0 to 1
- Data source: NASA POWER (MERRA-2)
- Record starts in: 1981
- Grid: cells of 0.5° latitude by 0.625° longitude; each cell is centred on a grid point, a multiple of the cell size, with its edges halfway between grid points. A place takes the nearest grid point.

Caution: Snow trends from this model are less reliable than temperature trends.

## Sea ice (FRSEAICE)

Sea ice (FRSEAICE): How much of the sea in the grid cell is covered by ice, from 0 for open water to 1 for full cover, averaged over the month. Inland places and seas that never freeze read zero.

- Catalogue ID: sea_ice
- NASA POWER parameter code: FRSEAICE
- Units: fraction, 0 to 1
- Data source: NASA POWER (MERRA-2)
- Record starts in: 1981
- Grid: cells of 0.5° latitude by 0.625° longitude; each cell is centred on a grid point, a multiple of the cell size, with its edges halfway between grid points. A place takes the nearest grid point.

Caution: The model takes sea ice from satellite-based ocean analyses. Near Helsinki and Longyearbyen the record shows ice in months that should be ice-free until about 2005 and steps down in 2005 to 2007, so a trend or record year can be an artefact of the data, not a change in the ice.

## Surface air pressure (PS)

Surface air pressure (PS): The pressure of the air at the height of the ground in the grid cell, averaged over the month. It is lower on high ground, so it differs from the pressure on a weather map.

- Catalogue ID: surface_pressure
- NASA POWER parameter code: PS
- Units: kPa
- Rate of change shown in: kPa per decade
- Data source: NASA POWER (MERRA-2)
- Record starts in: 1981
- Grid: cells of 0.5° latitude by 0.625° longitude; each cell is centred on a grid point, a multiple of the cell size, with its edges halfway between grid points. A place takes the nearest grid point.

## Water vapour in the air column (TQV)

Water vapour in the air column (TQV): How much water vapour the whole column of air above the ground holds, as kilograms over each square metre, averaged over the month.

- Catalogue ID: water_vapour
- NASA POWER parameter code: TQV
- Units: kg/m²
- Rate of change shown in: kg/m² per decade
- Data source: NASA POWER (MERRA-2)
- Record starts in: 1981
- Grid: cells of 0.5° latitude by 0.625° longitude; each cell is centred on a grid point, a multiple of the cell size, with its edges halfway between grid points. A place takes the nearest grid point.

Caution: Water vapour trends from this model are less reliable than temperature trends.

## Strongest wind (WS10M_MAX)

Strongest wind (WS10M_MAX): The highest hourly wind speed ten metres above the ground in each month; a yearly value averages the months' highest winds. It is not a count of storms.

- Catalogue ID: max_wind_speed
- NASA POWER parameter code: WS10M_MAX
- Units: m/s
- Rate of change shown in: m/s per decade
- Data source: NASA POWER (MERRA-2)
- Record starts in: 1981
- Grid: cells of 0.5° latitude by 0.625° longitude; each cell is centred on a grid point, a multiple of the cell size, with its edges halfway between grid points. A place takes the nearest grid point.

Caution: Wind trends from this model are less reliable than temperature trends.

## Haze (AOD_55_ADJ)

Haze (AOD_55_ADJ): How much dust, smoke and other particles in the air dim the sunlight, as aerosol optical depth at 550 nm, averaged over the month: 0 is perfectly clear and 1 is very hazy. It comes from CERES SYN1deg, which blends MODIS satellite aerosol data into a model, not from the MODIS Aqua product shown in Giovanni.

- Catalogue ID: haze
- NASA POWER parameter code: AOD_55_ADJ
- Units: optical depth
- Data source: NASA POWER (CERES SYN1deg, from 2001)
- Record starts in: 2001
- Grid: cells of 1° latitude by 1° longitude; each cell's edges are multiples of the cell size, such as whole degrees, so its centre lies halfway between them. A place takes the cell that holds it, and a place on an edge the cell north or east of it.

Caution: POWER documents no change of source for haze since 2001, but changes in the satellite data its model takes in could not be ruled out.
