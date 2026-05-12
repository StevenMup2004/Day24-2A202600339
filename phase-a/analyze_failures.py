from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lab24_common import read_csv

METRICS = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]


DIAGNOSIS = {
    "faithfulness": (
        "C3: answer grounding gap",
        "Tighten answer prompt, lower temperature, and require citations from retrieved context.",
    ),
    "answer_relevancy": (
        "C2: answer does not directly address question",
        "Rewrite generation prompt to answer the user question first, then add supporting detail.",
    ),
    "context_precision": (
        "C1: retrieval dilution / irrelevant chunks",
        "Increase reranker weight, add metadata filters, or reduce noisy enriched text.",
    ),
    "context_recall": (
        "C4: missing evidence / multi-hop context gap",
        "Increase top_k, add BM25 + vector hybrid search, and test multi-context retrieval.",
    ),
}

CLUSTER_METRIC = {cluster: metric for metric, (cluster, _fix) in DIAGNOSIS.items()}


def main() -> None:
    path = ROOT / "phase-a" / "ragas_results.csv"
    if not path.exists():
        import run_ragas_eval

        run_ragas_eval.main()
    rows = read_csv(path)
    for row in rows:
        row["avg_score"] = float(row["avg_score"])
    bottom = sorted(rows, key=lambda r: r["avg_score"])[:10]

    clusters: dict[str, list[dict[str, str]]] = defaultdict(list)
    examples_by_cluster: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in sorted(rows, key=lambda r: r["avg_score"]):
        worst_metric = min(METRICS, key=lambda m: float(row[m]))
        cluster, fix = DIAGNOSIS[worst_metric]
        row["worst_metric"] = worst_metric
        row["cluster"] = cluster
        row["proposed_fix"] = fix
        examples_by_cluster[cluster].append(row)

    for row in bottom:
        clusters[row["cluster"]].append(row)

    lines = [
        "# Failure Cluster Analysis",
        "",
        "This analysis uses the bottom 10 questions by average score across the four RAGAS-style metrics.",
        "",
        "## Bottom 10 Questions",
        "",
        "| # | Question | Type | F | AR | CP | CR | Avg | Cluster |",
        "|---:|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for idx, row in enumerate(bottom, 1):
        q = row["question"].replace("|", " ")[:90]
        lines.append(
            f"| {idx} | {q} | {row['evolution_type']} | {float(row['faithfulness']):.2f} | "
            f"{float(row['answer_relevancy']):.2f} | {float(row['context_precision']):.2f} | "
            f"{float(row['context_recall']):.2f} | {float(row['avg_score']):.2f} | {row['cluster']} |"
        )

    lines.extend(["", "## Clusters Identified", ""])
    used_example_questions: set[str] = set()
    for cluster, items in clusters.items():
        metric = CLUSTER_METRIC[cluster]
        candidate_examples = examples_by_cluster[cluster] + sorted(rows, key=lambda r: (float(r[metric]), r["avg_score"]))
        selected_examples = []
        for row in candidate_examples:
            if row["question"] in used_example_questions:
                continue
            selected_examples.append(row)
            used_example_questions.add(row["question"])
            if len(selected_examples) >= 2:
                break
        if len(selected_examples) < 2:
            for row in candidate_examples:
                if row in selected_examples:
                    continue
                selected_examples.append(row)
                if len(selected_examples) >= 2:
                    break

        lines.extend(
            [
                f"### {cluster}",
                "",
                f"**Pattern:** {len(items)} of the bottom 10 questions share this failure mode.",
                "When a cluster has only one direct item, the second example is the next-lowest scoring question on the associated metric.",
                "",
                "**Examples:**",
            ]
        )
        for row in selected_examples[:2]:
            lines.append(f"- {row['question']}")
        lines.extend(
            [
                "",
                f"**Root cause:** weakest metric is usually `{items[0]['worst_metric']}`.",
                f"**Proposed fix:** {items[0]['proposed_fix']}",
                "",
            ]
        )

    lines.extend(
        [
            "## Next Actions",
            "",
            "1. Re-run retrieval with higher `top_k` on multi-context questions.",
            "2. Add a reranker or metadata filter for queries with low context precision.",
            "3. Keep this bottom-10 set as a regression suite for the CI eval gate.",
        ]
    )
    out = ROOT / "phase-a" / "failure_analysis.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
