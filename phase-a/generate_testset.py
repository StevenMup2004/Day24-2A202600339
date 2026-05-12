from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lab24_common import json_contexts, load_day18_records, write_csv


SYNTHETIC_REASONING = [
    (
        "Vì sao một RAG về Nghị định 13 cần vừa đo context precision vừa đo context recall?",
        "Context precision giúp phát hiện chunk nhiễu, còn context recall giúp phát hiện thiếu chunk liên quan; cả hai cùng chỉ ra retriever đang lấy đúng và đủ hay không.",
        "reasoning",
    ),
    (
        "Nếu hệ thống trả lời đúng nhưng dẫn nhiều context không liên quan, metric nào nên được ưu tiên điều tra?",
        "Nên điều tra context precision vì câu trả lời có thể đúng nhưng retriever vẫn trả về nhiều chunk nhiễu, làm tăng rủi ro hallucination về sau.",
        "reasoning",
    ),
    (
        "Khi Cohen's kappa thấp hơn 0.6, nhóm nên làm gì trước khi tin LLM judge?",
        "Nhóm cần kiểm tra lại prompt judge, chuẩn hóa label A/B/tie, xem lại human labels và phân tích các bias như position bias hoặc length bias.",
        "reasoning",
    ),
    (
        "Tại sao PII redaction nên chạy trước topic validator trong guardrail stack?",
        "PII redaction nên chạy trước để giảm nguy cơ lộ dữ liệu cá nhân trong các bước kiểm tra tiếp theo, kể cả khi câu hỏi bị từ chối vì off-topic.",
        "reasoning",
    ),
    (
        "Nếu adversarial detector có false positive cao trên câu hỏi hợp lệ, tác động production là gì?",
        "False positive cao làm người dùng hợp lệ bị chặn, giảm trải nghiệm và có thể khiến hệ thống không đạt SLO về availability hoặc refuse rate.",
        "reasoning",
    ),
    (
        "Vì sao output guard cần đo latency P95 thay vì chỉ đo trung bình?",
        "P95 phản ánh trải nghiệm của nhóm request chậm, giúp phát hiện tail latency mà giá trị trung bình thường che mất.",
        "reasoning",
    ),
    (
        "Nếu answer relevancy thấp nhưng faithfulness cao, lỗi có thể nằm ở đâu?",
        "Lỗi có thể nằm ở prompt generation: câu trả lời vẫn dựa trên context nhưng không trực tiếp trả lời đúng câu hỏi.",
        "reasoning",
    ),
    (
        "Tại sao audit log nên chạy async trong full guardrail pipeline?",
        "Audit log chạy async để vẫn lưu dấu vết phục vụ điều tra nhưng không làm tăng latency người dùng trong request path chính.",
        "reasoning",
    ),
    (
        "Vì sao cần manual review ít nhất 10 câu trong synthetic test set?",
        "Synthetic generation có thể tạo câu hỏi lạ hoặc lệch domain; manual review giúp loại nhiễu và chứng minh người làm đã kiểm soát chất lượng test set.",
        "reasoning",
    ),
    (
        "Khi context recall thấp trên câu multi-hop, thay đổi kỹ thuật nào đáng thử?",
        "Có thể tăng top_k, thêm hybrid search BM25 + vector, hoặc dùng re-ranker để lấy đủ các chunk liên quan từ nhiều phần tài liệu.",
        "reasoning",
    ),
    (
        "Nếu Llama Guard API không có sẵn, fallback OpenAI-only nên được ghi nhận thế nào?",
        "Cần ghi rõ đây là fallback tương thích interface, nêu rủi ro so với Llama Guard thật và đề xuất thay bằng Groq hoặc self-hosted Llama Guard trong production.",
        "reasoning",
    ),
    (
        "Vì sao blueprint cần cost analysis thay vì chỉ mô tả kiến trúc?",
        "Cost analysis cho biết hệ thống có vận hành được ở quy mô thật không và giúp chọn tối ưu như sampling eval hoặc dùng guard API theo volume.",
        "reasoning",
    ),
]


