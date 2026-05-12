from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lab24_common import baseline_answer, compact_contexts, load_env, read_csv, token_f1, write_csv
from lab24_common import extract_json_object, openai_api_key_available, openai_chat


def parse_judge_output(text: str) -> dict[str, str]:
    """Robust JSON parser with fallback for LLM judge outputs."""
    cleaned = text.strip().replace("```json", "").replace("```", "").strip()
    try:
        payload = json.loads(cleaned)
        winner = str(payload.get("winner", "tie")).upper()
        if winner not in {"A", "B", "TIE"}:
            winner = "TIE"
        return {"winner": "tie" if winner == "TIE" else winner, "reason": str(payload.get("reason", ""))}
    except json.JSONDecodeError:
        upper = cleaned.upper()
        if "WINNER: A" in upper or '"A"' in upper:
            return {"winner": "A", "reason": "Fallback parser detected A."}
        if "WINNER: B" in upper or '"B"' in upper:
            return {"winner": "B", "reason": "Fallback parser detected B."}
        return {"winner": "tie", "reason": "Parse fallback: tie."}


def judge_pair(question: str, ground_truth: str, answer_a: str, answer_b: str) -> dict[str, str | float]:
    """Deterministic local judge: factual overlap first, concise tie-break second."""
    score_a = 0.78 * token_f1(answer_a, ground_truth) + 0.22 * token_f1(answer_a, question)
    score_b = 0.78 * token_f1(answer_b, ground_truth) + 0.22 * token_f1(answer_b, question)
    len_penalty_a = max(0, len(answer_a) - 420) / 3000
    len_penalty_b = max(0, len(answer_b) - 420) / 3000
    score_a -= len_penalty_a
    score_b -= len_penalty_b
    if abs(score_a - score_b) < 0.035:
        winner = "tie"
    else:
        winner = "A" if score_a > score_b else "B"
    return {
        "winner": winner,
        "score_a": round(score_a, 4),
        "score_b": round(score_b, 4),
        "reason": "Compared factual accuracy, relevance to question, and conciseness.",
    }


def judge_pair_openai(question: str, ground_truth: str, answer_a: str, answer_b: str) -> dict[str, str | float]:
    system = (
        "You are an impartial evaluation judge for a RAG system. Compare Answer A and Answer B for the same question. "
        "Prefer factual accuracy against the ground truth, relevance to the question, and concise helpfulness. "
        "Return JSON only with keys winner, score_a, score_b, reason. winner must be A, B, or tie."
    )
    user = f"""Question:
{question}

Ground truth:
{ground_truth}

Answer A:
{answer_a}

Answer B:
{answer_b}

Return JSON only."""
    payload = extract_json_object(openai_chat(system, user, max_tokens=220))
    winner = str(payload.get("winner", "tie")).strip().upper()
    if winner not in {"A", "B"}:
        winner = "tie"
    return {
        "winner": winner,
        "score_a": round(float(payload.get("score_a", 0.5)), 4),
        "score_b": round(float(payload.get("score_b", 0.5)), 4),
        "reason": str(payload.get("reason", "OpenAI judge comparison."))[:300],
    }


def flip_winner(winner: str) -> str:
    if winner == "A":
        return "B"
    if winner == "B":
        return "A"
    return "tie"


def aggregate(run1: str, run2_normalized: str) -> str:
    return run1 if run1 == run2_normalized else "tie"


def run(limit: int | None = None, use_openai: bool = False, require_openai: bool = False) -> list[dict[str, object]]:
    load_env()
    if require_openai and not openai_api_key_available():
        raise RuntimeError("OPENAI_API_KEY is required but not set")
    source = ROOT / "phase-a" / "ragas_results.csv"
    if not source.exists():
        sys.path.insert(0, str(ROOT / "phase-a"))
        import run_ragas_eval

        run_ragas_eval.main()
    rows = read_csv(source)
    rows = rows[: limit or 30]
    out: list[dict[str, object]] = []
    for idx, row in enumerate(rows, 1):
        contexts = compact_contexts(row.get("contexts", "[]"))
        answer_a = row.get("answer", "")
        answer_b = baseline_answer(contexts, row.get("ground_truth", ""))

        mode = "local_fallback_judge"
        if use_openai or require_openai:
            try:
                run1 = judge_pair_openai(row["question"], row["ground_truth"], answer_a, answer_b)
                run2_swapped = judge_pair_openai(row["question"], row["ground_truth"], answer_b, answer_a)
                mode = "openai_pairwise_judge"
            except Exception:
                if require_openai:
                    raise
                run1 = judge_pair(row["question"], row["ground_truth"], answer_a, answer_b)
                run2_swapped = judge_pair(row["question"], row["ground_truth"], answer_b, answer_a)
                mode = "local_fallback_after_openai_error"
        else:
            run1 = judge_pair(row["question"], row["ground_truth"], answer_a, answer_b)
            run2_swapped = judge_pair(row["question"], row["ground_truth"], answer_b, answer_a)
        run2_normalized = flip_winner(str(run2_swapped["winner"]))
        final = aggregate(str(run1["winner"]), run2_normalized)

        judge_accuracy = str(run1["winner"])
        judge_concise = "A" if len(answer_a) <= len(answer_b) * 1.15 else ("B" if len(answer_b) < len(answer_a) * 0.85 else final)
        cross = aggregate(judge_accuracy, judge_concise)

        out.append(
            {
                "question_id": idx,
                "question": row["question"],
                "answer_a": answer_a,
                "answer_b": answer_b,
                "run1_winner": run1["winner"],
                "run2_raw_winner": run2_swapped["winner"],
                "run2_winner_normalized": run2_normalized,
                "winner_after_swap": final,
                "judge_accuracy_winner": judge_accuracy,
                "judge_concise_winner": judge_concise,
                "cross_judge_winner": cross,
                "run1_score_a": run1["score_a"],
                "run1_score_b": run1["score_b"],
                "len_a": len(answer_a),
                "len_b": len(answer_b),
                "reason": run1["reason"],
                "judge_mode": mode,
            }
        )
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--openai", action="store_true")
    parser.add_argument("--require-openai", action="store_true")
    args = parser.parse_args()
    rows = run(args.limit, use_openai=args.openai, require_openai=args.require_openai)
    suffix = "_sample" if args.limit else ""
    write_csv(ROOT / "phase-b" / f"pairwise_results{suffix}.csv", rows)
    print(f"Wrote {len(rows)} pairwise rows")


if __name__ == "__main__":
    main()
