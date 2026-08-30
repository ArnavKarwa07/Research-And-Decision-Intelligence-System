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

## Evidence

```http
GET /runs/{run_id}/claims
GET /runs/{run_id}/sources
GET /runs/{run_id}/contradictions
GET /runs/{run_id}/evidence-graph
```

## Decisions

```http
GET /runs/{run_id}/decision
POST /runs/{run_id}/decision/feedback
```

## Event Streaming

Use SSE initially for one-way UI updates.
Use WebSockets when bidirectional live control is required.

Example event:

```json
{
  "type": "agent.updated",
  "run_id": "run_123",
  "agent": "contradiction_agent",
  "status": "working",
  "message": "Comparing two conflicting revenue figures"
}
```
