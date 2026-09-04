"""Memory Context Injector for Phase 12 Continuous Intelligence."""
import logging
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project_memory import (
    HumanApprovalStatus,
    MemoryType,
    ValidityStatus,
)
from app.schemas.project_memory import (
    ProjectMemoryContext,
    ProjectMemoryItemResponse,
    ResearchHeuristicResponse,
)
from app.services.heuristics_store_service import HeuristicsStoreService
from app.services.project_memory_service import ProjectMemoryService

logger = logging.getLogger(__name__)


class MemoryContextInjector:
    """
    Retrieves active, approved project memory items and domain heuristics,
    building a structured ProjectMemoryContext payload formatted for prompt context injection.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.memory_service = ProjectMemoryService(db)
        self.heuristics_service = HeuristicsStoreService(db)

    async def build_memory_context(
        self,
        project_id: Optional[UUID] = None,
        session_id: Optional[UUID] = None,
        domain: Optional[str] = None,
        query_text: Optional[str] = None,
    ) -> ProjectMemoryContext:
        """
        Retrieve active, approved facts, prior conclusions, reusable assumptions,
        lessons learned, and domain heuristics, constructing a ProjectMemoryContext.
        """
        items = await self.memory_service.list_memory_items(
            project_id=project_id,
            session_id=session_id,
            validity_status=ValidityStatus.ACTIVE.value,
        )

        active_facts: List[ProjectMemoryItemResponse] = []
        prior_conclusions: List[ProjectMemoryItemResponse] = []
        reusable_assumptions: List[ProjectMemoryItemResponse] = []
        lessons_learned: List[ProjectMemoryItemResponse] = []

        allowed_statuses = {
            HumanApprovalStatus.APPROVED.value,
            HumanApprovalStatus.NOT_REQUIRED.value,
        }
        for item in items:
            # Only inject items with human_approval_status in APPROVED or NOT_REQUIRED
            if item.human_approval_status not in allowed_statuses:
                continue

            resp = ProjectMemoryItemResponse.model_validate(item)

            if item.memory_type == MemoryType.FACT.value:
                active_facts.append(resp)
            elif item.memory_type in [MemoryType.DECISION_TRAIL.value, MemoryType.PRIOR_CONCLUSION.value]:
                prior_conclusions.append(resp)
            elif item.memory_type == MemoryType.REUSABLE_ASSUMPTION.value:
                reusable_assumptions.append(resp)
            elif item.memory_type == MemoryType.LESSON_LEARNED.value:
                lessons_learned.append(resp)

        heuristics_resp: Optional[ResearchHeuristicResponse] = None
        if domain:
            heuristics = await self.heuristics_service.get_heuristics_by_domain(
                domain=domain, project_id=project_id
            )
            if heuristics:
                heuristics_resp = ResearchHeuristicResponse.model_validate(heuristics)

        return ProjectMemoryContext(
            project_id=project_id,
            session_id=session_id,
            active_facts=active_facts,
            prior_conclusions=prior_conclusions,
            reusable_assumptions=reusable_assumptions,
            lessons_learned=lessons_learned,
            heuristics=heuristics_resp,
        )

    def format_context_for_prompt(self, context: ProjectMemoryContext) -> str:
        """
        Format a ProjectMemoryContext into a structured markdown string for agent prompt injection.
        """
        lines: List[str] = ["### PERSISTENT PROJECT MEMORY CONTEXT ###"]

        if context.active_facts:
            lines.append("\n#### Active Project Facts:")
            for f in context.active_facts:
                lines.append(f"- [{f.key}] {f.summary} (Confidence: {f.confidence:.2f})")

        if context.prior_conclusions:
            lines.append("\n#### Prior Decision Trails & Conclusions:")
            for c in context.prior_conclusions:
                lines.append(f"- [{c.key}] {c.summary}")

        if context.reusable_assumptions:
            lines.append("\n#### Validated Reusable Assumptions:")
            for a in context.reusable_assumptions:
                lines.append(f"- [{a.key}] {a.summary} (Status: {a.human_approval_status})")

        if context.lessons_learned:
            lines.append("\n#### Lessons Learned:")
            for l in context.lessons_learned:
                lines.append(f"- [{l.key}] {l.summary}")

        if context.heuristics:
            h = context.heuristics
            lines.append(f"\n#### Domain Research Heuristics ({h.domain}):")
            if h.untrusted_domains:
                lines.append(f"  - Untrusted Source Domains: {', '.join(h.untrusted_domains)}")
            if h.effective_query_templates:
                lines.append(f"  - Effective Query Templates: {', '.join(h.effective_query_templates)}")
            if h.verified_tool_patterns:
                lines.append(f"  - Verified Tool Execution Patterns Count: {len(h.verified_tool_patterns)}")
            if h.failure_modes:
                lines.append(f"  - Known Failure Modes Count: {len(h.failure_modes)}")

        if len(lines) == 1:
            return "### PERSISTENT PROJECT MEMORY CONTEXT ###\nNo prior active project memory records found."

        return "\n".join(lines)
