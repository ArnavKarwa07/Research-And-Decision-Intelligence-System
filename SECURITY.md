# SECURITY.md

# Security & Trust Model

## Threats

- Direct prompt injection
- Indirect prompt injection from web/document content
- Malicious files
- Tool abuse
- SQL injection
- Python sandbox escape
- Data exfiltration
- PII leakage
- Secret leakage
- Infinite agent loops
- Excessive tool cost
- Unauthorized actions

## Rules

1. Retrieved content is untrusted.
2. System and developer policies have priority over retrieved content.
3. Tools are allow-listed per agent.
4. Sensitive tools require approval.
5. SQL is parameterized where user input is involved.
6. Python execution is sandboxed.
7. Secrets never enter prompts unless explicitly required and controlled.
8. Tenant/project boundaries must be enforced at the database layer and application layer.
9. Every sensitive action is audited.
10. Rate and budget limits are mandatory.

## Data Classification

- Public
- Internal
- Confidential
- Restricted

Every connector and retrieval path should carry classification metadata.

## Security Test Suite

Maintain adversarial tests for:
- Web prompt injection
- Malicious PDFs
- Poisoned knowledge-base content
- Tool impersonation
- Data exfiltration attempts
- Sandbox escape attempts
- Cross-tenant retrieval
