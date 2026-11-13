# Trend Detective

A NASA Space Apps Challenge 2026 project helping students investigate regional
Earth-system trends and understand what the evidence supports.

## Current plan

The first release focuses on NASA POWER two-metre air temperature, two locations,
annual series, trend estimates, validated significance and a guided evidence lesson.
Manual controls and frozen examples work without live NASA/model connections.
Local Ollama and hosted AI are optional, evaluated adapters.

## Documents

- [Technical specification](docs/technical-spec.md): current scope, contracts and release gates.
- [Full challenge](docs/challenge-description.md)
- [NASA data requirements and judging criteria](docs/event-information.md)
- [Resource research](docs/resource-assessment.md)

## Status and next step

This repository contains planning documents. Application code, installed project
dependencies, downloaded models/data and evaluation results do not exist yet.
No setup, test or serving commands have been verified.

## Proposed local setup

Use standard 64-bit CPython 3.14.10, recorded in `.python-version`. Runtime
dependencies are pinned in [requirements.txt](requirements.txt); development and
statistical-reference tools are in [requirements-dev.txt](requirements-dev.txt).
These are direct dependency pins, not a complete transitive lockfile.

From the repository root in PowerShell:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
.\.venv\Scripts\python -m pip check
```

Installation and combined dependency resolution have not been tested yet. Ollama
and its model are installed separately; frontend packages will live in
`package.json`. Optional hosted AI, MCP and chart-rendering dependencies are deferred.

Next: verify a POWER snapshot and its metadata, implement aggregation and the
descriptive estimator, then evaluate the candidate inference method before making
significance claims. Hardware/model choice and hosting remain open. Extra sources,
RAG, period scanning, maps and MCP are conditional extensions.

## NASA data and AI use

NASA POWER is the planned service. Actual product/version, query, retrieval date
and attribution will accompany acquired snapshots. Planned use is not evidence
that a dataset has already been obtained or analyzed.

Codex assisted with setup, dependency declarations, research and documentation. The spec was drafted and
revised with AI assistance. Application functionality, statistical calibration,
user impact and model quality have not been demonstrated.
