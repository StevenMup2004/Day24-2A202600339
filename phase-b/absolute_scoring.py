from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lab24_common import extract_json_object, openai_api_key_available, openai_chat, read_csv, token_f1, write_csv, write_json


def to_1_5(score: float) -> int:
    if score >= 0.82:
        return 5
    if score >= 0.62:
        return 4
    if score >= 0.42:
        return 3
    if score >= 0.22:
        return 2
    return 1


def openai_absolute_score(question: str, answer: str) -> dict[str, int | float]:
    system = (
        "You are a strict RAG answer scoring judge. Score the answer on a 1-5 scale for accuracy, relevance, "
        "conciseness, and helpfulness. Return JSON only."
    )
    user = f"""Question:
{question}

Answer:
{answer}

Return JSON exactly like:
{{"accuracy": 1, "relevance": 1, "conciseness": 1, "helpfulness": 1, "overall": 1.0}}"""
    payload = extract_json_object(openai_chat(system, user, max_tokens=160))
    scores: dict[str, int | float] = {}
    for key in ["accuracy", "relevance", "conciseness", "helpfulness"]:
        scores[key] = max(1, min(5, int(round(float(payload.get(key, 3))))))
    scores["overall"] = round(float(payload.get("overall", sum(int(scores[k]) for k in ["accuracy", "relevance", "conciseness", "helpfulness"]) / 4)), 2)
    return scores


def score_rows(limit: int | None = None, use_openai: bool = False, require_openai: bool = False) -> list[dict[str, object]]:
    if require_openai and not openai_api_key_available():
        raise RuntimeError("OPENAI_API_KEY is required but not set")
    source = ROOT / "phase-a" / "ragas_results.csv"
    rows = read_csv(source)[: limit or 30]
    scored: list[dict[str, object]] = []
    for idx, row in enumerate(rows, 1):
        answer = row.get("answer", "")
        ground_truth = row.get("ground_truth", "")
        mode = "local_fallback_rubric"
        if use_openai or require_openai:
            try:
                scores = openai_absolute_score(row.get("question", ""), answer)
                accuracy = int(scores["accuracy"])
                relevance = int(scores["relevance"])
                conciseness = int(scores["conciseness"])
                helpfulness = int(scores["helpfulness"])
                overall = round(float(scores["overall"]), 2)
                mode = "openai_absolute_rubric"
            except Exception:
                if require_openai:
                    raise
                accuracy_raw = token_f1(answer, ground_truth)
                relevance_raw = max(float(row.get("answer_relevancy", 0)), token_f1(answer, row.get("question", "")))
                conciseness_raw = 1.0 if len(answer) <= 320 else max(0.2, 1 - (len(answer) - 320) / 1000)
                helpfulness_raw = (accuracy_raw + relevance_raw + conciseness_raw) / 3
                accuracy = to_1_5(accuracy_raw)
                relevance = to_1_5(relevance_raw)
                conciseness = to_1_5(conciseness_raw)
                helpfulness = to_1_5(helpfulness_raw)
                overall = round((accuracy + relevance + conciseness + helpfulness) / 4, 2)
                mode = "local_fallback_after_openai_error"
        else:
            accuracy_raw = token_f1(answer, ground_truth)
            relevance_raw = max(float(row.get("answer_relevancy", 0)), token_f1(answer, row.get("question", "")))
            conciseness_raw = 1.0 if len(answer) <= 320 else max(0.2, 1 - (len(answer) - 320) / 1000)
            helpfulness_raw = (accuracy_raw + relevance_raw + conciseness_raw) / 3
            accuracy = to_1_5(accuracy_raw)
            relevance = to_1_5(relevance_raw)
            conciseness = to_1_5(conciseness_raw)
            helpfulness = to_1_5(helpfulness_raw)
            overall = round((accuracy + relevance + conciseness + helpfulness) / 4, 2)
        scored.append(
            {
                "question_id": idx,
                "question": row.get("question", ""),
                "answer": answer,
                "accuracy": accuracy,
                "relevance": relevance,
                "conciseness": conciseness,
                "helpfulness": helpfulness,
                "overall": overall,
                "rubric": "1-5 scale; overall is average of 4 dimensions",
                "judge_mode": mode,
            }
        )
    return scored


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--openai", action="store_true")
    parser.add_argument("--require-openai", action="store_true")
    args = parser.parse_args()
    rows = score_rows(args.limit, use_openai=args.openai, require_openai=args.require_openai)
    suffix = "_sample" if args.limit else ""
    write_csv(ROOT / "phase-b" / f"absolute_scores{suffix}.csv", rows)
    avg = round(sum(float(r["overall"]) for r in rows) / len(rows), 3) if rows else 0.0
    write_json(ROOT / "phase-b" / f"absolute_scores_summary{suffix}.json", {"num_questions": len(rows), "overall_avg": avg})
    print(f"Wrote {len(rows)} absolute score rows; overall_avg={avg}")


if __name__ == "__main__":
    main()
