# API Contract Reference (Appendix B)

## Standard Error Format
All JSON errors return:
```json
{
  "error": {
    "code": "unauthorized | not_found | rate_limited | validation_error | internal_error",
    "message": "human-readable description"
  }
}
```

## 1. POST /api/v1/ask (or /ask)
University academic QA endpoint with citations.

### Request
```json
{
  "question": "string, required, max 1000 chars",
  "department": "Computer Science",
  "course": "CS401",
  "stream": false
}
```

### Response 200
```json
{
  "answer": "Binary search trees require...",
  "citations": [
    {
      "document_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "title": "Algorithms Lecture 4",
      "page_number": 12,
      "section": "Tree Balancing",
      "snippet": "A balanced BST ensures O(log n) lookup..."
    }
  ],
  "served_by": "local"
}
```

## 2. POST /v1/chat/completions
OpenAI-compatible chat completion endpoint.

## 3. POST /api/v1/folders/register (or /sources/folder)
Register directory for folder-watch ingestion.

### Request
```json
{
  "path": "/data/courses/ComputerScience/Semester4/CS401",
  "department": "Computer Science",
  "semester": "Semester 4",
  "course": "CS401"
}
```

## 4. GET /health
```json
{
  "status": "ok",
  "database": true,
  "vector_store": true,
  "llm_backend": "local",
  "documents_indexed": 48213
}
```
