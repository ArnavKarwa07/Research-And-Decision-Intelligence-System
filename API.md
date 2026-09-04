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

## Self-Challenge & Dynamic Re-planning (Phase 5)

### Endpoint Outline

```http
POST /api/v1/queries/{query_id}/hypotheses/generate
GET /api/v1/queries/{query_id}/hypotheses
GET /api/v1/hypotheses/{hypothesis_id}
POST /api/v1/hypotheses/{hypothesis_id}/falsify
POST /api/v1/queries/{query_id}/critique
POST /api/v1/queries/{query_id}/self-challenge
```

### JSON Examples

**`POST /api/v1/queries/{query_id}/hypotheses/generate`**
*Description:* Triggers `HypothesisAgent` to generate 3-7 competing, falsifiable hypotheses for the specified query.
*Request Body (Optional):*
```json
{
  "max_hypotheses": 5,
  "existing_claims": []
}
```
*Response (HTTP 201 Created):*
```json
[
  {
    "id": "hyp-a1b2c3d4-1111-4000-8000-000000000001",
    "query_id": "q_45678901-1234-5678-1234-567812345678",
    "statement": "Primary assertion: System throughput scales linearly under microservice architecture.",
    "status": "proposed",
    "confidence": 0.6,
    "supporting_claim_ids": ["c_123"],
    "falsifying_claim_ids": [],
    "evidence_map": [],
    "falsification_attempts": 0,
    "max_falsification_attempts": 5,
    "metadata_": {
      "discriminating_evidence_needed": [
        "Direct empirical throughput benchmarks",
        "Network latency overhead measurements"
      ]
    },
    "created_at": "2026-09-04T00:10:00Z",
    "updated_at": "2026-09-04T00:10:00Z"
  },
  {
    "id": "hyp-a1b2c3d4-1111-4000-8000-000000000002",
    "query_id": "q_45678901-1234-5678-1234-567812345678",
    "statement": "Alternative assertion: Throughput bottlenecks occur at database synchronization boundaries.",
    "status": "proposed",
    "confidence": 0.4,
    "supporting_claim_ids": [],
    "falsifying_claim_ids": [],
    "evidence_map": [],
    "falsification_attempts": 0,
    "max_falsification_attempts": 5,
    "metadata_": {
      "discriminating_evidence_needed": [
        "Database locking profiling",
        "Connection pool saturation logs"
      ]
    },
    "created_at": "2026-09-04T00:10:00Z",
    "updated_at": "2026-09-04T00:10:00Z"
  }
]
```

**`GET /api/v1/queries/{query_id}/hypotheses`**
*Description:* Retrieves all generated hypotheses associated with a research query.
*Response (HTTP 200 OK):*
```json
[
  {
    "id": "hyp-a1b2c3d4-1111-4000-8000-000000000001",
    "query_id": "q_45678901-1234-5678-1234-567812345678",
    "statement": "Primary assertion: System throughput scales linearly under microservice architecture.",
    "status": "active",
    "confidence": 0.65,
    "supporting_claim_ids": ["c_123", "c_125"],
    "falsifying_claim_ids": ["c_129"],
    "evidence_map": [
      {
        "evidence_id": "ev_888",
        "hypothesis_id": "hyp-a1b2c3d4-1111-4000-8000-000000000001",
        "relationship": "SUPPORTS",
        "weight": 0.8,
        "justification": "Baseline load test proves linear scaling up to 10k RPS."
      }
    ],
    "falsification_attempts": 1,
    "max_falsification_attempts": 5,
    "metadata_": {},
    "created_at": "2026-09-04T00:10:00Z",
    "updated_at": "2026-09-04T00:12:30Z"
  }
]
```

**`GET /api/v1/hypotheses/{hypothesis_id}`**
*Description:* Retrieves detail for a specific hypothesis by UUID.
*Response (HTTP 200 OK):*
```json
{
  "id": "hyp-a1b2c3d4-1111-4000-8000-000000000001",
  "query_id": "q_45678901-1234-5678-1234-567812345678",
  "statement": "Primary assertion: System throughput scales linearly under microservice architecture.",
  "status": "supported",
  "confidence": 0.72,
  "supporting_claim_ids": ["c_123", "c_125"],
  "falsifying_claim_ids": ["c_129"],
  "evidence_map": [
    {
      "evidence_id": "ev_888",
      "hypothesis_id": "hyp-a1b2c3d4-1111-4000-8000-000000000001",
      "relationship": "SUPPORTS",
      "weight": 0.8,
      "justification": "Baseline load test proves linear scaling up to 10k RPS."
    },
    {
      "evidence_id": "ev_999",
      "hypothesis_id": "hyp-a1b2c3d4-1111-4000-8000-000000000001",
      "relationship": "FALSIFIES",
      "weight": 0.5,
      "justification": "Network saturation observed beyond 12k RPS."
    }
  ],
  "falsification_attempts": 2,
  "max_falsification_attempts": 5,
  "metadata_": {},
  "created_at": "2026-09-04T00:10:00Z",
  "updated_at": "2026-09-04T00:15:00Z"
}
```

