# Enterprise University RAG - Quality Evaluation Report

**Generated:** 2026-09-03 17:17:27 UTC

## 1. Summary Scorecard

| Metric | Result | Quality SLO Target | Status |
| :--- | :--- | :--- | :--- |
| **Retrieval Hit Rate** | 100.0% | $\ge 90\%$ | 🟢 PASS |
| **Citation Precision** | 100.0% | $\ge 85\%$ | 🟢 PASS |
| **Abstention Accuracy** | 100.0% | $100\%$ | 🟢 PASS |
| **Overall Accuracy** | 100.0% | $\ge 90\%$ | 🟢 PASS |

## 2. Test Case Breakdown

| ID | Question | Expected Doc | Result | Latency |
| :--- | :--- | :--- | :--- | :--- |
| `eval_01` | What is an AVL tree and what is its reba... | Doc match | PASS | 187207.5ms |
| `eval_02` | When are the instructor office hours for... | Doc match | PASS | 53576.9ms |
| `eval_03` | What are the five design principles behi... | Doc match | PASS | 404233.0ms |
| `eval_04` | How does Reciprocal Rank Fusion work in ... | Doc match | PASS | 6988.3ms |
| `eval_05_neg` | What was the capital city of ancient Atl... | [Abstain] | PASS | 30898.9ms |
| `eval_06_neg` | What is the secret recipe for immortalit... | [Abstain] | PASS | 55072.8ms |
| `eval_07_neg` | Who won the men's Olympic marathon in Pa... | [Abstain] | PASS | 398143.6ms |
