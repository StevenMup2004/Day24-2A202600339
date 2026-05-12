from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def parse_threshold(raw: str) -> tuple[str, float]:
    if "=" not in raw:
        raise ValueError("threshold must look like metric=value")
    metric, value = raw.split("=", 1)
    return metric.strip(), float(value)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold", action="append", default=None)
    args = parser.parse_args()

    summary_path = ROOT / "phase-a" / "ragas_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    failures = []
    thresholds = args.threshold or ["faithfulness=0.75", "answer_relevancy=0.70"]
    for raw in thresholds:
        metric, target = parse_threshold(raw)
        actual = float(summary.get(metric, 0.0))
        status = "PASS" if actual >= target else "FAIL"
        print(f"{status}: {metric} actual={actual:.4f} target={target:.4f}")
        if actual < target:
            failures.append((metric, actual, target))
    if failures:
        raise SystemExit(1)
    print("Eval gate passed.")


if __name__ == "__main__":
    main()
