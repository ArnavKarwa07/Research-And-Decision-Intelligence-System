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

## Knowledge

```http
POST /projects/{project_id}/documents
GET /projects/{project_id}/documents
POST /projects/{project_id}/search
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

## Decisions

```http
GET /runs/{run_id}/decision
POST /runs/{run_id}/decision/feedback
```

## Event Streaming

Use SSE (`GET /queries/{id}/stream`) initially for one-way UI updates.
Use WebSockets when bidirectional live control is required.

**Phase 3 SSE Event Types Added:**
`claim:extracted`, `claim:verified`, `contradiction:detected`, `contradiction:resolved`, `source:scored`, `evidence:graph_updated`.

Example event:

```json
{
  "type": "contradiction:detected",
  "query_id": "query_123",
  "agent": "contradiction_agent",
  "severity": "high",
  "message": "Comparing two conflicting revenue figures"
}
```
