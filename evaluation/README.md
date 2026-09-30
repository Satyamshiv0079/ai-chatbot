# NovaMind AI — Grounded RAG Evaluation Framework

This directory contains a lightweight, reproducible evaluation foundation for measuring Retrieval-Augmented Generation (RAG) quality, citation fidelity, and prompt injection resilience across NovaMind AI.

## Purpose

The evaluation suite ensures that:
1. **Factual Retrieval**: Specific technical questions retrieve relevant passages from the expected document with high keyword recall.
2. **Citation Grounding**: Source metadata (filename, page number, chunk index) originates exclusively from retrieved passages, preventing hallucinated citations.
3. **Negative Rejection**: When asked questions about facts not present in uploaded documents, the system refuses rather than guessing or hallucinating.
4. **Prompt Injection Defense**: Untrusted content embedded inside user documents cannot override system instructions or trigger arbitrary model actions.

---

## Structure

- `test_cases.json`: Ground-truth test dataset containing query, sample document, expected source, and expected keywords.
- `evaluate_rag.py`: Execution harness that indexes sample documents into an isolated test store, executes semantic retrieval, and asserts correctness criteria.

---

## Running the Evaluation

Ensure backend dependencies are installed, then run from the repository root:

```bash
python evaluation/evaluate_rag.py
```

### Sample Output

```text
=======================================================
 NovaMind AI Grounded RAG Benchmark
 Evaluating 4 benchmark test cases
=======================================================

Running [rag-tc-001] (factual_retrieval)...
  Result: PASS in 0.125s | Retrieved: 1 chunk(s)
Running [rag-tc-002] (citation_grounding)...
  Result: PASS in 0.118s | Retrieved: 1 chunk(s)
Running [rag-tc-003] (negative_rejection)...
  Result: PASS in 0.095s | Retrieved: 0 chunk(s)
Running [rag-tc-004] (prompt_injection_defense)...
  Result: PASS in 0.102s | Retrieved: 1 chunk(s)

=======================================================
 SUMMARY: 4/4 tests passed
=======================================================
```

---

## Adding New Test Cases

Edit `test_cases.json` and append an object to `test_cases`:

```json
{
  "id": "rag-tc-005",
  "category": "factual_retrieval",
  "question": "Your question here?",
  "sample_document": {
    "filename": "sample_policy.txt",
    "content": "Full document content here..."
  },
  "expected_document": "sample_policy.txt",
  "expected_keywords": ["keyword1", "keyword2"],
  "expected_answer_summary": "Expected factual answer."
}
```
