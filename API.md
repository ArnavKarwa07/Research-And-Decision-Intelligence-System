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

## Data Agent & Data Visualization (Phase 7)

```http
POST /api/v1/data/datasets/upload
GET /api/v1/data/datasets/{dataset_id}/schema
POST /api/v1/data/query
POST /api/v1/data/analyze
POST /api/v1/data/visualize
GET /api/v1/data/artifacts/{query_id}
```

### Endpoints Overview

1. `POST /api/v1/data/datasets/upload`
   - Uploads a CSV or Excel dataset, ingests it into SQLite, profiles columns/types/stats, and returns metadata.
2. `GET /api/v1/data/datasets/{dataset_id}/schema`
   - Retrieves column schema and profiling stats for an uploaded dataset.
3. `POST /api/v1/data/query`
   - Executes a read-only SQL query with safety AST keyword validation and limit injection.
4. `POST /api/v1/data/analyze`
   - Executes a Python script in a secure sandbox with AST module whitelisting and timeout limits.
5. `POST /api/v1/data/visualize`
   - Programmatically generates Vega-Lite JSON visualization specifications, summary tables, and statistical key findings.
6. `GET /api/v1/data/artifacts/{query_id}`
   - Compiles SQL queries, Python scripts, chart configs, and execution logs into a reproducible analysis artifact.

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

## Human-in-the-Loop & Safety Framework (Phase 8)

### Endpoint Outline

```http
GET /api/v1/hitl/approvals
POST /api/v1/hitl/approvals/{gate_id}/resolve
GET /api/v1/hitl/clarifications
POST /api/v1/hitl/clarifications/{question_id}/answer
POST /api/v1/hitl/evidence/override
POST /api/v1/hitl/assumptions/confirm

GET /api/v1/safety/audit-logs
GET /api/v1/safety/permissions
POST /api/v1/safety/scan-pii
POST /api/v1/safety/check-injection
```

### Endpoints Overview

1. `GET /api/v1/hitl/approvals`
   - Lists pending or filtered human approval gates. Automatically evaluates 5-minute timeout checks to expire stale pending gates.
2. `POST /api/v1/hitl/approvals/{gate_id}/resolve`
   - Resolves a pending approval gate with an operator decision (`approve`, `reject`, or `kill`) and optional user feedback.
3. `GET /api/v1/hitl/clarifications`
   - Lists clarification questions submitted by agents to resolve query ambiguity. Triggers 5-minute timeout checks.
4. `POST /api/v1/hitl/clarifications/{question_id}/answer`
   - Submits a user answer to a pending clarification question.
5. `POST /api/v1/hitl/evidence/override`
   - Allows operators to override verified claim evidence statuses (`supported`, `contradicted`, `inferred`, `unverified`) and attach notes.
6. `POST /api/v1/hitl/assumptions/confirm`
   - Confirms or rejects preliminary agent hypotheses/assumptions.
7. `GET /api/v1/safety/audit-logs`
   - Retrieves immutable security audit logs with filtering by `run_id`, `action_type`, `severity`, and `limit`.
8. `GET /api/v1/safety/permissions`
   - Retrieves active role-based tool capability permission matrix (`research`, `data_agent`, `supervisor`).
9. `POST /api/v1/safety/scan-pii`
   - Scans input text for sensitive PII (emails, phones, SSNs, API tokens, passwords) and returns redacted text.
10. `POST /api/v1/safety/check-injection`
    - Scans untrusted content for indirect prompt injections, jailbreaks, and dangerous payloads, returning risk score and XML-wrapped sanitized text.

### JSON Examples

**`GET /api/v1/hitl/approvals`**
*Query Parameters:* `run_id` (optional), `status_filter` (optional, e.g. `pending`, `approved`, `expired`)
*Response (HTTP 200 OK):*
```json
[
  {
    "id": "gate-12345678-aaaa-bbbb-cccc-111122223333",
    "run_id": "run-88889999-4444-1111-2222-333344445555",
    "agent_id": "data_agent",
    "tool_name": "python_sandbox",
    "tool_args": {
      "code": "import pandas as pd\ndf = pd.read_csv('data.csv')\nprint(df.describe())"
    },
    "risk_level": "high",
    "description": "High-risk Python sandbox code execution requesting human approval.",
    "status": "pending",
    "user_feedback": null,
    "timeout_seconds": 300,
    "created_at": "2026-09-04T19:00:00Z",
    "resolved_at": null
  }
]
```

