# TESTING.md

# Testing Strategy

## 1. Testing Layers

### Unit tests

Use deterministic unit tests for:
- Data transformations
- Budget calculations
- Source scoring
- Decision scoring
- State transitions
- Validation logic

### Contract tests

Verify every agent and tool obeys its schema.

### Integration tests

Test:
- API + database
- API + queue
- Agent + tool layer
- RAG ingestion + retrieval
- Run events + frontend stream

### End-to-end tests

Use representative scenarios from the evaluation dataset.

## 2. Agent Tests

For each agent test:
- Correct task selection
- Correct tool usage
- Invalid-tool handling
- Missing-data behavior
- Retry behavior
- Stop conditions
- Output schema

## 3. Adversarial Tests

Test:
- Prompt injection in web pages
- Prompt injection in PDFs
- Conflicting sources
- Misleading statistics
- Fake citations
- Tool failure
- Infinite-loop conditions
- Excessive tool use
- Malicious CSV/Python inputs

## 4. Regression Tests

Maintain a versioned benchmark suite.

Track:
- Final answer quality
- Claim support
- Citation accuracy
- Research coverage
- Agent cost
- Latency
- Safety failures

## 5. Evaluation Gates

A production release should fail when:
- Critical safety tests regress
- Citation correctness falls below baseline
- Unsupported-claim rate rises above threshold
- Critical tool contracts break
- Cost rises beyond accepted limit without a quality justification

## 6. Test Environments

- Local
- CI
- Staging
- Production smoke tests

Use deterministic mocks for external services in unit/integration tests and real providers in controlled evaluation runs.
