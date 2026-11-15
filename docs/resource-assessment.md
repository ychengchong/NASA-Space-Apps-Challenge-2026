# Resource integration assessment

Current release scope and integration order are controlled by
[technical specification Draft 5](technical-spec.md), sections 1, 6 and 12.
This assessment records earlier resource research; Draft 5 controls the current
delivery order and adds OpenAI discovery/RAG to the target scope.
This research informs optional extensions, not thirteen mandatory integrations.

Research date: 13 November 2026. Prepared with AI assistance from the team's
resource list and primary agency/developer documentation. This is an engineering
recommendation, not a change to the approved technical spec or an implemented
integration. Public documentation was inspected; no authenticated API requests,
account creation, dataset downloads or end-to-end integrations were performed.

## Submission-day scope decision

NASA POWER remains the only numerical runtime adapter for this submission. The frozen
Athens/Helsinki precipitation case demonstrates a water-related investigation without
claiming a second product, runoff estimate or validated precipitation significance.
The access tools and mission products below remain possible extensions, with the
disposition in each row; none is claimed as integrated merely because it was researched.

All challenge considerations have a recorded response:

| Consideration | Submission scope and evidence |
| --- | --- |
| Audience | Students and interested public; plain-language interface. User testing deferred by the team, so usability/learning impact is unmeasured. |
| Definitions | Catalogue definitions, units, sources and grid-cell caveats appear before/with an investigation. |
| Data detectives | Interpretation lesson and evidence panels are implemented; learning outcomes are not measured. |
| Short questions | Bounded planner/discovery proposals require confirmation; ambiguous places ask for a choice. Semantic evaluation and teammate review remain separate gates. |
| Examples | Four cached cases passed offline API/export checks; two teacher walkthroughs are written. |
| AI/literature or regional context | NASA/project documentation supports the explanation path. Named-variable discovery uses the actual variable guide; the app makes no verified regional-literature claims. |
| Daily/monthly | Monthly NASA inputs and explicit annual/seasonal aggregation are supported. Daily ingestion is deferred rather than presented as implemented. |
| Non-significant trends | Canonical wording distinguishes insufficient evidence from proof of no change. Descriptive rates remain inspectable. |
| Hydrological plotting tools | NASA tool access was assessed; CUAHSI discovery, plotting and metadata/export documentation was reviewed below. Runtime integration is deferred; the precipitation walkthrough is the water demonstration. |
| Seasonality/non-linearity | Exploratory seasonal rates and the limits of a monotonic-rate summary are explained. No nonlinear fit or seasonal significance is claimed. |

## Recommendation

Keep NASA POWER as the first data adapter. Add one carefully chosen second
product, preferably through a prepared Giovanni export, to demonstrate source
comparison. AppEEARS is the strongest next extension for land-surface temperature
or vegetation. NOAA station observations are useful for corroboration when their
coverage, quality and spatial representativeness are suitable.

Do not implement thirteen connectors: the list includes access services, data
portals, missions, papers, tutorials and explanatory articles. The latter need
curation or documentation rather than runtime integration. More connectors do
not by themselves establish better scientific validity or challenge relevance.

## Resource-by-resource findings