**`POST /api/v1/hypotheses/{hypothesis_id}/falsify`**
*Description:* Triggers `FalsificationAgent` to formulate targeted disconfirming queries, search for counter-evidence, and update hypothesis confidence.
*Request Body (Optional):*
```json
{
  "research_context": "Deep audit on high-concurrency microservice edge cases.",
  "max_counter_queries": 3
}
```
*Response (HTTP 200 OK):*
```json
{
  "hypothesis_id": "hyp-a1b2c3d4-1111-4000-8000-000000000001",
  "evidence_items": [
    {
      "evidence_id": "ev_999",
      "hypothesis_id": "hyp-a1b2c3d4-1111-4000-8000-000000000001",
      "relationship": "FALSIFIES",
      "weight": 0.8,
      "justification": "Direct counter-evidence query flagged latency degradation under connection pool exhaustion.",
      "source_url": "https://example.org/counter-benchmark",
      "content": "Microservice response times degraded by 300% under pool starvation."
    }
  ],
  "updated_confidence": 0.45,
  "status_summary": "Falsification check completed for hyp-a1b2c3d4-1111-4000-8000-000000000001. Confidence updated to 0.45."
}
```

**`POST /api/v1/queries/{query_id}/critique`**
*Description:* Triggers `CriticAgent` to run an independent red-team audit across Evidence Quality, Logical Coherence, Completeness, and Bias Detection.
*Request Body (Optional):*
```json
{
  "synthesis_snapshot": "The system recommended Option B microservices architecture based on 5 supported claims.",
  "claims": [
    {"id": "c_123", "confidence": 0.88, "support_status": "SUPPORTED", "sources": [{"url": "https://example.com/spec"}]}
  ]
}
```
*Response (HTTP 200 OK):*
```json
{
  "id": "crit-f9e8d7c6-5555-4000-8000-000000000001",
  "query_id": "q_45678901-1234-5678-1234-567812345678",
  "synthesis_snapshot": "The system recommended Option B microservices architecture based on 5 supported claims.",
  "findings": [
    "Evidence Quality Issue: Claim c_123 depends on single source.",
    "Completeness Gap: Omitted variable 'financial_cost'."
  ],
  "weak_evidence": [
    {
      "claim_id": "c_123",
      "reason": "SINGLE_SOURCE",
      "severity": "MEDIUM",
      "details": "Claim 'c_123' relies on only 1 source.",
      "remediation": "Gather secondary independent sources to verify claim."
    }
  ],
  "missing_variables": [
    {
      "variable": "financial_cost",
      "impact": "HIGH",
      "category": "OMITTED_FACTOR",
      "suggested_action": "Include research analysis addressing financial cost."
    }
  ],
  "overall_severity": "HIGH",
  "recommendations": [
    "Address 1 weak evidence item(s) through targeted retrieval.",
    "Incorporate missing variables: financial_cost."
  ],
  "replan_triggered": true,
  "iteration": 1,
  "created_at": "2026-09-04T00:18:00Z",
  "updated_at": "2026-09-04T00:18:00Z"
}
```

**`POST /api/v1/queries/{query_id}/self-challenge`**
*Description:* Executes the complete end-to-end self-challenge pipeline: generating competing hypotheses, running falsification passes, executing red-team critique, and triggering dynamic re-planning loops until confidence threshold or iteration limit is satisfied.
*Request Body:*
```json
{
  "max_replan_iterations": 3,
  "confidence_threshold": 0.3
}
```
*Response (HTTP 200 OK):*
```json
{
  "query_id": "q_45678901-1234-5678-1234-567812345678",
  "hypotheses": [
    {
      "id": "hyp-a1b2c3d4-1111-4000-8000-000000000001",
      "query_id": "q_45678901-1234-5678-1234-567812345678",
      "statement": "Primary assertion: System throughput scales linearly under microservice architecture.",
      "status": "falsified",
      "confidence": 0.25,
      "supporting_claim_ids": ["c_123"],
      "falsifying_claim_ids": ["c_129"],
      "evidence_map": [],
      "falsification_attempts": 2,
      "max_falsification_attempts": 5,
      "metadata_": {},
      "created_at": "2026-09-04T00:10:00Z",
      "updated_at": "2026-09-04T00:20:00Z"
    }
  ],
  "critique_reports": [
    {
      "id": "crit-f9e8d7c6-5555-4000-8000-000000000001",
      "query_id": "q_45678901-1234-5678-1234-567812345678",
      "synthesis_snapshot": "Initial synthesis snapshot...",
      "findings": ["Evidence Quality Issue: Claim c_123 depends on single source."],
      "weak_evidence": [],
      "missing_variables": [],
      "overall_severity": "LOW",
      "recommendations": ["Synthesis and evidence chain pass red-team audit cleanly."],
      "replan_triggered": false,
      "iteration": 2,
      "created_at": "2026-09-04T00:22:00Z",
      "updated_at": "2026-09-04T00:22:00Z"
    }
  ],
  "replan_count": 1,
  "final_status": "completed",
  "finalized_with_caveats": false
}
```

