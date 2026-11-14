"""Generate frozen MK null tables and independent confirmation evidence (research plan v1)."""

import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.stats import beta

ROOT = Path(__file__).resolve().parents[2]
TABLE = ROOT / "backend/data/inference-v1.json"
REPORT = ROOT / "research/inference-results.json"
REPLICATES = 4000
BURN_IN = 250
METHOD = "mk_mc_envelope_v1"
SCENARIOS = [(phi, shape) for phi in (0.0, 0.2, 0.5) for shape in ("gaussian", "skewed")]


def records(n: int, phi: float, shape: str, seed: int) -> np.ndarray:
    """Stationary AR(1) approximation after burn-in; fixed-seed independent records."""
    rng = np.random.default_rng(seed)
    innovations = (
        rng.standard_normal((REPLICATES, BURN_IN + n))
        if shape == "gaussian"
        else rng.exponential(size=(REPLICATES, BURN_IN + n)) - 1
    )
    x = np.zeros(REPLICATES)
    result = np.empty((REPLICATES, n))
    for t in range(BURN_IN + n):
        x = phi * x + innovations[:, t]
        if t >= BURN_IN:
            result[:, t - BURN_IN] = x
    return result


def scores(x: np.ndarray) -> np.ndarray:
    """Absolute ordinary MK scores, including ties, independently vectorized for the study."""
    i, j = np.triu_indices(x.shape[1], 1)
    return np.abs(np.sign(x[:, j] - x[:, i]).sum(axis=1)).astype(int)


def main() -> None:
    """Freeze tables before evaluating independent confirmation draws; report all settings."""
    tails = {}
    for n in range(20, 46):
        counts = []
        for index, (phi, shape) in enumerate(SCENARIOS):
            sample = scores(records(n, phi, shape, 61000 + 100 * n + index))
            counts.append(
                np.cumsum(np.bincount(sample, minlength=n * (n - 1) // 2 + 1)[::-1])[::-1]
            )
        tails[str(n)] = np.max(counts, axis=0).tolist()
    document = {
        "method": METHOD,
        "replicates": REPLICATES,
        "burn_in": BURN_IN,
        "scenarios": SCENARIOS,
        "tails": tails,
    }
    content = (json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n").encode()
    TABLE.write_bytes(content)
    results = []
    for n in (20, 30, 45):
        for index, (phi, shape) in enumerate(SCENARIOS):
            seed = 91000 + 100 * n + index
            x = records(n, phi, shape, seed)
            null_p = (np.asarray(tails[str(n)])[scores(x)] + 1) / (REPLICATES + 1)
            k = int(np.count_nonzero(null_p < 0.05))
            upper = float(beta.ppf(0.95, k + 1, REPLICATES - k))
            trend_p = (np.asarray(tails[str(n)])[scores(x + np.arange(n) * 0.1)] + 1) / (
                REPLICATES + 1
            )
            results.append(
                {
                    "n": n,
                    "phi": phi,
                    "shape": shape,
                    "seed": seed,
                    "rejections": k,
                    "replicates": REPLICATES,
                    "rate": k / REPLICATES,
                    "upper95": upper,
                    "power_slope_0.1": float(np.mean(trend_p < 0.05)),
                    "pass": upper <= 0.07,
                }
            )
    report = {
        "method": METHOD,
        "table_sha256": hashlib.sha256(content).hexdigest(),
        "plan": "research/inference-plan.md",
        "settings": results,
        "passed": all(setting["pass"] for setting in results),
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(report, indent=2))
    if not report["passed"]:
        raise SystemExit("Inference gate failed; do not enable this table.")


if __name__ == "__main__":
    main()