**`POST /api/v1/hitl/approvals/{gate_id}/resolve`**
*Request Body:*
```json
{
  "action": "approve",
  "user_feedback": "Approved after reviewing code safety."
}
```
*Response (HTTP 200 OK):*
```json
{
  "id": "gate-12345678-aaaa-bbbb-cccc-111122223333",
  "run_id": "run-88889999-4444-1111-2222-333344445555",
  "agent_id": "data_agent",
  "tool_name": "python_sandbox",
  "tool_args": {
    "code": "import pandas as pd\ndf = pd.read_csv('data.csv')\nprint(df.describe())"
  },
  "risk_level": "high",
  "description": "High-risk Python sandbox code execution requesting human approval.",
  "status": "approved",
  "user_feedback": "Approved after reviewing code safety.",
  "timeout_seconds": 300,
  "created_at": "2026-09-04T19:00:00Z",
  "resolved_at": "2026-09-04T19:02:15Z"
}
```

**`GET /api/v1/hitl/clarifications`**
*Query Parameters:* `run_id` (optional), `status_filter` (optional)
*Response (HTTP 200 OK):*
```json
[
  {
    "id": "clar-98765432-bbbb-cccc-dddd-555566667777",
    "run_id": "run-88889999-4444-1111-2222-333344445555",
    "agent_id": "gatekeeper_agent",
    "prompt": "The research objective is ambiguous. Please specify target focus area.",
    "options": [
      "Focus on financial metrics",
      "Focus on technical architecture",
      "Focus on market analysis"
    ],
    "answer": null,
    "status": "pending",
    "created_at": "2026-09-04T19:05:00Z",
    "resolved_at": null
  }
]
```

**`POST /api/v1/hitl/clarifications/{question_id}/answer`**
*Request Body:*
```json
{
  "answer": "Focus on technical architecture"
}
```
*Response (HTTP 200 OK):*
```json
{
  "id": "clar-98765432-bbbb-cccc-dddd-555566667777",
  "run_id": "run-88889999-4444-1111-2222-333344445555",
  "agent_id": "gatekeeper_agent",
  "prompt": "The research objective is ambiguous. Please specify target focus area.",
  "options": [
    "Focus on financial metrics",
    "Focus on technical architecture",
    "Focus on market analysis"
  ],
  "answer": "Focus on technical architecture",
  "status": "answered",
  "created_at": "2026-09-04T19:05:00Z",
  "resolved_at": "2026-09-04T19:06:30Z"
}
```

**`POST /api/v1/hitl/evidence/override`**
*Request Body:*
```json
{
  "claim_id": "c_12345678-aaaa-bbbb-cccc-000000000001",
  "status": "supported",
  "notes": "Verified against official Q3 SEC filing document.",
  "weight_adjustment": 1.5
}
```
*Response (HTTP 200 OK):*
```json
{
  "message": "Claim evidence status successfully overridden.",
  "claim_id": "c_12345678-aaaa-bbbb-cccc-000000000001",
  "status": "supported"
}
```

**`POST /api/v1/hitl/assumptions/confirm`**
*Request Body:*
```json
{
  "hypothesis_id": "hyp-a1b2c3d4-1111-4000-8000-000000000001",
  "confirmed": true,
  "user_notes": "Confirmed microservices traffic assumption with engineering lead."
}
```
*Response (HTTP 200 OK):*
```json
{
  "message": "Assumption updated successfully.",
  "hypothesis_id": "hyp-a1b2c3d4-1111-4000-8000-000000000001",
  "status": "confirmed"
}
```

**`GET /api/v1/safety/audit-logs`**
*Query Parameters:* `run_id` (optional), `action_type` (optional), `severity` (optional), `limit` (default: 50, max: 500)
*Response (HTTP 200 OK):*
```json
[
  {
    "id": "audit-11112222-3333-4444-5555-666677778888",
    "run_id": "run-88889999-4444-1111-2222-333344445555",
    "agent_id": "data_agent",
    "action_type": "approval_requested",
    "severity": "WARNING",
    "details": {
      "gate_id": "gate-12345678-aaaa-bbbb-cccc-111122223333",
      "tool_name": "python_sandbox",
      "risk_level": "high",
      "timeout_seconds": 300
    },
    "timestamp": "2026-09-04T19:00:00Z"
  }
]
```

