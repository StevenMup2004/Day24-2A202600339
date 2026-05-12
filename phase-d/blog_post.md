# From "RAG Works" To "RAG Is Measured"

This lab turned a Day18 RAG pipeline into a more production-shaped system. The main lesson is that a demo answer is not enough: the system needs quality metrics, judge calibration, safety checks and latency numbers.

The evaluation layer uses a 50-question test set and OpenAI-backed RAGAS-compatible scoring for faithfulness, answer relevancy, context precision and context recall. The current run clears the target on all four metrics. The most useful artifact is not only the score table, but the failure analysis: bottom questions show whether the fix belongs in retrieval, reranking, prompting or corpus cleanup.

The LLM-as-Judge layer compares the production RAG answer with a baseline answer. To reduce position bias, each pair is judged twice with the answer order swapped. Disagreements become ties instead of forced wins. A small human calibration set then computes Cohen's kappa so the judge can be trusted for monitoring only when it agrees with human labels.

The guardrail stack uses defense in depth. L1 redacts Vietnamese PII, validates topic scope and blocks common jailbreak patterns. L2 runs the RAG answer. L3 classifies output safety through an OpenAI safety classifier with the same `safe/unsafe` interface expected from Llama Guard. L4 writes async audit logs. The benchmark shows the local L1 checks are tiny, while network output safety dominates tail latency.

The biggest production risk is the output guard implementation. OpenAI is acceptable for this OpenAI-only submission, but exact parity with the lab's Llama Guard 3 requirement should use Groq or a self-hosted Llama Guard model. The architecture keeps that replacement isolated in `phase-c/output_guard.py`.

The practical takeaway: evaluation catches quality failures after they happen, guardrails reduce the chance users see unsafe failures, and monitoring connects both to operations. A production RAG system needs all three.
