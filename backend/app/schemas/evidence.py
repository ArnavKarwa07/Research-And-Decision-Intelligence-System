"""Evidence Pydantic schemas."""
import uuid
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict, field_validator

class EvidenceType(str, Enum):
    """Enumeration of valid evidence types."""
    
    FACT = "FACT"
    CALCULATION = "CALCULATION"
    INFERENCE = "INFERENCE"
    ASSUMPTION = "ASSUMPTION"
    PREDICTION = "PREDICTION"
    OPINION = "OPINION"
    UNRESOLVED = "UNRESOLVED"
    
    fact = "fact"
    calculation = "calculation"
    inference = "inference"
    assumption = "assumption"
    prediction = "prediction"
    opinion = "opinion"
    unresolved = "unresolved"

class EvidenceResponse(BaseModel):
    """Schema for an evidence response."""
    
    id: uuid.UUID
    query_id: uuid.UUID
    content: str
    evidence_type: str
    confidence: float
    source_id: uuid.UUID | None = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