**`GET /api/v1/safety/permissions`**
*Query Parameters:* `agent_role` (optional, e.g. `research`, `data_agent`, `supervisor`)
*Response (HTTP 200 OK):*
```json
{
  "research": {
    "allowed": ["web_search", "content_extractor", "summarize"],
    "denied": ["python_sandbox", "execute_sql_query"],
    "requires_approval": []
  },
  "data_agent": {
    "allowed": ["sql_schema_inspect", "csv_inspect", "chart_generate"],
    "denied": ["web_search"],
    "requires_approval": ["python_sandbox", "execute_sql_query"]
  },
  "supervisor": {
    "allowed": ["web_search", "content_extractor", "summarize", "sql_schema_inspect", "csv_inspect", "chart_generate"],
    "denied": [],
    "requires_approval": ["python_sandbox", "execute_sql_query"]
  }
}
```

**`POST /api/v1/safety/scan-pii`**
*Request Body:*
```json
{
  "text": "Contact user at alice@example.com or call +1-555-0199 with token sk_live_999888777666555444333."
}
```
*Response (HTTP 200 OK):*
```json
{
  "original_length": 98,
  "sanitized_text": "Contact user at [REDACTED_EMAIL] or call [REDACTED_PHONE] with token [REDACTED_API_TOKEN].",
  "redactions_count": 3,
  "detected_types": ["EMAIL", "PHONE", "API_TOKEN"]
}
```

**`POST /api/v1/safety/check-injection`**
*Query Parameters:* `content` (required), `source_type` (default: `"web"`)
*Response (HTTP 200 OK):*
```json
{
  "is_injection_detected": true,
  "risk_score": 0.7,
  "flagged_patterns": [
    "ignore\\s+all\\s+previous\\s+instructions",
    "<script\\b[^>]*>"
  ],
  "sanitized_content": "<untrusted_content source='web' injection_flagged='True'>\n[BLOCKED_INJECTION_PATTERN: ignore\\s+all\\s+previous\\s+instructions] System instructions neutralized.\n[BLOCKED_INJECTION_PATTERN: <script\\b[^>]*>] alert('xss')</script>\n</untrusted_content>"
}
```

## Production Agent Runtime (Phase 9)

```http
POST /api/v1/runtime/runs/{run_id}/pause
POST /api/v1/runtime/runs/{run_id}/resume
GET /api/v1/runtime/runs/{run_id}/checkpoints
GET /api/v1/runtime/runs/{run_id}/budget

POST /api/runs/{run_id}/pause
POST /api/runs/{run_id}/resume
GET /api/runs/{run_id}/checkpoints
GET /api/runs/{run_id}/budget
```

### Endpoints Overview

1. `POST /api/v1/runtime/runs/{run_id}/pause` (and `/api/runs/{run_id}/pause`)
   - Pauses an active research run. Updates job queue status to `paused`.
2. `POST /api/v1/runtime/runs/{run_id}/resume` (and `/api/runs/{run_id}/resume`)
   - Resumes a paused or failed research run, re-enqueuing it for execution from its latest step checkpoint.
3. `GET /api/v1/runtime/runs/{run_id}/checkpoints` (and `/api/runs/{run_id}/checkpoints`)
   - Retrieves all step-level state checkpoints recorded for a research run.
4. `GET /api/v1/runtime/runs/{run_id}/budget` (and `/api/runs/{run_id}/budget`)
   - Retrieves multi-dimension budget tracking statistics (token usage, search count, tool calls, wall-clock duration) and soft/hard limit status.

### SSE Telemetry Event Types (Phase 9)

- `telemetry:cost_updated`: Emitted on each LLM or tool execution with incremental cost and query cost metrics breakdown.
- `telemetry:budget_updated`: Emitted when general budget stats update.
- `telemetry:budget_warning`: Emitted when a soft budget limit (80% utilization) is reached.
- `telemetry:budget_exceeded`: Emitted when a hard budget limit is hit and execution halts.

