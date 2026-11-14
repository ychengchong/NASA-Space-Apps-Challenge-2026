# Verification record ? 14 November 2026

Branch: `fix/draft3-compliance`, based on `initial-app` at d42207c.
Changes are uncommitted; this is verification of the working tree, not a pushed release.

## Observed checks

| Check | Result |
| --- | --- |
| Fresh environment installed from updated uv.lock | Passed; CPython 3.14.5, no dependence on removed provider SDKs |
| Full backend suite | 706 passed |
| Backend Ruff lint and formatting | Passed |
| Pydantic-to-TypeScript contract check | Passed |
| Frontend tests | 346 passed, 32 files, Node 22.23.5 |
| Frontend ESLint, Prettier and TypeScript/Vite build | Passed |
| Original inference confirmation | All 18 settings passed; 4,000 null replications each |
| Independent full-length confirmation | All 156 settings passed; maximum one-sided 95% upper bound 0.0670674 |
| Tied-value stress panel and constant | All 18 stress settings passed; constant p=1 |
| Real app over local HTTP with AI disabled | Readiness, three cached examples, identical pinned replay, checksum-verified evidence, CSVs and PNG exports passed |
| Invalid dates / missing pin | Rejected; missing pins did not fall back to live data |
| Export layout inspection | Single-place T2M and two-place precipitation PNGs inspected; titles, units, data, legends and attribution were readable |
| Git whitespace check / scientific table EOL protection | Passed; frozen calibration bytes are protected from checkout conversion |

The original source-cancellation failure reproduced on Python 3.14 is covered by a
passing regression. Scientific regressions cover missing internal/endpoint years,
disjoint comparison coverage, changed source snapshots, grid boundaries and a zero
median rate with significant rank evidence. These distinct statistics are not conflated.

## Exact runtime limits

The manual app and inference engine were exercised with cached NASA data. Provider
integration uses fake HTTP transports. No paid model request or real Ollama generation
was made. The AI remains off until exact model identity, evaluation and required
budget/persistence configuration are supplied. No benchmark accuracy is claimed.

The browser tool reported its host unavailable, so browser interactions, keyboard and
phone-width layout were not visually verified. Docker and Ollama executables were not
installed in this environment; the image, named-volume redeploy and live local model
are unverified. Public deployment, student study and final video/deck are separate
team tasks. Plotly retains its existing large lazy-loaded chunk warning (~385 KB gzip).

Legacy seed data is marked as normalized evidence without original response bytes;
new downloads retain exact bytes. Unknown scientific product releases remain unknown.
This prototype does not claim universal climate calibration, a judging score or a
Global Winner outcome. See [evaluation protocol](evaluation.md) for remaining evidence.