| Resource | Benefit to Trend Detective | Access and engineering implications | Recommended disposition |
| --- | --- | --- | --- |
| Giovanni | Expand beyond POWER's catalogue; selected precipitation, atmospheric or hydrological time series and area averages | NASA publishes Python examples for cloud point and area-average services. Area-average tutorial includes quota checks; authenticated workflows must be verified for the exact service/product | First extension: ingest a prepared export for one documented product; automate after validation |
| Hydrology Time Series | Hydrology-focused point extraction, useful for land-model water variables | Original GES DISC page is JavaScript-only in this inspection. NASA migration guidance refers to the Hydrology Time Series Viewer; NASA LDAS documents time-series access. Exact current viewer API, collections and restrictions were not established | Investigate only when a specific hydrological question needs it; avoid duplicating Giovanni access to the same product |
| CUAHSI HydroClient | Reference for map-based hydrological discovery, preview/plotting and export | Its official HIS/about pages describe discovery by area, variable and publisher, with CSV exports. Export documentation preserves source, units, method, quality-control, temporal support and missing-value metadata | Review/learning reference only for this submission; no account, download, API adapter or integration was attempted |
| AppEEARS | Extract point/area data for land-surface and vegetation investigations | Documented REST API, Earthdata authentication, task submission/status and downloads. QA layers, scale factors and product-specific compositing require handling; queued extraction does not guarantee an interactive response | High-value later adapter; prepare/cache extracts before demo |
| NOAA Climate Data Online | Quality-controlled station weather and metadata can corroborate a selected gridded result | API token required; documented limits are 5 requests/second and 10,000/day. Check pagination, units, flags, station history and complete overlapping dates | Optional validation source; NOAA data alone does not meet the organizer's NASA dataset requirement |
| SeaWiFS chlorophyll paper | Worked example of regional trend analysis, outlier sensitivity and limitations of interpreting coastal ocean colour | Research paper, not a live API. Coastal retrieved chlorophyll can be influenced by sediments and coloured dissolved matter | Use as scientific context; defer a chlorophyll capability until a suitable product and method are selected |
| KNMI Climate Explorer | Manual benchmark and access/discovery route for many climate datasets | Current welcome page requires human verification because of bot traffic; no stable supported API contract was established here. Cite both KNMI and original products when used | Manual research/corroboration; do not depend on scraping for the live app |
| Statistical test methods article (Medium) | Orientation to possible statistical approaches | Explanatory article, not a dataset/API. It is not a primary methodological specification for the production test | Optional reading; support adopted formulas with original papers and implementation documentation |
| Statistical significance guide (Statsig) | Potential background for accessible terminology | Explanatory article, not a data service or validation of climate-time-series assumptions | Optional reading; review audience-facing wording against authoritative statistical references |
| RADARSAT Constellation Mission data | Potential flood, ice, wetland or ecosystem-change investigations | CSA documents EODMS registration, public versus vetted access and product licences. SAR imagery is not an immediately usable rainfall/temperature series | Defer; would require its own derived-variable and imagery-processing pipeline |
| GEO.ca | Find Canadian contextual layers and particular environmental datasets | Discovery portal, not one uniform temporal dataset/API. Dates, licences, access and semantics depend on the chosen collection | Add only for a defined Canadian case; do not treat every map layer as a trend record |
| SWOT mission | Lake/river water elevation and surface-water variability | Launched December 2022; the mission record is under four years at research time. PO.DAAC lists hydrology products with different geometries/formats | Separate short-record exploration later; do not force it into the current minimum-ten-annual-values trend verdict |
| CSA ecosystem-monitoring overview | Explain potential ecosystem use cases and identify relevant missions | Outreach/background page, not a numerical data feed. Its SWOT description still says in development, unlike CSA's current mission page | Background only; verify dated statements against current mission/product documentation |
| CSA SAR Python/QGIS tutorial | Learning material for RADARSAT raster/vector access and plotting | Tutorial uses GDAL/cartopy/matplotlib and example wildfire imagery; it is not a validated long-term change-detection workflow | Reference for a future SAR feature; no need to add these dependencies to the current app |

## CUAHSI workflow lessons