### JSON Examples

**`POST /api/v1/runtime/runs/{run_id}/pause`**
*Response (HTTP 200 OK):*
```json
{
  "run_id": "run-88889999-4444-1111-2222-333344445555",
  "job_id": "job-a1b2c3d4e5",
  "status": "paused",
  "message": "Run 'run-88889999-4444-1111-2222-333344445555' successfully paused."
}
```

**`POST /api/v1/runtime/runs/{run_id}/resume`**
*Response (HTTP 200 OK):*
```json
{
  "run_id": "run-88889999-4444-1111-2222-333344445555",
  "job_id": "job-a1b2c3d4e5",
  "status": "queued",
  "latest_checkpoint_id": "chk-run-8888-2",
  "message": "Run 'run-88889999-4444-1111-2222-333344445555' successfully resumed."
}
```

**`GET /api/v1/runtime/runs/{run_id}/checkpoints`**
*Response (HTTP 200 OK):*
```json
{
  "run_id": "run-88889999-4444-1111-2222-333344445555",
  "count": 2,
  "checkpoints": [
    {
      "checkpoint_id": "chk-run-8888-1",
      "run_id": "run-88889999-4444-1111-2222-333344445555",
      "step_name": "supervisor_step",
      "step_index": 1,
      "state": {
        "text": "Analyze cloud migration options",
        "mode": "comprehensive",
        "plan": ["web_search", "synthesis"]
      },
      "claims": [],
      "sources": [],
      "agent_outputs": {},
      "timestamp": "2026-09-04T20:00:00Z"
    },
    {
      "checkpoint_id": "chk-run-8888-2",
      "run_id": "run-88889999-4444-1111-2222-333344445555",
      "step_name": "research_step",
      "step_index": 2,
      "state": {
        "text": "Analyze cloud migration options",
        "mode": "comprehensive",
        "snippets": [{"url": "https://example.com/cloud", "title": "Cloud Benchmarks"}]
      },
      "claims": [],
      "sources": [{"url": "https://example.com/cloud", "score": 0.85}],
      "agent_outputs": {"summary": "Preliminary findings gathered."},
      "timestamp": "2026-09-04T20:02:15Z"
    }
  ]
}
```

**`GET /api/v1/runtime/runs/{run_id}/budget`**
*Response (HTTP 200 OK):*
```json
{
  "run_id": "run-88889999-4444-1111-2222-333344445555",
  "hard_limit_exceeded": false,
  "hard_limit_reason": null,
  "soft_warnings": [],
  "budget_stats": {
    "tokens": {
      "prompt": 12500,
      "completion": 3200,
      "total": 15700,
      "max": 100000,
      "soft_limit": 80000,
      "utilization": 0.157
    },
    "searches": {
      "conducted": 4,
      "max": 20,
      "soft_limit": 16,
      "utilization": 0.20
    },
    "tools": {
      "calls": 8,
      "max": 50,
      "soft_limit": 40,
      "utilization": 0.16
    },
    "wall_clock": {
      "elapsed_seconds": 45.2,
      "max_seconds": 300.0,
      "soft_limit_seconds": 240.0,
      "utilization": 0.1507
    }
  }
}
```

## Phase 11 - Production UX Artifacts & Export Packages

```http
POST /api/v1/queries/{query_id}/artifacts/decision-memo
GET  /api/v1/queries/{query_id}/artifacts/decision-memo
POST /api/v1/queries/{query_id}/artifacts/research-report
GET  /api/v1/queries/{query_id}/artifacts/research-report
GET  /api/v1/queries/{query_id}/artifacts/comparison-table
GET  /api/v1/queries/{query_id}/artifacts/export-package
GET  /api/v1/queries/{query_id}/sources
```

### JSON Examples