## Event Streaming

Use SSE (`GET /queries/{id}/stream` and `GET /documents/{id}/stream`) for real-time updates.

**Phase 3 SSE Event Types:**
`claim:extracted`, `claim:verified`, `contradiction:detected`, `contradiction:resolved`, `source:scored`, `evidence:graph_updated`.

**Phase 4 SSE Document Event Types:**
`document:status_changed`, `document:parsed`, `document:chunked`, `document:embedded`, `document:failed`.

**Phase 5 SSE Self-Challenge Event Types:**
`hypothesis:generated`, `hypothesis:falsification_started`, `hypothesis:falsified`, `critique:report_generated`, `replan:triggered`, `self_challenge:completed`.

**Phase 6 SSE Decision Event Types:**
`decision:evaluating`, `decision:scored`, `decision:sensitivity_calculated`, `decision:completed`.

## Decision Intelligence (Phase 6)

### Endpoint Outline

```http
POST /api/v1/queries/{query_id}/decisions
GET /api/v1/queries/{query_id}/decisions
GET /api/v1/decisions/{decision_id}
POST /api/v1/decisions/{decision_id}/sensitivity
POST /api/v1/decisions/{decision_id}/scenarios
```

### JSON Examples

**`POST /api/v1/queries/{query_id}/decisions`**
*Description:* Runs multi-criteria weighted scoring, scenario simulation (best/base/worst), sensitivity stress-testing, and expected value calculation for a query.
*Request Body:*
```json
{
  "query_id": "q_45678901-1234-5678-1234-567812345678",
  "alternatives": [
    {"id": "opt1", "name": "Option A: Monolithic Deployment", "pros": ["Lower initial complexity"], "cons": ["Scalability ceiling"]},
    {"id": "opt2", "name": "Option B: Distributed Microservices", "pros": ["High scalability", "Fault isolation"], "cons": ["Operational overhead"]}
  ],
  "criteria": [
    {"id": "c1", "name": "Cost Efficiency", "weight": 0.4},
    {"id": "c2", "name": "System Scalability", "weight": 0.6}
  ],
  "scenarios": [
    {"name": "Best Case", "probability": 0.25},
    {"name": "Base Case", "probability": 0.50},
    {"name": "Worst Case", "probability": 0.25}
  ]
}
```
*Response (HTTP 201 Created):*
```json
{
  "id": "dec-11112222-3333-4444-5555-666677778888",
  "query_id": "q_45678901-1234-5678-1234-567812345678",
  "recommendation": "Option B: Distributed Microservices",
  "confidence": 0.84,
  "rationale": "Primary recommendation 'Option B' selected based on highest weighted multi-criteria score (84.0% confidence).",
  "alternatives": [
    {
      "id": "opt2",
      "name": "Option B: Distributed Microservices",
      "weighted_score": 0.88,
      "pros": ["High scalability", "Fault isolation"],
      "cons": ["Operational overhead"]
    }
  ],
  "criteria": [
    {"id": "c1", "name": "Cost Efficiency", "weight": 0.4},
    {"id": "c2", "name": "System Scalability", "weight": 0.6}
  ],
  "weighted_matrix": {
    "opt2": {"c1": 0.28, "c2": 0.60}
  },
  "scenarios": {
    "top_scenario_pick": "Option B: Distributed Microservices",
    "expected_payoffs": {"Option B: Distributed Microservices": 0.88}
  },
  "sensitivity_analysis": {
    "baseline_recommendation": "Option B: Distributed Microservices",
    "switch_points": [
      {
        "criterion_id": "c1",
        "criterion_name": "Cost Efficiency",
        "original_weight": 0.4,
        "threshold_weight": 0.68,
        "switches_from": "Option B: Distributed Microservices",
        "switches_to": "Option A: Monolithic Deployment"
      }
    ]
  },
  "expected_values": {
    "expected_values": {"Option B": 0.88},
    "best_ev_alternative": "Option B"
  },
  "key_risks": ["Operational overhead", "Network partition risk"],
  "assumptions": ["Traffic growth exceeds 50% year-over-year"],
  "decision_triggers": [
    {
      "condition": "Cost overrun > 20%",
      "threshold": "> 20%",
      "action": "Re-run sensitivity matrix",
      "severity": "high"
    }
  ],
  "created_at": "2026-09-04T01:15:00Z",
  "updated_at": "2026-09-04T01:15:00Z"
}
```
