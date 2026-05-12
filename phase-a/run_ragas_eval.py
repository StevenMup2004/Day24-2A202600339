from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lab24_common import (
    compact_contexts,
    extract_json_object,
    load_env,
    openai_api_key_available,
    openai_chat,
    read_csv,
    score_rag_row,
    summarize_scores,
    write_csv,
    write_json,
)

METRICS = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]


def openai_score_row(question: str, answer: str, ground_truth: str, contexts: list[str]) -> dict[str, float]:
    system = (
        "You are a strict RAG evaluation judge. Score the answer from 0.0 to 1.0 on four metrics: "
        "faithfulness, answer_relevancy, context_precision, context_recall. Return JSON only."
    )
    user = f"""Question:
{question}

Answer:
{answer}

Ground truth:
{ground_truth}

Retrieved contexts:
{chr(10).join('- ' + c[:900] for c in contexts[:3])}

Return JSON exactly like:
{{"faithfulness": 0.0, "answer_relevancy": 0.0, "context_precision": 0.0, "context_recall": 0.0, "reason": "short"}}"""
    payload = extract_json_object(openai_chat(system, user, max_tokens=260))
    return {metric: round(max(0.0, min(1.0, float(payload.get(metric, 0.0)))), 4) for metric in METRICS}


def ensure_testset() -> Path:
    path = ROOT / "phase-a" / "testset_v1.csv"
    if not path.exists():
        import generate_testset

        generate_testset.main()
    return path


def run_eval(limit: int | None = None, use_openai: bool = False, require_openai: bool = False) -> tuple[list[dict[str, object]], dict[str, object]]:
    load_env()
    if require_openai and not openai_api_key_available():
        raise RuntimeError("OPENAI_API_KEY is required but not set")
    rows = read_csv(ensure_testset())
    if limit:
        rows = rows[:limit]

    results: list[dict[str, object]] = []
    for idx, row in enumerate(rows, 1):
        contexts = compact_contexts(row.get("contexts", "[]"))
        answer = row.get("answer") or row.get("ground_truth", "")
        eval_mode = "ragas_style_offline_fallback"
        if use_openai or require_openai:
            try:
                scores = openai_score_row(row.get("question", ""), answer, row.get("ground_truth", ""), contexts)
                eval_mode = "openai_ragas_compatible_judge"
            except Exception:
                if require_openai:
                    raise
                scores = score_rag_row(answer, row.get("ground_truth", ""), contexts)
                eval_mode = "ragas_style_offline_fallback_after_openai_error"
        else:
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
                "eval_mode": eval_mode,
            }
        )

    aggregate = summarize_scores(results, METRICS)
    modes = sorted({str(row["eval_mode"]) for row in results})
    summary: dict[str, object] = {
        **aggregate,
        "num_questions": len(results),
        "eval_mode": ", ".join(modes),
        "note": "OpenAI-backed RAGAS-compatible judging is used when --openai/--require-openai is enabled; otherwise an offline fallback keeps the pipeline runnable.",
        "estimated_cost_usd": round(len(results) * (0.006 if "openai_ragas_compatible_judge" in modes else 0.002), 3),
    }
    return results, summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--output", default=None)
    parser.add_argument("--openai", action="store_true")
    parser.add_argument("--require-openai", action="store_true")
    args = parser.parse_args()

    results, summary = run_eval(args.limit, use_openai=args.openai, require_openai=args.require_openai)
    suffix = "_sample" if args.limit and not args.output else ""
    out_csv = ROOT / "phase-a" / (args.output or f"ragas_results{suffix}.csv")
    out_json = ROOT / "phase-a" / f"ragas_summary{suffix}.json"
    write_csv(out_csv, results)
    write_json(out_json, summary)
    print(f"Wrote {len(results)} rows to {out_csv.relative_to(ROOT)}")
    print(summary)


if __name__ == "__main__":
    main()
