# 5-Minute Demo Script

## 0:00-1:00 RAGAS-Compatible Evaluation

Run:

```powershell
python phase-a/run_ragas_eval.py --limit 5 --require-openai
```

Show:

- `phase-a/ragas_results_sample.csv`
- `phase-a/ragas_summary_sample.json`
- Main run summary: F 0.890, AR 0.882, CP 0.884, CR 0.886 on 50 questions.

## 1:00-2:00 LLM-as-Judge

Run:

```powershell
python phase-b/pairwise_judge.py --limit 5 --require-openai
```

Show:

- `phase-b/pairwise_results_sample.csv`
- swap-and-average columns: `run1_winner`, `run2_winner_normalized`, `winner_after_swap`
- `phase-b/judge_bias_report.md`

## 2:00-4:00 Guardrail Attack Tests

Run:

```powershell
python phase-c/input_guard.py
python phase-c/output_guard.py --require-openai
```

Show:

- PII redaction examples in `phase-c/pii_test_results.csv`
- DAN/jailbreak blocks in `phase-c/adversarial_test_results.csv`
- OpenAI output safety classifier in `phase-c/output_guard_results.csv`

## 4:00-5:00 Latency Benchmark

Run:

```powershell
python phase-c/full_pipeline.py --benchmark 20 --openai-output-guard
```

Show:

- `phase-c/latency_summary.json`
- Existing 100-request benchmark: P50 1495.346 ms, P95 2317.918 ms, P99 2912.119 ms.

Close with:

- CI eval gate: `.github/workflows/eval-gate.yml`
- Production blueprint: `phase-d/blueprint.md`
