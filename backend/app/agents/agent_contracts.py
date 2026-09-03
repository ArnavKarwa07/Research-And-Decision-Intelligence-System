"""Agent Contracts for RADIS (Research And Decision Intelligence System).
Defines explicit typed input, output, and state schemas for all production agents in accordance with AGENT_CONTRACTS.md and AGENTS.md.
"""
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ClaimType(str, Enum):
    FACT = "FACT"
    CALCULATION = "CALCULATION"
    INFERENCE = "INFERENCE"
    ASSUMPTION = "ASSUMPTION"
    PREDICTION = "PREDICTION"
    OPINION = "OPINION"
    UNRESOLVED = "UNRESOLVED"


class EvidenceSupportStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    INFERRED = "INFERRED"
    UNSUPPORTED = "UNSUPPORTED"


# --- Supervisor / Dynamic Planner Contract ---
class PlanSubTask(BaseModel):
    id: str
    task_type: str  # research, retrieval, evidence, synthesis, adversarial
    title: str
    objective: str
    dependencies: List[str] = Field(default_factory=list)
    assigned_agent: str
    status: str = "pending"  # pending, in_progress, completed, failed


class SupervisorInput(BaseModel):
    objective: str
    mode: str = "comprehensive"  # quick, comprehensive, deep_dive, comparative, exploratory, adversarial
    constraints: List[str] = Field(default_factory=list)
    decision_criteria: List[str] = Field(default_factory=list)
    max_budget_tokens: int = 50000


class SupervisorOutput(BaseModel):
    query_id: str
    objective: str
    plan: List[PlanSubTask]
    selected_agents: List[str]
    estimated_budget: Dict[str, Any]
    next_action: str


# --- Research Agent Contract ---
class SourceMetadata(BaseModel):
    url: str
    title: str
    publisher: Optional[str] = None
    quality_score: str = "MEDIUM"  # HIGH, MEDIUM, LOW
    retrieved_at: Optional[str] = None


class RawSnippet(BaseModel):
    content: str
    source: SourceMetadata
    query_used: str


class ResearchAgentInput(BaseModel):
    query: str
    mode: str = "comprehensive"
    num_results: int = 3
    existing_queries: List[str] = Field(default_factory=list)


class ResearchAgentOutput(BaseModel):
    search_queries: List[str]
    snippets: List[RawSnippet]
    sources: List[SourceMetadata]
    summary_message: str


# --- Retrieval Agent Contract ---
class RetrievalAgentInput(BaseModel):
    query: str
    project_id: Optional[str] = None
    top_k: int = 5


class DocumentChunk(BaseModel):
    chunk_id: str
    document_id: str
    content: str
    score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RetrievalAgentOutput(BaseModel):
    chunks: List[DocumentChunk]
    query_used: str
    total_retrieved: int


# --- Evidence Agent Contract ---
class AtomicClaim(BaseModel):
    id: str
    text: str
    claim_type: ClaimType
    confidence: float
    support_status: EvidenceSupportStatus
    source_url: Optional[str] = None
    source_title: Optional[str] = None
    excerpt: Optional[str] = None


class EvidenceAgentInput(BaseModel):
    raw_snippets: List[RawSnippet] = Field(default_factory=list)
    document_chunks: List[DocumentChunk] = Field(default_factory=list)


class EvidenceAgentOutput(BaseModel):
    claims: List[AtomicClaim]
    supported_count: int
    contradicted_count: int
    unresolved_count: int


# --- Synthesis Agent Contract ---
class AlternativeOption(BaseModel):
    name: str
    pros: List[str]
    cons: List[str]
    score: float


class DecisionMatrix(BaseModel):
    recommendation: str
    confidence: float
    rationale: str
    alternatives: List[AlternativeOption] = Field(default_factory=list)
    key_risks: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    decision_triggers: List[str] = Field(default_factory=list)


class SynthesisAgentInput(BaseModel):
    objective: str
    claims: List[AtomicClaim]
    sources: List[SourceMetadata]


class SynthesisAgentOutput(BaseModel):
    summary: str
    decision_matrix: Optional[DecisionMatrix] = None
    sources_used: List[SourceMetadata]
    confidence: float


# --- Adversarial Review Agent Contract ---
class AuditIssue(BaseModel):
    issue_id: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    category: str  # UNVALIDATED_CLAIM, WEAK_SOURCE, CONTRADICTION, RACE_CONDITION, EDGE_CASE, UI_INCONSISTENCY
    description: str
    assigned_agent: str
    recommendation: str


class AdversarialInput(BaseModel):
    objective: str
    claims: List[AtomicClaim]
    synthesis_summary: str
    confidence: float


class AdversarialOutput(BaseModel):
    audit_passed: bool
    confidence_adjusted: float
    issues: List[AuditIssue] = Field(default_factory=list)
    assessment_message: str

class FactCheckInput(BaseModel):
    claim: AtomicClaim
    existing_source_urls: List[str] = Field(default_factory=list)
    budget: int = 50000

class FactCheckOutput(BaseModel):
    verdict: str
    confidence_adjustment: float
    new_sources: List[SourceMetadata] = Field(default_factory=list)
    supporting_evidence: List[RawSnippet] = Field(default_factory=list)
    conflicting_evidence: List[RawSnippet] = Field(default_factory=list)

# --- Contradiction Agent Contract ---
class ContradictionDetail(BaseModel):
    claim_a_id: str
    claim_b_id: str
    contradiction_type: str
    severity: str
    description: str
    resolution_status: str
    resolution_notes: Optional[str] = None

class ContradictionAgentInput(BaseModel):
    claims: List[AtomicClaim]
    sources: List[SourceMetadata]
    query_id: str

class ContradictionAgentOutput(BaseModel):
    contradictions: List[ContradictionDetail]
    auto_resolved_count: int
    escalated_count: int
    unresolved_claims: List[str]