**`POST /api/v1/queries/{query_id}/artifacts/decision-memo`**
*Description:* Generates a structured executive decision memo containing executive summary, MCDA matrix, scenario projections (Best/Base/Worst), risk/assumption assessment, and footnote citations.
*Response (HTTP 201 Created):*
```json
{
  "id": "art-11112222-3333-4444-5555-666677778888",
  "query_id": "q_45678901-1234-5678-1234-567812345678",
  "title": "Executive Decision Memo: AWS vs GCP ML Workload Migration",
  "artifact_type": "decision_memo",
  "executive_summary": "Migrate primary training to GCP TPU/GPU instances while keeping data lake on AWS S3.",
  "objective_and_constraints": {
    "objective": "Compare AWS vs GCP for ML workloads with $5k/mo budget limit",
    "confidence": 0.88
  },
  "mcda_comparison_matrix": {
    "alternatives": [
      {"name": "GCP TPU Instances", "weighted_score": 0.88},
      {"name": "AWS EC2 P4d", "weighted_score": 0.76}
    ],
    "criteria": [
      {"name": "Total Cost", "weight": 0.40},
      {"name": "Performance", "weight": 0.35}
    ]
  },
  "scenario_projections": [
    {"name": "Best Case", "probability": 0.25, "description": "30% price reduction on TPU v4 preemptibles."},
    {"name": "Base Case", "probability": 0.50, "description": "Target metrics met within budget."}
  ],
  "key_risks_and_assumptions": {
    "risks": ["Egress bandwidth cost spikes"],
    "assumptions": ["Workload scales 20% YoY"]
  },
  "citation_footnotes": [
    {"index": 1, "title": "GCP TPU Pricing Guide", "publisher": "Google Cloud", "url": "https://cloud.google.com/tpu/pricing"}
  ],
  "markdown_content": "# EXECUTIVE DECISION MEMO\n...",
  "html_content": "<div style=\"...\"><h1>EXECUTIVE DECISION MEMO</h1>...</div>",
  "created_at": "2026-09-04T22:00:00Z"
}
```

**`GET /api/v1/queries/{query_id}/artifacts/export-package`**
*Description:* Downloads a bundled `.zip` archive containing `decision_memo.md`, `research_report.md`, `executive_summary.html`, `research_state.json`, `sources_manifest.csv`, and `mcda_comparison.csv`.
*Response (HTTP 200 OK):*
`Binary Stream (application/zip)`

## Phase 12 - Continuous Intelligence & Decision Monitoring

```http
POST   /api/v1/monitoring/jobs
GET    /api/v1/monitoring/jobs
GET    /api/v1/monitoring/jobs/{id}
PATCH  /api/v1/monitoring/jobs/{id}
DELETE /api/v1/monitoring/jobs/{id}
POST   /api/v1/monitoring/jobs/{id}/run
GET    /api/v1/monitoring/jobs/{id}/logs
POST   /api/v1/monitoring/baselines
GET    /api/v1/monitoring/baselines/{id}
GET    /api/v1/monitoring/alerts
POST   /api/v1/monitoring/alerts/{id}/acknowledge
POST   /api/v1/memory/items
GET    /api/v1/memory/items
GET    /api/v1/memory/items/{id}
PATCH  /api/v1/memory/items/{id}
POST   /api/v1/memory/items/{id}/approve
GET    /api/v1/memory/heuristics
POST   /api/v1/memory/heuristics
POST   /api/v1/memory/inject-context
```

### Endpoints Overview

1. `POST /api/v1/monitoring/jobs`
   - Creates a continuous research and decision monitoring job (`MonitoringJobCreate`). Accepts `name`, `schedule_type` (`CRON`, `INTERVAL`, `EVENT_DRIVEN`), `cron_expression`, `interval_seconds`, `alert_threshold`, `webhook_url`, and baseline snapshot references.
2. `GET /api/v1/monitoring/jobs`
   - Lists monitoring jobs filtered by `project_id`, `session_id`, or `status` (`ACTIVE`, `PAUSED`, etc.).
3. `GET /api/v1/monitoring/jobs/{id}`
   - Retrieves full configuration details for a specific monitoring job by ID.
4. `PATCH /api/v1/monitoring/jobs/{id}`
   - Updates monitoring job settings, schedule, alert threshold, status (e.g. pause or resume), or metadata.
5. `DELETE /api/v1/monitoring/jobs/{id}`
   - Deletes a monitoring job and cascades deletion to associated execution logs and decision alerts.
