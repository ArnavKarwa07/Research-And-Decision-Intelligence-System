"""
Pydantic schemas for Safety and Tool Security Framework (Phase 8).
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class ToolPermissionScope(BaseModel):
    agent_role: str = Field(..., description="Role of the agent (e.g., research, data_agent, supervisor)")
    allowed_tools: List[str] = Field(..., description="List of allowed tool names")
    denied_tools: List[str] = Field(default_factory=list, description="Explicitly forbidden tools")
    requires_approval: List[str] = Field(default_factory=list, description="Tools requiring HITL approval gate")


class PIIRedactionRequest(BaseModel):
    text: str = Field(..., description="Text content to scan and redact")


class PIIRedactionResponse(BaseModel):
    original_length: int
    sanitized_text: str
    redactions_count: int
    detected_types: List[str]


class PromptInjectionCheckRequest(BaseModel):
    content: str = Field(..., description="Untrusted text content to scan for prompt injections")
    source_type: str = Field("web", description="Type of source content (web, document, external_api)")


class PromptInjectionCheckResult(BaseModel):
    is_injection_detected: bool
    risk_score: float = Field(..., ge=0.0, le=1.0)
    flagged_patterns: List[str] = Field(default_factory=list)
    sanitized_content: str



class AuditLogEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: Optional[str] = None
    agent_id: Optional[str] = None
    action_type: str
    severity: str
    details: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None

