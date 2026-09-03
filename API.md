# API.md

# API Contract Outline

## Authentication

Bearer token / session-based authentication.

## Projects

```http
POST /projects
GET /projects
GET /projects/{project_id}
PATCH /projects/{project_id}
```

## Tasks

```http
POST /projects/{project_id}/tasks
GET /tasks/{task_id}
POST /tasks/{task_id}/cancel
```

## Runs

```http
POST /tasks/{task_id}/runs
GET /runs/{run_id}
GET /runs/{run_id}/events
POST /runs/{run_id}/approve
POST /runs/{run_id}/cancel
```

## Internal Knowledge & RAG (Phase 4)

### Document Management Endpoints

```http
POST /api/v1/sessions/{session_id}/documents
GET /api/v1/sessions/{session_id}/documents
GET /api/v1/documents/{document_id}
DELETE /api/v1/documents/{document_id}
GET /api/v1/documents/{document_id}/chunks
GET /api/v1/documents/{document_id}/stream
```

### Document Search Endpoints

```http
POST /api/v1/sessions/{session_id}/search/hybrid
POST /api/v1/sessions/{session_id}/search/semantic
POST /api/v1/sessions/{session_id}/search/keyword
```

## Evidence & Phase 3 Intelligence

```http
GET /queries/{id}/claims
POST /queries/{id}/claims/extract
POST /queries/{id}/claims/{claim_id}/verify
GET /queries/{id}/contradictions
POST /contradictions/{id}/resolve
GET /queries/{id}/evidence-graph
```

### JSON Examples

**`GET /queries/{id}/claims`**
*Response:*
```json
[
  {
    "id": "c_123",
    "query_id": "q_456",
    "content": "The company's revenue grew by 15% in Q3.",
    "claim_type": "FACT",
    "confidence": 0.88,
    "status": "verified",
    "claim_sources": [
      {
        "source_id": "s_789",
        "source_title": "Q3 Financial Report",
        "source_url": "https://example.com/report",
        "excerpt": "Revenue grew 15% year-over-year in Q3.",
        "support_type": "supports",
        "relevance_score": 0.95
      }
    ],
    "created_at": "2026-09-03T12:00:00Z",
    "verified_at": "2026-09-03T12:05:00Z"
  }
]
```

**`POST /queries/{id}/claims/{claim_id}/verify`**
*Response:*
```json
{
  "claim_id": "c_123",
  "status": "verified",
  "verification_strategies_used": ["Direct", "Authority"],
  "sources_added": 2
}
```

**`GET /queries/{id}/contradictions`**
*Response:*
```json
[
  {
    "id": "contra_456",
    "query_id": "q_456",
    "claim_a_id": "c_123",
    "claim_b_id": "c_124",
    "contradiction_type": "direct",
    "severity": "high",
    "resolution_status": "unresolved",
    "resolution_notes": null,
    "detected_at": "2026-09-03T12:06:00Z",
    "resolved_at": null
  }
]
```

**`POST /contradictions/{id}/resolve`**
*Request:*
```json
{
  "resolution_status": "resolved_a",
  "resolution_notes": "Source A is official documentation"
}
```
*Response:*
```json
{
  "id": "contra_456",
  "resolution_status": "resolved_a",
  "resolution_notes": "Source A is official documentation",
  "resolved_at": "2026-09-03T12:10:00Z"
}
```

**`GET /queries/{id}/evidence-graph`**
*Response:*
```json
{
  "nodes": [
    {"id": "c_123", "type": "claim"}
  ],
  "edges": [
    {"source": "s_789", "target": "c_123", "type": "supports"}
  ],
  "stats": {
    "total_claims": 12,
    "verified": 8,
    "disputed": 2,
    "unresolved": 2,
    "avg_confidence": 0.85,
    "total_contradictions": 1,
    "independence_score": 0.9
  }
}
```

**`POST /api/v1/sessions/{session_id}/documents`**
*Request:* `multipart/form-data` (file: `UploadFile`)
*Response (HTTP 202 Accepted):*
```json
{
  "id": "12345678-1234-5678-1234-567812345678",
  "session_id": "87654321-4321-8765-4321-876543218765",
  "filename": "annual_report_2025.pdf",
  "mime_type": "application/pdf",
  "file_path": "./uploads/documents/annual_report_2025.pdf",
  "file_size": 2458900,
  "file_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "status": "queued",
  "error_message": null,
  "chunk_count": 0,
  "metadata_json": {},
  "created_at": "2026-09-04T00:00:00Z",
  "updated_at": "2026-09-04T00:00:00Z"
}
```

**`GET /api/v1/documents/{document_id}`**
*Response (HTTP 200 OK):*
```json
{
  "id": "12345678-1234-5678-1234-567812345678",
  "session_id": "87654321-4321-8765-4321-876543218765",
  "filename": "annual_report_2025.pdf",
  "mime_type": "application/pdf",
  "file_path": "./uploads/documents/annual_report_2025.pdf",
  "file_size": 2458900,
  "file_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "status": "stored",
  "error_message": null,
  "chunk_count": 48,
  "metadata_json": {"author": "Finance Team", "page_count": 12},
  "created_at": "2026-09-04T00:00:00Z",
  "updated_at": "2026-09-04T00:01:15Z"
}
```

**`DELETE /api/v1/documents/{document_id}`**
*Response (HTTP 200 OK):*
```json
{
  "message": "Document 12345678-1234-5678-1234-567812345678 and related chunks/vectors deleted successfully"
}
```

**`POST /api/v1/sessions/{session_id}/search/hybrid`**
*Request Body:*
```json
{
  "query": "What were the total Q3 operating expenses?",
  "top_k": 5,
  "alpha": 0.5,
  "enable_reranking": true
}
```
*Response (HTTP 200 OK):*
```json
{
  "session_id": "87654321-4321-8765-4321-876543218765",
  "query": "What were the total Q3 operating expenses?",
  "search_type": "hybrid",
  "total_results": 1,
  "chunks": [
    {
      "id": "chk_9876",
      "document_id": "12345678-1234-5678-1234-567812345678",
      "chunk_index": 4,
      "content": "Total operating expenses in Q3 amounted to $14.2M, representing a 5% decrease year-over-year.",
      "content_hash": "a1b2c3d4e5f6...",
      "token_count": 18,
      "page_number": 6,
      "section_heading": "Financial Operations",
      "score": 0.94,
      "citation": "[Doc: annual_report_2025.pdf, Page: 6, Chunk: 4]"
    }
  ]
}
```

## Decisions

```http
GET /runs/{run_id}/decision
POST /runs/{run_id}/decision/feedback
```

## Event Streaming

Use SSE (`GET /queries/{id}/stream` and `GET /documents/{id}/stream`) for real-time updates.

**Phase 3 SSE Event Types:**
`claim:extracted`, `claim:verified`, `contradiction:detected`, `contradiction:resolved`, `source:scored`, `evidence:graph_updated`.

**Phase 4 SSE Document Event Types:**
`document:status_changed`, `document:parsed`, `document:chunked`, `document:embedded`, `document:failed`.

Example event:

```json
{
  "event_type": "document:status_changed",
  "document_id": "12345678-1234-5678-1234-567812345678",
  "status": "chunking"
}
```