6. `POST /api/v1/monitoring/jobs/{id}/run`
   - Triggers a manual execution run for a monitoring job, calculating deltas against baseline snapshots and outputting execution logs.
7. `GET /api/v1/monitoring/jobs/{id}/logs`
   - Retrieves historical execution logs (`MonitoringExecutionLog`) for a job ordered by execution timestamp.
8. `POST /api/v1/monitoring/baselines`
   - Creates a new research baseline snapshot (`ResearchBaselineSnapshot`) containing claims, sources, assumptions, and decision state.
9. `GET /api/v1/monitoring/baselines/{id}`
   - Retrieves a baseline snapshot by ID.
10. `GET /api/v1/monitoring/alerts`
    - Lists decision alerts (`DecisionAlert`) filtered by `job_id`, `project_id`, `session_id`, `status` (`UNREAD`, `ACKNOWLEDGED`, `RESOLVED`), or `severity` (`INFO`, `WARNING`, `HIGH`, `CRITICAL`).
11. `POST /api/v1/monitoring/alerts/{id}/acknowledge`
    - Marks a decision alert as acknowledged.
12. `POST /api/v1/memory/items`
    - Creates a persistent project memory item (`ProjectMemoryItemCreate`) across types: `FACT`, `DECISION_TRAIL`, `REUSABLE_ASSUMPTION`, `PRIOR_CONCLUSION`, `LESSON_LEARNED`.
13. `GET /api/v1/memory/items`
    - Lists project memory items with filters for `project_id`, `session_id`, `memory_type`, `validity_status`, `human_approval_status`, or `key`.
14. `GET /api/v1/memory/items/{id}`
    - Retrieves a project memory item by ID.
15. `PATCH /api/v1/memory/items/{id}`
    - Updates a project memory item's summary, content, confidence, validity, human approval status, or tags.
16. `POST /api/v1/memory/items/{id}/approve`
    - Approves or rejects a candidate memory item or assumption (`approval_status`: `APPROVED` or `REJECTED`).
17. `GET /api/v1/memory/heuristics`
    - Retrieves domain-specific research heuristics (untrusted domain blacklists, effective query templates, verified tool execution patterns, failure modes) by `domain` string.
18. `POST /api/v1/memory/heuristics`
    - Adds or updates domain-specific research heuristics.
19. `POST /api/v1/memory/inject-context`
    - Previews project memory context injection payload and formatted markdown text for prompt generation.

### JSON Examples

**`POST /api/v1/monitoring/jobs`**
*Request Body:*
```json
{
  "name": "Cloud Infrastructure Competitor & Pricing Monitor",
  "schedule_type": "CRON",
  "cron_expression": "0 0 * * *",
  "alert_threshold": 0.5,
  "webhook_url": "https://hooks.example.com/alerts/radis",
  "baseline_snapshot_id": "b1000000-0000-0000-0000-000000000001",
  "metadata": {
    "category": "infrastructure",
    "owner": "devops-team"
  }
}
```
*Response (HTTP 201 Created):*
```json
{
  "id": "j1234567-89ab-cdef-0123-456789abcdef",
  "project_id": null,
  "session_id": null,
  "query_id": null,
  "baseline_snapshot_id": "b1000000-0000-0000-0000-000000000001",
  "name": "Cloud Infrastructure Competitor & Pricing Monitor",
  "schedule_type": "CRON",
  "cron_expression": "0 0 * * *",
  "interval_seconds": null,
  "status": "ACTIVE",
  "alert_threshold": 0.5,
  "webhook_url": "https://hooks.example.com/alerts/radis",
  "last_run_at": null,
  "next_run_at": "2026-09-06T00:00:00Z",
  "run_count": 0,
  "metadata": {
    "category": "infrastructure",
    "owner": "devops-team"
  },
  "created_at": "2026-09-05T00:45:00Z",
  "updated_at": "2026-09-05T00:45:00Z"
}
```

