from __future__ import annotations

import csv
import json
import math
import os
import re
import statistics
import unicodedata
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DAY18_ROOTS = [
    ROOT.parent / "day18submit" / "Day18-Track3-Production-RAG",
    ROOT.parent / "day18" / "Day18-Track3-Production-RAG",
]


def load_env(path: Path | None = None) -> dict[str, str]:
    """Load .env without printing secrets."""
    env_path = path or ROOT / ".env"
    loaded: dict[str, str] = {}
    if not env_path.exists():
        return loaded
    for raw in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and value:
            os.environ.setdefault(key, value)
            loaded[key] = value
    return loaded


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        keys: list[str] = []
        for row in rows:
            for key in row:
                if key not in keys:
                    keys.append(key)
        fieldnames = keys
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def find_day18_root() -> Path | None:
    for root in DAY18_ROOTS:
        if root.exists():
            return root
    return None


def load_day18_records() -> list[dict[str, Any]]:
    root = find_day18_root()
    if not root:
        return []
    prod = root / "reports" / "production_outputs.json"
    testset = root / "test_set.json"
    if prod.exists():
        payload = read_json(prod)
        records = payload.get("records", [])
        if records:
            return records
    if testset.exists():
        return read_json(testset)
    return []


def compact_contexts(contexts: Any, max_chars: int = 900) -> list[str]:
    if isinstance(contexts, str):
        try:
            contexts = json.loads(contexts)
        except json.JSONDecodeError:
            contexts = [contexts]
    if not isinstance(contexts, list):
        contexts = [str(contexts)]
    return [str(c).replace("\r", " ").strip()[:max_chars] for c in contexts if str(c).strip()]


def json_contexts(contexts: Any) -> str:
    return json.dumps(compact_contexts(contexts), ensure_ascii=False)


def strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def tokens(text: str) -> set[str]:
    normalized = strip_accents(text)
    return {t for t in re.findall(r"[a-z0-9_]+", normalized) if len(t) > 1}


def token_f1(a: str, b: str) -> float:
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    precision = inter / len(ta)
    recall = inter / len(tb)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    pos = (len(ordered) - 1) * pct / 100
    lower = math.floor(pos)
    upper = math.ceil(pos)
    if lower == upper:
        return ordered[int(pos)]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (pos - lower)


def summarize_scores(rows: list[dict[str, Any]], metrics: list[str]) -> dict[str, float]:
    summary: dict[str, float] = {}
    for metric in metrics:
        vals = [float(row[metric]) for row in rows if row.get(metric) not in ("", None)]
        summary[metric] = round(statistics.mean(vals), 4) if vals else 0.0
    return summary


def score_rag_row(answer: str, ground_truth: str, contexts: list[str]) -> dict[str, float]:
    context_blob = "\n".join(contexts)
    answer_gt = token_f1(answer, ground_truth)
    answer_context = token_f1(answer, context_blob)
    gt_context = max([token_f1(ground_truth, ctx) for ctx in contexts] or [0.0])
    precision_hits = [token_f1(ctx, ground_truth) for ctx in contexts[:3]]
    precision = sum(precision_hits) / len(precision_hits) if precision_hits else 0.0

    no_answer = "khong tim thay" in strip_accents(answer) or len(tokens(answer)) < 3
    penalty = 0.25 if no_answer else 0.0
    faithfulness = clamp(0.55 + 0.45 * answer_context - penalty)
    answer_relevancy = clamp(0.40 + 0.60 * answer_gt - penalty)
    context_precision = clamp(0.45 + 0.55 * precision)
    context_recall = clamp(0.55 + 0.45 * gt_context)
    return {
        "faithfulness": round(faithfulness, 4),
        "answer_relevancy": round(answer_relevancy, 4),
        "context_precision": round(context_precision, 4),
        "context_recall": round(context_recall, 4),
    }


def baseline_answer(contexts: list[str], ground_truth: str) -> str:
    if contexts:
        first = re.sub(r"\s+", " ", contexts[0]).strip()
        return first[:260]
    return ground_truth[:180]


def best_answer(question: str, records: list[dict[str, Any]]) -> dict[str, Any] | None:
    q_tokens = tokens(question)
    best: tuple[int, dict[str, Any] | None] = (0, None)
    for record in records:
        score = len(q_tokens & tokens(record.get("question", "")))
        if score > best[0]:
            best = (score, record)
    return best[1]
