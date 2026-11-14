"""Independent full-length confirmation of the frozen procedure; never modifies its tables."""

import hashlib
import json
import platform

import numpy as np
import scipy
from scipy.stats import beta

from app.tools.inference import TABLE_SHA256
from scripts.calibrate_inference import METHOD, REPLICATES, ROOT, SCENARIOS, TABLE, records, scores


def main() -> None:
    content = TABLE.read_bytes()
    if hashlib.sha256(content).hexdigest() != TABLE_SHA256:
        raise SystemExit("The frozen table changed; confirmation refused.")
    tails = json.loads(content)["tails"]
    results = []
    stress = []
    for n in range(20, 46):
        lookup = np.asarray(tails[str(n)])
        for index, (phi, shape) in enumerate(SCENARIOS):
            seed = 141000 + 100 * n + index
            x = records(n, phi, shape, seed)
            k = int(np.count_nonzero((lookup[scores(x)] + 1) / (REPLICATES + 1) < 0.05))
            upper = float(beta.ppf(0.95, k + 1, REPLICATES - k))
            results.append(
                {
                    "n": n,
                    "phi": phi,
                    "shape": shape,
                    "seed": seed,
                    "rejections": k,
                    "replicates": REPLICATES,
                    "upper95": upper,
                    "rate": k / REPLICATES,
                    "pass": upper <= 0.07,
                }
            )
            if n in (20, 30, 45):
                rounded = np.round(x, 1)
                rejects = int(
                    np.count_nonzero((lookup[scores(rounded)] + 1) / (REPLICATES + 1) < 0.05)
                )
                bound = float(beta.ppf(0.95, rejects + 1, REPLICATES - rejects))
                stress.append(
                    {
                        "n": n,
                        "phi": phi,
                        "shape": shape,
                        "seed": seed,
                        "kind": "one_decimal_ties",
                        "rejections": rejects,
                        "replicates": REPLICATES,
                        "upper95": bound,
                        "pass": bound <= 0.07,
                    }
                )
    constant_p = float((np.asarray(tails["45"])[0] + 1) / (REPLICATES + 1))
    report = {
        "method": METHOD,
        "table_sha256": TABLE_SHA256,
        "plan": "research/inference-followup-plan.md",
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
        "settings": results,
        "ties_stress": stress,
        "constant_p": constant_p,
        "passed": all(row["pass"] for row in results + stress) and constant_p == 1,
    }
    destination = ROOT / "research/inference-confirmation-all-lengths.json"
    destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(
        json.dumps(
            {
                "settings": len(results),
                "max_upper95": max(row["upper95"] for row in results),
                "stress_checks": len(stress),
                "passed": report["passed"],
            }
        )
    )
    if not report["passed"]:
        raise SystemExit("Full-length confirmation failed. Preserve all results and review scope.")


if __name__ == "__main__":
    main()
