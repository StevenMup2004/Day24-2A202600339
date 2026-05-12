from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lab24_common import read_csv, write_json

LABELS = ["A", "B", "tie"]


def normalize_label(value: str) -> str:
    label = value.strip()
    if label.lower() == "tie":
        return "tie"
    label = label.upper()
    if label not in {"A", "B"}:
        raise ValueError(f"Invalid label {value!r}; expected A, B, or tie")
    return label


def cohen_kappa(a: list[str], b: list[str]) -> float:
    n = len(a)
    if n == 0:
        return 0.0
    observed = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    expected = sum((ca[label] / n) * (cb[label] / n) for label in LABELS)
    if expected == 1:
        return 1.0
    return round((observed - expected) / (1 - expected), 4)


def interpretation(kappa: float) -> str:
    if kappa < 0:
        return "worse than chance"
    if kappa < 0.2:
        return "slight agreement"
    if kappa < 0.4:
        return "fair agreement"
    if kappa < 0.6:
        return "moderate agreement"
    if kappa < 0.8:
        return "substantial agreement"
    return "almost perfect agreement"


def main() -> None:
    pairwise_path = ROOT / "phase-b" / "pairwise_results.csv"
    if not pairwise_path.exists():
        import pairwise_judge

        pairwise_judge.main()
    pairwise = read_csv(pairwise_path)

    labels_path = ROOT / "phase-b" / "human_labels.csv"
    if not labels_path.exists():
        raise FileNotFoundError(
            "phase-b/human_labels.csv is required. Create at least 10 rows with "
            "question_id,human_winner,confidence,notes before running kappa analysis."
        )

    pairwise_by_id = {row["question_id"]: row for row in pairwise}
    labels = read_csv(labels_path)
    if len(labels) < 10:
        raise ValueError("At least 10 human labels are required for calibration.")

    paired = []
    for label_row in labels[:10]:
        question_id = label_row.get("question_id", "").strip()
        if question_id not in pairwise_by_id:
            raise ValueError(f"Human label question_id={question_id!r} is not present in pairwise_results.csv")
        human_label = normalize_label(label_row.get("human_winner", ""))
        judge_label = normalize_label(pairwise_by_id[question_id].get("winner_after_swap", "tie"))
        paired.append(
            {
                "question_id": question_id,
                "human_winner": human_label,
                "judge_winner": judge_label,
                "agreement": human_label == judge_label,
                "confidence": label_row.get("confidence", ""),
                "notes": label_row.get("notes", ""),
            }
        )

    human = [row["human_winner"] for row in paired]
    judge = [row["judge_winner"] for row in paired]
    kappa = cohen_kappa(human, judge)
    disagreements = [row for row in paired if not row["agreement"]]
    payload = {
        "num_labels": len(paired),
        "cohen_kappa": kappa,
        "interpretation": interpretation(kappa),
        "label_source": "phase-b/human_labels.csv",
        "label_source_note": "Human labels are treated as a reviewed input artifact; this script no longer generates them from judge output.",
        "judge_source": "phase-b/pairwise_results.csv:winner_after_swap",
        "agreements": sum(1 for row in paired if row["agreement"]),
        "disagreements": len(disagreements),
        "disagreement_question_ids": [row["question_id"] for row in disagreements],
    }
    write_json(ROOT / "phase-b" / "kappa_analysis.json", payload)

    md = [
        "# Cohen's Kappa Analysis",
        "",
        f"- Samples: {payload['num_labels']}",
        f"- Cohen's kappa: {payload['cohen_kappa']}",
        f"- Interpretation: {payload['interpretation']}",
        f"- Agreements: {payload['agreements']}",
        f"- Disagreements: {payload['disagreements']}",
        f"- Label source: `{payload['label_source']}`",
        "",
        "Human labels are loaded from the checked-in label file instead of being generated from judge output.",
    ]
    if disagreements:
        md.extend(
            [
                "",
                "## Disagreements",
                "",
                "| Question ID | Human | Judge | Notes |",
                "|---:|---|---|---|",
            ]
        )
        for row in disagreements:
            note = str(row["notes"]).replace("|", " ")
            md.append(f"| {row['question_id']} | {row['human_winner']} | {row['judge_winner']} | {note} |")
    (ROOT / "phase-b" / "kappa_analysis.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    notebook = {
        "cells": [
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": ["# Cohen's Kappa Analysis\n", json.dumps(payload, ensure_ascii=False, indent=2)],
            }
        ],
        "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}},
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    (ROOT / "phase-b" / "kappa_analysis.ipynb").write_text(json.dumps(notebook, ensure_ascii=False, indent=2), encoding="utf-8")
    print(payload)


if __name__ == "__main__":
    main()
