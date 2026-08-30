# PRD.md

# Agentic Research & Decision Intelligence System

## 1. Product Summary

A general-purpose AI system that helps users research questions, validate information, analyze data, challenge assumptions, compare alternatives, and make evidence-backed decisions.

The primary interface is conversational, but the product is fundamentally a **research and decision workspace** with persistent projects, evidence, agent runs, sources, assumptions, and decisions.

The system should behave like a capable research team rather than a single chatbot.

## 2. Problem

Users can ask an LLM for an answer, but complex decisions require more than generation:

- Gathering information from multiple sources
- Distinguishing facts from assumptions and inferences
- Validating claims independently
- Detecting contradictory or outdated evidence
- Analyzing structured data
- Considering alternative explanations
- Stress-testing conclusions
- Understanding uncertainty and downside scenarios
- Keeping a durable record of how a conclusion was reached

Current AI assistants often fail by answering too early, trusting weak sources, collapsing uncertainty, or hiding their reasoning process.

## 3. Product Vision

Build an AI decision partner that can move from an ambiguous objective to a defensible recommendation through autonomous investigation, evidence validation, adversarial review, quantitative analysis, and transparent synthesis.

## 4. Target Users

### Primary
- Analysts
- Product managers
- Founders
- Strategy teams
- Consultants
- Researchers
- Engineers making architecture or technology decisions
- Students and professionals doing deep research

### Secondary
- Operations teams
- Investment and business development teams
- Knowledge workers with large internal document collections

## 5. Core User Jobs

1. Research a topic deeply.
2. Validate whether a claim is true.
3. Compare multiple options against constraints.
4. Investigate why a metric or event changed.
5. Test a hypothesis.
6. Combine internal documents with external information.
7. Analyze structured data.
8. Stress-test a proposed decision.
9. Maintain a reusable research trail.
10. Monitor a decision topic for material changes.

## 6. Product Principles

- Evidence before confidence.
- Facts, calculations, inferences, assumptions, predictions, and opinions must be distinguishable.
- Agents should decide what work is needed rather than follow a rigid workflow.
- More agents are not inherently better. Agent selection must be justified by task requirements.
- The system should stop researching when marginal information value is low or budget limits are reached.
- Important conclusions should be challengeable and traceable.
- The system must surface uncertainty rather than manufacture certainty.
- The UI should expose useful progress without becoming a developer trace viewer.

## 7. Core Experience

### 7.1 User starts with an objective

Example:
"Should we move our ML workloads from AWS to GCP? We have a five-person ML team, already use AWS, and want to keep infrastructure costs below $5k/month."

### 7.2 System interprets the objective

The system extracts:
- Goal
- Alternatives
- Constraints
- Decision criteria
- Time horizon
- Known assumptions
- Missing critical information

### 7.3 System builds an investigation plan

The plan can contain independent workstreams such as:
- Market research
- Internal knowledge retrieval
- Cost analysis
- Technical comparison
- Regulatory research
- Risk analysis

### 7.4 System executes dynamically

Agents and tools can be launched in parallel, sequentially, conditionally, or recursively.

### 7.5 Evidence is collected and normalized

Every material claim gets provenance, source metadata, confidence, and relationship to other claims.

### 7.6 System validates and challenges

The system checks for:
- Contradictions
- Missing evidence
- Weak sources
- Outdated information
- Unsupported inference
- Alternative explanations
- Sensitivity to assumptions

### 7.7 System synthesizes a decision

Output includes:
- Recommendation
- Rationale
- Evidence
- Major assumptions
- Risks
- Alternatives considered
- Confidence
- What could change the decision
- Suggested next actions

## 8. Product Modes

### Quick Answer
Low-complexity questions with minimal tool use.

### Research
Multi-source investigation with evidence collection.

### Deep Research
Autonomous investigation, contradiction detection, adversarial review, quantitative analysis, and iterative re-planning.

### Decision Analysis
Explicit alternatives, weighted criteria, scenarios, risk, and recommendation.

### Data Investigation
SQL/Python/statistical analysis over user-provided or connected data.

### Monitoring
Recurring checks against a prior evidence state or decision baseline.

## 9. MVP Scope

The MVP must establish the core agentic loop:

- Conversational task intake
- Task/project state
- Dynamic planning
- Web research
- Internal document RAG
- Evidence/claim store
- Source citations
- Basic contradiction checks
- Critic pass
- Final synthesis
- Run progress UI
- Persistent research session

The MVP should not attempt every enterprise connector or every advanced agent pattern.

## 10. Success Metrics

### Product
- Percentage of research tasks completed without manual orchestration
- Percentage of answers containing traceable evidence
- User-rated usefulness of recommendations
- User-rated trustworthiness
- Research completion rate
- Repeat usage per project

### Quality
- Claim support rate
- Citation correctness
- Evidence coverage
- Contradiction detection recall
- Hallucination rate
- Decision calibration

### Engineering
- P95 interactive response latency
- Deep-research task completion time
- Cost per completed task
- Tool failure rate
- Agent loop failure rate

## 11. Non-Goals

- Fully autonomous high-stakes decisions without human oversight
- Pretending to be a licensed financial, legal, medical, or other regulated professional
- Building a general AGI
- Replacing domain experts in decisions requiring professional accountability

## 12. Safety and Trust Requirements

- Untrusted web content must be treated as data, not instructions.
- Tool permissions must be explicit.
- Sensitive actions require user approval.
- Python execution must be sandboxed.
- PII must be protected.
- Research citations must be reproducible.
- The system must state when evidence is insufficient.

## 13. Future Direction

The long-term product should support:
- Enterprise knowledge connectors
- Browser automation
- Advanced quantitative modeling
- Decision monitoring
- Personal/project memory
- Multi-user collaboration
- Reusable research templates
- Agent performance learning
- Organization-wide knowledge graphs
