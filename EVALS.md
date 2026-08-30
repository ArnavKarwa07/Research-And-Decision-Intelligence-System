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

## 5. Human Evaluation

Use expert review for:
- Difficult research questions
- Ambiguous decisions
- Contradictory evidence
- High-impact recommendations

Reviewers should score evidence quality separately from writing quality.
