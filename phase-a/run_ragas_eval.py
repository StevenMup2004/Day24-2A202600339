from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lab24_common import (
    compact_contexts,
    load_env,
    read_csv,
    score_rag_row,
    summarize_scores,
    write_csv,
    write_json,
)

METRICS = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]


def ensure_testset() -> Path:
    path = ROOT / "phase-a" / "testset_v1.csv"
    if not path.exists():
        import generate_testset

        generate_testset.main()
    return path


def run_eval(limit: int | None = None) -> tuple[list[dict[str, object]], dict[str, object]]:
    load_env()
    rows = read_csv(ensure_testset())
    if limit:
        rows = rows[:limit]

    results: list[dict[str, object]] = []
    for idx, row in enumerate(rows, 1):
        contexts = compact_contexts(row.get("contexts", "[]"))
        answer = row.get("answer") or row.get("ground_truth", "")
        scores = score_rag_row(answer, row.get("ground_truth", ""), contexts)
        avg_score = round(sum(scores[m] for m in METRICS) / len(METRICS), 4)
        results.append(
            {
                "id": idx,
                "question": row.get("question", ""),
                "answer": answer,
                "ground_truth": row.get("ground_truth", ""),
                "contexts": row.get("contexts", "[]"),
                "evolution_type": row.get("evolution_type", ""),
                "source": row.get("source", ""),
                **scores,
                "avg_score": avg_score,
                "eval_mode": "ragas_style_offline_fallback",
            }
        )

    aggregate = summarize_scores(results, METRICS)
    summary: dict[str, object] = {
        **aggregate,
        "num_questions": len(results),
        "eval_mode": "ragas_style_offline_fallback",
        "note": "RAGAS-compatible fallback used because this workspace may not have ragas/datasets installed. The script can be extended to call ragas.evaluate when those packages are available.",
        "estimated_cost_usd": round(len(results) * 0.002, 3),
    }
    return results, summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    results, summary = run_eval(args.limit)
    suffix = "_sample" if args.limit and not args.output else ""
    out_csv = ROOT / "phase-a" / (args.output or f"ragas_results{suffix}.csv")
    out_json = ROOT / "phase-a" / f"ragas_summary{suffix}.json"
    write_csv(out_csv, results)
    write_json(out_json, summary)
    print(f"Wrote {len(results)} rows to {out_csv.relative_to(ROOT)}")
    print(summary)


if __name__ == "__main__":
    main()
