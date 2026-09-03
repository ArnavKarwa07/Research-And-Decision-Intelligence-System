"""Pydantic schemas."""
from .common import ErrorResponse, PaginatedResponse
from .session import SessionCreate, SessionResponse, SessionList
from .query import QueryCreate, QueryResponse, QueryStatus
from .evidence import EvidenceType, EvidenceResponse
from .source import SourceResponse
from .claim import (
    ClaimType, ClaimStatus, SupportType, ClaimCreate,
    ClaimResponse, ClaimSourceLinkCreate, ClaimSourceResponse
)
from .contradiction import (
    ContradictionType, ContradictionSeverity, ResolutionStatus,
    ContradictionResponse, ContradictionResolveRequest
)
from .source_group import SourceGroupType, SourceGroupResponse
from .document import DocumentResponse, DocumentChunkResponse
from .hypothesis import (
    HypothesisStatus, EvidenceRelationship, CritiqueSeverity, WeakEvidenceReason,
    EvidenceMapItem, EvidenceMapEntry, WeakEvidenceItem, MissingVariable, MissingVariableItem,
    HypothesisCreate, HypothesisUpdate, HypothesisResponse,
    CritiqueReportResponse,
    SelfChallengeRequest, SelfChallengeResponse
)

__all__ = [
    "ErrorResponse",
    "PaginatedResponse",
    "SessionCreate",
    "SessionResponse",
    "SessionList",
    "QueryCreate",
    "QueryResponse",
    "QueryStatus",
    "EvidenceType",
    "EvidenceResponse",
    "SourceResponse",
    "ClaimType",
    "ClaimStatus",
    "SupportType",
    "ClaimCreate",
    "ClaimResponse",
    "ClaimSourceLinkCreate",
    "ClaimSourceResponse",
    "ContradictionType",
    "ContradictionSeverity",
    "ResolutionStatus",
    "ContradictionResponse",
    "ContradictionResolveRequest",
    "SourceGroupType",
    "SourceGroupResponse",
    "DocumentResponse",
    "DocumentChunkResponse",
    "HypothesisStatus",
    "EvidenceRelationship",
    "CritiqueSeverity",
    "WeakEvidenceReason",
    "EvidenceMapItem",
    "EvidenceMapEntry",
    "WeakEvidenceItem",
    "MissingVariable",
    "MissingVariableItem",
    "HypothesisCreate",
    "HypothesisUpdate",
    "HypothesisResponse",
    "CritiqueReportResponse",
    "SelfChallengeRequest",
    "SelfChallengeResponse",
]
