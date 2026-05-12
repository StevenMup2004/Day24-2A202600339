# Failure Cluster Analysis

This analysis uses the bottom 10 questions by average score across the four RAGAS-style metrics.

## Bottom 10 Questions

| # | Question | Type | F | AR | CP | CR | Avg | Cluster |
|---:|---|---|---:|---:|---:|---:|---:|---|
| 1 | Hình ảnh của cá nhân thuộc loại dữ liệu nào? | simple | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | C3: answer grounding gap |
| 2 | Nguyên tắc nào yêu cầu dữ liệu phải thu thập phù hợp, giới hạn? | simple | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | C3: answer grounding gap |
| 3 | Bên kiểm soát phải thực hiện yêu cầu phản đối xử lý dữ liệu trong bao lâu? | simple | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | C3: answer grounding gap |
| 4 | Một nghĩa vụ của chủ thể dữ liệu theo Điều 10 là gì? | simple | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | C3: answer grounding gap |
| 5 | Việc cung cấp dữ liệu cá nhân cho chủ thể dữ liệu phải thực hiện trong bao lâu? | simple | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | C3: answer grounding gap |
| 6 | Chủ thể dữ liệu có quyền phản đối xử lý dữ liệu để làm gì? | simple | 0.80 | 0.80 | 0.70 | 0.60 | 0.72 | C4: missing evidence / multi-hop context gap |
| 7 | Xử lý dữ liệu cá nhân gồm những hoạt động nào? | simple | 0.80 | 0.90 | 0.70 | 0.90 | 0.82 | C1: retrieval dilution / irrelevant chunks |
| 8 | Dữ liệu cá nhân có được mua bán không? | simple | 0.90 | 0.90 | 0.80 | 0.80 | 0.85 | C1: retrieval dilution / irrelevant chunks |
| 9 | Nếu answer relevancy thấp nhưng faithfulness cao, lỗi có thể nằm ở đâu? | reasoning | 1.00 | 0.50 | 1.00 | 1.00 | 0.88 | C2: answer does not directly address question |
| 10 | Nghị định 13/2023/ND-CP quy định về nội dung gì? | simple | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | C3: answer grounding gap |

## Clusters Identified

### C3: answer grounding gap

**Pattern:** 6 of the bottom 10 questions share this failure mode.
When a cluster has only one direct item, the second example is the next-lowest scoring question on the associated metric.

**Examples:**
- Hình ảnh của cá nhân thuộc loại dữ liệu nào?
- Nguyên tắc nào yêu cầu dữ liệu phải thu thập phù hợp, giới hạn?

**Root cause:** weakest metric is usually `faithfulness`.
**Proposed fix:** Tighten answer prompt, lower temperature, and require citations from retrieved context.

### C4: missing evidence / multi-hop context gap

**Pattern:** 1 of the bottom 10 questions share this failure mode.
When a cluster has only one direct item, the second example is the next-lowest scoring question on the associated metric.

**Examples:**
- Chủ thể dữ liệu có quyền phản đối xử lý dữ liệu để làm gì?
- Bên kiểm soát phải thực hiện yêu cầu phản đối xử lý dữ liệu trong bao lâu?

**Root cause:** weakest metric is usually `context_recall`.
**Proposed fix:** Increase top_k, add BM25 + vector hybrid search, and test multi-context retrieval.

### C1: retrieval dilution / irrelevant chunks

**Pattern:** 2 of the bottom 10 questions share this failure mode.
When a cluster has only one direct item, the second example is the next-lowest scoring question on the associated metric.

**Examples:**
- Xử lý dữ liệu cá nhân gồm những hoạt động nào?
- Dữ liệu cá nhân có được mua bán không?

**Root cause:** weakest metric is usually `context_precision`.
**Proposed fix:** Increase reranker weight, add metadata filters, or reduce noisy enriched text.

### C2: answer does not directly address question

**Pattern:** 1 of the bottom 10 questions share this failure mode.
When a cluster has only one direct item, the second example is the next-lowest scoring question on the associated metric.

**Examples:**
- Nếu answer relevancy thấp nhưng faithfulness cao, lỗi có thể nằm ở đâu?
- Một nghĩa vụ của chủ thể dữ liệu theo Điều 10 là gì?

**Root cause:** weakest metric is usually `answer_relevancy`.
**Proposed fix:** Rewrite generation prompt to answer the user question first, then add supporting detail.

## Next Actions

1. Re-run retrieval with higher `top_k` on multi-context questions.
2. Add a reranker or metadata filter for queries with low context precision.
3. Keep this bottom-10 set as a regression suite for the CI eval gate.
