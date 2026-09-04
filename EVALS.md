# EVALS.md

# Evaluation Strategy

## 1. Goal

Evaluate not just whether the final answer sounds good, but whether the system researched correctly, used evidence correctly, selected appropriate tools, handled uncertainty, and produced a defensible decision.

## 2. Evaluation Layers

### Retrieval
- Recall@K
- Precision@K
- MRR
- NDCG
- Context precision
- Context recall

### Evidence
- Claim support rate
- Citation correctness
- Citation completeness
- Source quality
- Source independence
- Contradiction detection

### Agent
- Plan quality
- Tool-selection accuracy
- Tool-call correctness
- Agent trajectory quality
- Re-planning quality
- Budget efficiency

### Final Answer
- Correctness
- Faithfulness
- Relevance
- Completeness
- Calibration
- Actionability

### Decision
- Alternative coverage
- Risk coverage
- Assumption transparency
- Scenario robustness
- Recommendation quality

### Safety
- Prompt injection resistance
- Data leakage resistance
- Tool abuse resistance
- Sandbox escape resistance

## 3. Golden Dataset Structure

Each case should include:

```yaml
id: decision_001
objective: ...
constraints: [...]
required_sources: [...]
known_claims: [...]
contradictions: [...]
critical_assumptions: [...]
acceptable_decision_properties: [...]
```

## 4. Regression Policy

Every major change should run the regression suite.

Track:
- Overall score
- Per-component score
- Cost
- Latency
- Failure rate

A change that improves answer quality but materially increases unsafe behavior or cost should not automatically ship.

## 6. Phase 10 Implemented Evaluation & Observability Architecture

### Implemented Services & Engine Modules
- **`EvalMetricsEngine` (`eval_metrics_engine.py`)**: Computes `Precision@K`, `Recall@K`, `MRR`, `NDCG`, `Hallucination Rate`, `Faithfulness`, `Evidence Groundedness`, `Citation Coverage/Precision`, `Trajectory Efficiency`, `Tool Call Accuracy`, `Unnecessary Re-plan Penalty`, `MCDA Criteria Weight Alignment`, `Scenario Payoff Alignment`, and `Sensitivity Tipping Point Validity`.
- **`EvalBenchmarkService` (`eval_benchmark_service.py`)**: Golden dataset and test case CRUD management and pre-seeding for market analysis, technical feasibility, financial evaluation, and strategic decisions.
- **`OpenTelemetryService` (`open_telemetry_service.py`)**: Hierarchical span context tracing, in-memory buffering, and SSE span event streaming (`telemetry:span_started`, `telemetry:span_finished`).
- **`AgentTimelineService` (`agent_timeline_service.py`)**: Real-time Gantt execution timeline tracking and SSE payload generation (`telemetry:agent_timeline_step`).
- **`RegressionHarnessService` (`regression_harness_service.py`)**: Automated evaluation suite runner, baseline comparison, score delta computation, and pass/fail regression report generation.
- **`EvaluationAgent` (`evaluation_agent.py`)**: Specialist evaluation agent obeying `AGENTS.md` typed contracts.

### REST Endpoints (`/api/v1/eval` & `/api/v1/observability`)
- `POST /api/v1/eval/datasets/seed`: Pre-seed default golden benchmark datasets
- `POST /api/v1/eval/datasets`: Create golden dataset
- `GET /api/v1/eval/datasets`: List golden datasets
- `POST /api/v1/eval/datasets/{id}/cases`: Add ground-truth test case
- `POST /api/v1/eval/runs`: Trigger evaluation run
- `GET /api/v1/eval/runs/{id}`: Inspect evaluation report and metrics
- `POST /api/v1/eval/regression/compare`: Compare evaluation run against baseline
- `GET /api/v1/observability/traces/{run_id}`: Fetch OpenTelemetry trace summary
- `GET /api/v1/observability/timeline/{run_id}`: Fetch Gantt chart execution timeline
- `GET /api/v1/observability/metrics/dashboard`: Fetch token, USD cost, and latency (p50/p90/p99) metrics dashboard

