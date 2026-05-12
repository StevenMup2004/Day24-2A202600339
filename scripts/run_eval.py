from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "phase-a"))

from lab24_common import write_csv, write_json
import run_ragas_eval


def parse_threshold(raw: str) -> tuple[str, float]:
    if "=" not in raw:
        raise ValueError("threshold must look like metric=value")
    metric, value = raw.split("=", 1)
    return metric.strip(), float(value)


def resolve_output(raw: str) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else ROOT / path


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def load_or_run_summary(args: argparse.Namespace) -> dict[str, object]:
    summary_path = resolve_output(args.summary_output)
    csv_path = resolve_output(args.output_csv)
    if args.skip_run:
        print(f"Reading existing eval summary from {display_path(summary_path)}")
        return json.loads(summary_path.read_text(encoding="utf-8"))

    print("Running fresh RAG evaluation before applying thresholds...")
    rows, summary = run_ragas_eval.run_eval(
        limit=args.limit,
        use_openai=args.openai,
        require_openai=args.require_openai,
    )
    write_csv(csv_path, rows)
    write_json(summary_path, summary)
    print(f"Wrote {len(rows)} rows to {display_path(csv_path)}")
    print(f"Wrote summary to {display_path(summary_path)}")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold", action="append", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--openai", action="store_true")
    parser.add_argument("--require-openai", action="store_true")
    parser.add_argument("--skip-run", action="store_true", help="Only read the existing summary artifact.")
    parser.add_argument("--output-csv", default="phase-a/ragas_results.csv")
    parser.add_argument("--summary-output", default="phase-a/ragas_summary.json")
    args = parser.parse_args()

    summary = load_or_run_summary(args)
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
