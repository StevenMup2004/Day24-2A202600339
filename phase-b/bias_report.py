from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lab24_common import read_csv


def pct(n: int, d: int) -> float:
    return round(100 * n / d, 1) if d else 0.0


def main() -> None:
    path = ROOT / "phase-b" / "pairwise_results.csv"
    if not path.exists():
        import pairwise_judge

        pairwise_judge.main()
    rows = read_csv(path)
    total = len(rows)
    a_first_wins = sum(1 for r in rows if r["run1_winner"] == "A")
    b_first_wins = sum(1 for r in rows if r["run2_raw_winner"] == "A")
    disagreements = sum(1 for r in rows if r["run1_winner"] != r["run2_winner_normalized"])
    longer_wins = 0
    longer_total = 0
    for r in rows:
        len_a, len_b = int(r["len_a"]), int(r["len_b"])
        winner = r["winner_after_swap"]
        if abs(len_a - len_b) < 40 or winner == "tie":
            continue
        longer_total += 1
        if (len_a > len_b and winner == "A") or (len_b > len_a and winner == "B"):
            longer_wins += 1

    cross_ties = sum(1 for r in rows if r["cross_judge_winner"] == "tie")
    lines = [
        "# Judge Bias Report",
        "",
        "## Summary",
        "",
        f"- Pairwise comparisons: {total}",
        f"- A wins when listed first: {a_first_wins}/{total} ({pct(a_first_wins, total)}%)",
        f"- First-position wins after swap run: {b_first_wins}/{total} ({pct(b_first_wins, total)}%)",
        f"- Swap disagreement rate: {disagreements}/{total} ({pct(disagreements, total)}%)",
        f"- Longer answer win rate: {longer_wins}/{longer_total} ({pct(longer_wins, longer_total)}%)",
        f"- Cross-judge tie/escalation rate: {cross_ties}/{total} ({pct(cross_ties, total)}%)",
        "",
        "## Bias 1: Position Bias",
        "",
        "The judge was run twice for each pair: original order and swapped order. The swapped result was normalized back to A/B before aggregation.",
        "",
        "| Metric | Value | Interpretation |",
        "|---|---:|---|",
        f"| A-first win rate | {pct(a_first_wins, total)}% | Expected near content quality, not necessarily 50% because A is the production answer. |",
        f"| Swap disagreement rate | {pct(disagreements, total)}% | Disagreements are converted to tie to avoid overclaiming. |",
        "",
        "Mitigation: keep swap-and-average for production monitoring and send ties to human review or a stronger judge.",
        "",
        "## Bias 2: Length Bias",
        "",
        "| Metric | Value | Interpretation |",
        "|---|---:|---|",
        f"| Longer answer win rate | {pct(longer_wins, longer_total)}% | Values far above 55% would suggest length bias. |",
        "",
        "Mitigation: score conciseness independently and cap answer length in the production prompt.",
        "",
        "## Bonus: Cross-Judge Protocol",
        "",
        "This repo implements a lightweight cross-judge protocol: an accuracy-first judge and a conciseness-aware judge. If they disagree, the aggregate winner is `tie`, which is safer for monitoring than forcing a winner.",
        "",
        "## Production Decision",
        "",
        "Use pairwise judge for regression detection, not as the only source of truth. Keep human calibration weekly and re-run Cohen's kappa whenever the prompt or model changes.",
    ]
    out = ROOT / "phase-b" / "judge_bias_report.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