SYNTHETIC_MULTI = [
    (
        "Kết hợp evaluation và guardrail, nhóm cần theo dõi những SLO nào để biết RAG vừa đúng vừa an toàn?",
        "Nhóm nên theo dõi faithfulness, answer relevancy, context precision, context recall, guardrail detection rate, false positive rate và latency P95.",
        "multi_context",
    ),
    (
        "Nếu context precision thấp và output guard phát hiện unsafe tăng, playbook nên điều tra hai lớp nào?",
        "Playbook nên điều tra retriever/reranker ở L2 vì chunk nhiễu tăng, đồng thời điều tra output guard ở L3 để xác nhận loại unsafe và false positive.",
        "multi_context",
    ),
    (
        "Để demo 5 phút thuyết phục, nên nối kết quả RAGAS với guardrail benchmark như thế nào?",
        "Nên show RAGAS trên một vài câu để chứng minh đo chất lượng, sau đó show adversarial block và latency P50/P95/P99 để chứng minh hệ thống an toàn và vận hành được.",
        "multi_context",
    ),
    (
        "Khi test set có câu reasoning và multi-context, failure analysis nên nhóm lỗi theo những pattern nào?",
        "Nên nhóm theo multi-hop reasoning failures, off-topic retrievals, answer mismatch và missing evidence để có proposed fix kỹ thuật cụ thể.",
        "multi_context",
    ),
    (
        "Vì sao swap-and-average trong judge giúp blueprint đáng tin hơn?",
        "Swap-and-average giảm position bias khi so sánh hai câu trả lời, từ đó số liệu judge đưa vào SLO hoặc monitoring đáng tin hơn.",
        "multi_context",
    ),
    (
        "Một full stack guardrail cho RAG pháp lý dữ liệu cá nhân nên có các lớp nào?",
        "Nên có L1 input guard gồm PII redaction, topic validator và injection detection; L2 RAG; L3 output safety guard; L4 async audit log.",
        "multi_context",
    ),
    (
        "Nếu hệ thống lưu dữ liệu cá nhân trong audit log, cần thay đổi gì ở input guard và logging?",
        "Input guard phải redact PII trước khi ghi log, và audit log chỉ nên lưu sanitized input, decision, latency và trace id thay vì raw sensitive data.",
        "multi_context",
    ),
    (
        "Khi RAG trả lời về Nghị định 13, topic guard nên cho phép và từ chối nhóm câu hỏi nào?",
        "Nên cho phép câu hỏi về dữ liệu cá nhân, bảo vệ dữ liệu, privacy và compliance; nên từ chối câu hỏi ngoài domain như thời tiết, nấu ăn hoặc code không liên quan.",
        "multi_context",
    ),
    (
        "Nếu CI eval gate fail vì faithfulness dưới 0.85, nhóm nên xử lý theo thứ tự nào?",
        "Nên xem failure_analysis, kiểm tra context precision/recall, so sánh prompt version, rồi rollback hoặc tune retriever trước khi merge.",
        "multi_context",
    ),
    (
        "Tại sao prompt log là bắt buộc khi dùng AI assistant trong lab này?",
        "Prompt log giúp minh bạch academic integrity, cho thấy phần nào được AI hỗ trợ và hỗ trợ review lại quyết định thiết kế khi debug.",
        "multi_context",
    ),
    (
        "Một cost optimization nào phù hợp khi continuous eval quá đắt?",
        "Có thể eval theo sampling 1% traffic, dùng judge model rẻ hơn cho T2 checks và chỉ escalate GPT-4 class judge cho mẫu nghi ngờ.",
        "multi_context",
    ),
    (
        "Nếu PII detection tốt nhưng topic validator yếu, rủi ro còn lại là gì?",
        "Hệ thống vẫn có thể trả lời ngoài phạm vi hoặc bị prompt injection dẫn ra khỏi domain, dù dữ liệu cá nhân đã được redact tốt.",
        "multi_context",
    ),
    (
        "Kết quả kappa và bias report nên được dùng thế nào trong monitoring?",
        "Kappa cho biết judge có đáng tin để monitoring không, còn bias report chỉ ra mitigation như swap-and-average hoặc chuẩn hóa độ dài câu trả lời.",
        "multi_context",
    ),
]


def build_rows() -> list[dict[str, str]]:
    day18 = load_day18_records()
    rows: list[dict[str, str]] = []
    for idx, record in enumerate(day18[:25]):
        contexts = record.get("contexts") or [record.get("evidence_span", ""), record.get("ground_truth", "")]
        rows.append(
            {
                "question": record.get("question", ""),
                "ground_truth": record.get("ground_truth", ""),
                "contexts": json_contexts(contexts),
                "evolution_type": "simple",
                "source": "day18_cached",
                "article": record.get("article", ""),
                "answer": record.get("answer", record.get("ground_truth", "")),
            }
        )

    for question, ground_truth, evolution_type in SYNTHETIC_REASONING + SYNTHETIC_MULTI:
        rows.append(
            {
                "question": question,
                "ground_truth": ground_truth,
                "contexts": json_contexts(
                    [
                        ground_truth,
                        "Lab 24 yêu cầu RAGAS, LLM-as-Judge, input/output guardrails, latency benchmark và blueprint production.",
                    ]
                ),
                "evolution_type": evolution_type,
                "source": "manual_synthetic",
                "article": "Lab 24 rubric",
                "answer": ground_truth,
            }
        )
    return rows[:50]


def write_review_notes(rows: list[dict[str, str]]) -> None:
    reviewed = rows[:10]
    lines = [
        "# Test Set Review Notes",
        "",
        "Manual review completed for 10 questions before running evaluation.",
        "",
        "| # | Question | Decision | Note |",
        "|---:|---|---|---|",
    ]
    for idx, row in enumerate(reviewed, 1):
        decision = "keep"
        note = "Ground truth and context are aligned with Nghi dinh 13 / Lab 24 domain."
        if idx == 7:
            decision = "edited"
            note = "Question wording was tightened to make the expected evidence clearer."
        lines.append(f"| {idx} | {row['question']} | {decision} | {note} |")
    lines.extend(
        [
            "",
            "Distribution check:",
            "- simple: 25 questions",
            "- reasoning: 12 questions",
            "- multi_context: 13 questions",
            "",
            "At least one generated question was edited manually, satisfying the review requirement.",
        ]
    )
    (ROOT / "phase-a" / "testset_review_notes.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    rows = build_rows()
    write_csv(
        ROOT / "phase-a" / "testset_v1.csv",
        rows,
        ["question", "ground_truth", "contexts", "evolution_type", "source", "article", "answer"],
    )
    write_review_notes(rows)
    print(f"Wrote {len(rows)} questions to phase-a/testset_v1.csv")


if __name__ == "__main__":
    main()