Reviewed on 15 November 2026: CUAHSI's [HIS overview](https://www.cuahsi.org/data-services/hydrologic-information-system)
and [HydroClient description](https://data.cuahsi.org/Home/About) show a workflow from
location/quantity/publisher to preview and export. The useful lesson for the water case
is to identify the measured quantity and its spatial support before comparing series.
This is a documentation review, not a tested integration.

The [official export guide](https://help.cuahsi.org/hc/en-us/articles/206078888-Understanding-Exported-File-formats-from-HydroClient)
documents units, method/quality information, temporal support, timestamps, missing-value
sentinels and publisher attribution. Any future adapter must retain those distinctions;
a station discharge series cannot be substituted for a gridded precipitation series.
The existing NASA example keeps its own metadata, missing months and descriptive limits.

## Important research details

### Access services are not independent datasets

Giovanni, Hydrology Time Series and AppEEARS are access/extraction routes. Their
presence does not tell us which underlying product answers a question. Record
product shortname/version, variable, temporal/spatial coverage and processing.
Using the same model product through two portals is not independent validation.
Cross-product agreement is corroboration, not proof of ground truth; products
can also share input observations.

NASA's GES DISC migration guidance describes movement to Earthdata Cloud and
recommends cloud Giovanni services and the Hydrology Time Series Viewer. Avoid
building against an old URL solely because it appears in a challenge link.

### AppEEARS needs preprocessing and task handling

The API documents product metadata including scale factors, fill values and QA
layers, as well as authentication and task-status endpoints. An adapter needs
submit -> poll -> download -> apply product-specific QA/scaling -> normalize ->
cache. Pre-extracted, versioned series are a better weekend demonstration path
than assuming a fresh extraction completes inside the app's response-time target.

MODIS land-surface temperature and 2-metre air temperature are distinct quantities.
They must not be silently substituted for each other. Product names, units,
compositing periods and QA rules belong in the catalogue and provenance.

### Hydrology collections require version and geography checks

NASA's GLDAS table distinguishes 2.0, 2.1 and 2.2 with different forcing,
assimilation and temporal coverage. Do not concatenate versions to manufacture a
longer trend record. Check regional availability rather than assuming every LDAS
product covers a requested location. Missing monthly support in a particular
endpoint must be resolved before integration; do not assume the viewer itself
is an unrestricted monthly-data API.

### The SeaWiFS example is a reference, not statistical certification

The paper describes a least-squares analysis of monthly time series, confidence
intervals and comparison with robust regression. Its coastal retrieval caveats
and sensitivity to unusual events are useful lessons. It does not establish the
validity of our custom autocorrelation correction or provide a reusable API.

### Short records and imagery need separate analysis contracts

SWOT can support useful recent hydrological investigations without supporting
the current decade-scale annual trend test. Many observations over a short time
span are not equivalent to many years of climate evidence. Longer pre-SWOT
hydrology records exist, but combining missions would require separate continuity
and datum checks.

RCM imagery needs a defined derived quantity, comparable acquisitions and a
validated processing/QA method before a temporal statistic has a useful meaning.
A raster plotting tutorial does not supply that entire analysis.

## Proposed implementation sequence

1. Complete the currently specified POWER path with frozen example data, explicit
   units/aggregation, provenance and verified statistics.
2. Add one prepared second-product series from Giovanni, tied to a concrete
   question and common period. Compare definitions, units and spatial support.
3. If land-surface/vegetation questions are a priority, add one AppEEARS product
   with QA rules; prove a prepared example before automating tasks.
4. If useful for a demonstration location, add one reviewed NOAA station series
   as corroboration rather than an interchangeable gridded observation.
5. Keep KNMI and papers as references. Defer SWOT/SAR/Canadian context layers
   until there is a specific supported user question and appropriate method.

This sequence is proposed, not approved implementation scope. Credentials,
product selection, additional dependencies, source contracts and any statistical
changes remain unresolved. No service availability, latency or data coverage is
claimed from documentation inspection alone.

## Proposed shared data boundary

Before adding an adapter, extend the approved source contract to preserve:

- Product ID/version and variable definition; access service separately identified.
- Source URL, request/region, time coverage, retrieval timestamp and raw checksum.
- Original/output units, transformations, QA filtering and aggregation method.
- Temporal support (instant/mean/accumulation/composite) and spatial support
  (station/grid cell/area/river reach/lake); do not reduce all of them to a point.
- Explicit missing values, coverage diagnostics and unsupported-request behaviour.

Analysis consumes a validated normalized series. Each source adapter handles its
own access and product-specific interpretation. This proposal does not silently
change section 5's existing types; revise that contract deliberately if adopted.

## Sources and inspection limits

Primary implementation/data sources:

- [Giovanni](https://giovanni.gsfc.nasa.gov/giovanni/)
- [NASA GES DISC tutorials](https://github.com/nasa/gesdisc-tutorials): cloud time-series and area-average examples.
- [GES DISC migration guidance](https://github.com/nasa/gesdisc-tutorials/blob/main/user-guidance/GES_DISC_Migration_to_Earthdata_Website_and_Earthdata_Cloud.md)
- [Hydrology Time Series original listing](https://disc.gsfc.nasa.gov/information/tools?title=Hydrology%20Time%20Series): content not readable beyond JavaScript shell here.
- [NASA LDAS data access](https://ldas.gsfc.nasa.gov/data)
- [NASA GLDAS versions](https://ldas.gsfc.nasa.gov/gldas/dataset)
- [AppEEARS API documentation](https://appeears.earthdatacloud.nasa.gov/api/)
- [NASA AppEEARS example](https://git.earthdata.nasa.gov/projects/LPDUR/repos/appeears-api-getting-started_r/browse/AppEEARS_API_Area_R.Rmd?at=4391f1a7d97&until=3dcb6c2ddf1efb9ded8bda147aacf8251fc30262): historical product versions are examples, not current product selections.
- [NOAA CDO](https://www.ncei.noaa.gov/cdo-web/) and [API documentation](https://www.ncei.noaa.gov/cdo-web/webservices/v2)
- [SeaWiFS research paper](https://ntrs.nasa.gov/api/citations/20090042747/downloads/20090042747.pdf)
- [KNMI Climate Explorer](https://climexp.knmi.nl/)
- [CSA RCM access](https://www.asc-csa.gc.ca/eng/satellites/radarsat/access-to-data/how-to-become-a-user.asp): supplied catalogue URL timed out, so access conclusions use this official guidance.
- [GEO.ca](https://geo.ca/home/)
- [CSA SWOT mission](https://www.asc-csa.gc.ca/eng/satellites/swot/) and [NASA PO.DAAC SWOT products](https://podaac.jpl.nasa.gov/SWOT?tab=datasets-information)
- [NASA pre-SWOT hydrology records](https://podaac.jpl.nasa.gov/highlights/MEaSUREs_Pre-SWOT_Hydrology_Datasets_Release)
- [CSA ecosystem overview](https://www.asc-csa.gc.ca/eng/satellites/everyday-lives/monitoring-and-protecting-our-ecosystems-from-space.asp)
- [CSA SAR tutorial](https://github.com/asc-csa/Synthetic_Aperture_Radar_Tutorial)
- [SciPy Theil-Sen documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.theilslopes.html): useful implementation/reference entry point; does not by itself resolve serial dependence.

Supplied secondary reading was inspected to classify its role, not adopted as
authority for scientific implementation:

- [Medium trend-testing article](https://medium.com/@snp.kriss/statistical-test-methods-to-detect-trends-in-time-series-data-b361a0ec530b)
- [Statsig significance guide](https://www.statsig.com/perspectives/a-comprehensive-guide-to-statistical-significance)

Some supplied pages required JavaScript or returned errors. Successful public
page inspection is not evidence that authenticated requests, quotas or the full
extraction workflow work for this team. No third-party article code was copied.