**`POST /api/v1/monitoring/jobs/{id}/run`**
*Response (HTTP 200 OK):*
```json
{
  "id": "e9999999-8888-7777-6666-555544443333",
  "job_id": "j1234567-89ab-cdef-0123-456789abcdef",
  "new_query_id": "q1111111-2222-3333-4444-555566667777",
  "status": "ALERT_TRIGGERED",
  "materiality_score": 0.675,
  "materiality_level": "HIGH",
  "delta_summary": {
    "sub_scores": {
      "s_assumption": 1.0,
      "s_contradiction": 0.5,
      "s_matrix": 1.0,
      "s_source": 0.0
    },
    "diffs": {
      "assumptions_invalidated": [{"text": "GCP pricing remains 20% lower than AWS", "status": "INVALIDATED"}],
      "decision_drift": {
        "baseline_recommendation": "Migrate to GCP TPU v4",
        "current_recommendation": "Retain AWS EC2 P4d",
        "recommendation_flipped": true
      }
    },
    "recommendation_flipped": true,
    "summary": "Recommendation flipped from 'Migrate to GCP TPU v4' to 'Retain AWS EC2 P4d'; 1 assumption(s) invalidated"
  },
  "alert_triggered": true,
  "executed_at": "2026-09-05T00:46:00Z",
  "execution_duration_seconds": 2.45,
  "error_message": null
}
```

**`POST /api/v1/memory/items`**
*Request Body:*
```json
{
  "memory_type": "REUSABLE_ASSUMPTION",
  "key": "cloud_egress_pricing_growth",
  "summary": "Assumed cloud egress cost growth rate stays below 15% per annum",
  "content": {
    "full_assumption": "Egress bandwidth growth remains under 15% YoY based on CDN optimizations.",
    "category": "financial"
  },
  "confidence": 0.85,
  "validity_status": "ACTIVE",
  "human_approval_status": "PENDING",
  "tags": ["cloud", "egress", "financial"]
}
```
*Response (HTTP 201 Created):*
```json
{
  "id": "m5555555-4444-3333-2222-111100009999",
  "project_id": null,
  "session_id": null,
  "memory_type": "REUSABLE_ASSUMPTION",
  "key": "cloud_egress_pricing_growth",
  "summary": "Assumed cloud egress cost growth rate stays below 15% per annum",
  "content": {
    "full_assumption": "Egress bandwidth growth remains under 15% YoY based on CDN optimizations.",
    "category": "financial"
  },
  "confidence": 0.85,
  "source_query_id": null,
  "validity_status": "ACTIVE",
  "human_approval_status": "PENDING",
  "tags": ["cloud", "egress", "financial"],
  "created_at": "2026-09-05T00:46:30Z",
  "updated_at": "2026-09-05T00:46:30Z"
}
```

**`POST /api/v1/memory/inject-context`**
*Request Body:*
```json
{
  "domain": "cloud_computing",
  "query_text": "Analyze AWS vs GCP cost structure for large ML workloads"
}
```
*Response (HTTP 200 OK):*
```json
{
  "context": {
    "project_id": null,
    "session_id": null,
    "active_facts": [
      {
        "id": "m1111111-2222-3333-4444-555566667777",
        "memory_type": "FACT",
        "key": "fact_gcp_tpu_v4",
        "summary": "GCP TPU v4 instances offer 3.2x higher FLOPS per dollar for Transformer training.",
        "content": {"claim_type": "FACT"},
        "confidence": 0.92,
        "validity_status": "ACTIVE",
        "human_approval_status": "APPROVED",
        "tags": ["gcp", "tpu", "hardware"]
      }
    ],
    "prior_conclusions": [],
    "reusable_assumptions": [],
    "lessons_learned": [],
    "heuristics": {
      "id": "h8888888-7777-6666-5555-444433332222",
      "domain": "cloud_computing",
      "untrusted_domains": ["unverified-cloud-blog.com"],
      "effective_query_templates": ["{provider} benchmark instance pricing ML training"],
      "verified_tool_patterns": [],
      "failure_modes": []
    }
  },
  "formatted_prompt_text": "### PERSISTENT PROJECT MEMORY CONTEXT ###\n\n#### Active Project Facts:\n- [fact_gcp_tpu_v4] GCP TPU v4 instances offer 3.2x higher FLOPS per dollar for Transformer training. (Confidence: 0.92)\n\n#### Domain Research Heuristics (cloud_computing):\n  - Untrusted Source Domains: unverified-cloud-blog.com\n  - Effective Query Templates: {provider} benchmark instance pricing ML training"
}
```


