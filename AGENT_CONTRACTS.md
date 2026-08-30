# AGENT_CONTRACTS.md

# Agent Contracts

## 1. Contract Standard

Every production agent must implement the same high-level lifecycle:

```text
receive state
  ↓
inspect task
  ↓
choose next action
  ↓
use allowed tools
  ↓
validate result
  ↓
update structured state
  ↓
return status + result + next-step recommendation
```

## 2. Supervisor

### Input
- objective
- constraints
- current state
- prior findings
- budgets

### Output
- plan
- selected agents
- dependencies
- budgets
- next action
- completion decision

### Must not
- invent evidence
- silently resolve contradictions
- bypass approval gates

## 3. Research Agent

### Input
- research question
- source requirements
- current evidence gaps

### Output
- sources
- atomic claims
- evidence excerpts
- unresolved questions

### Stop when
- requested source coverage reached
- budget reached
- no meaningful new evidence found

## 4. Evidence Agent

### Input
- claims
- sources

### Output
- evidence links
- support status
- quality assessment
- independence assessment

## 5. Fact Checker

### Input
- target claim
- existing evidence

### Output
- verdict
- supporting evidence
- conflicting evidence
- confidence

## 6. Contradiction Agent

### Input
- conflicting claims
- associated sources

### Output
- contradiction classification
- explanation
- resolution or unresolved status

## 7. Data Agent

### Input
- question
- data source
- schema

### Output
- queries
- derived metrics
- analysis
- charts/artifacts
- limitations

## 8. Hypothesis Agent

### Input
- observation
- existing explanations

### Output
- alternative hypotheses
- discriminating evidence required
- investigation priorities

## 9. Critic Agent

### Input
- preliminary conclusion
- evidence
- assumptions

### Output
- objections
- unsupported claims
- missing variables
- counter-evidence
- recommendation for more research or acceptance

## 10. Decision Agent

### Input
- alternatives
- criteria
- evidence
- assumptions
- scenarios

### Output
- recommendation
- confidence
- trade-offs
- key risks
- decision triggers

## 11. Synthesis Agent

### Input
- verified evidence
- decision state

### Output
- final response
- citations
- assumptions
- uncertainty
- next actions

## 12. Shared Rules

Agents must never expose hidden chain-of-thought. User-visible explanations should summarize evidence, decisions, and uncertainty instead of revealing private reasoning traces.
