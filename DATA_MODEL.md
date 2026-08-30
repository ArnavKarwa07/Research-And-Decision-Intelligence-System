# DATA_MODEL.md

# Data Model

## Core entities

```text
User
  └── Project
        ├── Document
        ├── Task
        │    └── Run
        │         ├── AgentRun
        │         │    └── ToolCall
        │         ├── Source
        │         ├── Claim
        │         │    └── EvidenceLink
        │         ├── Hypothesis
        │         ├── Contradiction
        │         └── Decision
        └── Memory
```

## User

- id
- name
- email
- created_at
- preferences

## Project

- id
- user_id / owner_id
- name
- description
- status
- created_at
- updated_at

## Task

- id
- project_id
- title
- objective
- mode
- constraints
- decision_criteria
- status
- created_at

## Run

- id
- task_id
- status
- started_at
- completed_at
- model_config
- budget_config
- estimated_cost
- actual_cost
- confidence

## AgentRun

- id
- run_id
- agent_type
- parent_agent_run_id
- status
- input_ref
- output_ref
- started_at
- completed_at
- token_usage
- cost

## ToolCall

- id
- agent_run_id
- tool_name
- input
- output
- status
- latency_ms
- cost
- created_at

## Source

- id
- run_id / project_id
- uri
- title
- publisher
- source_type
- published_at
- retrieved_at
- content_hash
- quality_score
- independence_group

## Claim

- id
- run_id
- text
- claim_type
- status
- confidence
- created_by_agent_run_id

## EvidenceLink

- id
- claim_id
- source_id or artifact_id
- relationship
- strength
- excerpt
- location

## Contradiction

- id
- run_id
- claim_a_id
- claim_b_id
- status
- explanation
- resolution_confidence

## Hypothesis

- id
- run_id
- statement
- status
- confidence
- supporting_claim_ids
- contradicting_claim_ids

## Decision

- id
- run_id
- recommendation
- confidence
- alternatives
- criteria
- risks
- assumptions
- triggers
- rationale

## Artifact

Used for generated charts, reports, tables, datasets, and exported research packages.

- id
- run_id
- type
- storage_uri
- metadata
- created_at

## Memory

Memory should be explicitly typed:

- project_fact
- approved_assumption
- prior_decision
- research_finding
- operational_lesson

Every memory record needs source/reference provenance and a retention policy.
