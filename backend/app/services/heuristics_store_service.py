"""Heuristics Store Service for Phase 12 Continuous Intelligence."""
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project_memory import ResearchHeuristics
from app.schemas.project_memory import ResearchHeuristicCreate

logger = logging.getLogger(__name__)


class HeuristicsStoreService:
    """
    Service for storing, retrieving, and augmenting domain-specific research heuristics,
    untrusted source domains, effective query templates, and verified tool execution patterns.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_heuristics_by_domain(
        self, domain: str, project_id: Optional[UUID] = None
    ) -> Optional[ResearchHeuristics]:
        """Fetch heuristics for a domain (and optional project_id)."""
        stmt = select(ResearchHeuristics).where(ResearchHeuristics.domain == domain)
        if project_id is not None:
            stmt = stmt.where(ResearchHeuristics.project_id == project_id)
        else:
            stmt = stmt.where(ResearchHeuristics.project_id.is_(None))

        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def create_or_update_heuristics(
        self, heuristic_in: ResearchHeuristicCreate
    ) -> ResearchHeuristics:
        """Create or update research heuristics for a given domain and project."""
        existing = await self.get_heuristics_by_domain(
            domain=heuristic_in.domain, project_id=heuristic_in.project_id
        )

        if existing:
            # Reassign list attributes to trigger SQLAlchemy JSON change tracking
            curr_untrusted = list(existing.untrusted_domains or [])
            for u in heuristic_in.untrusted_domains:
                if u not in curr_untrusted:
                    curr_untrusted.append(u)
            existing.untrusted_domains = curr_untrusted

            curr_templates = list(existing.effective_query_templates or [])
            for t in heuristic_in.effective_query_templates:
                if t not in curr_templates:
                    curr_templates.append(t)
            existing.effective_query_templates = curr_templates

            curr_patterns = list(existing.verified_tool_patterns or [])
            for p in heuristic_in.verified_tool_patterns:
                if p not in curr_patterns:
                    curr_patterns.append(p)
            existing.verified_tool_patterns = curr_patterns

            curr_failures = list(existing.failure_modes or [])
            for f in heuristic_in.failure_modes:
                if f not in curr_failures:
                    curr_failures.append(f)
            existing.failure_modes = curr_failures

            await self.db.commit()
            await self.db.refresh(existing)
            return existing

        heuristics = ResearchHeuristics(
            project_id=heuristic_in.project_id,
            session_id=heuristic_in.session_id,
            domain=heuristic_in.domain,
            untrusted_domains=heuristic_in.untrusted_domains or [],
            effective_query_templates=heuristic_in.effective_query_templates or [],
            verified_tool_patterns=heuristic_in.verified_tool_patterns or [],
            failure_modes=heuristic_in.failure_modes or [],
        )
        self.db.add(heuristics)
        await self.db.commit()
        await self.db.refresh(heuristics)
        return heuristics

    async def add_untrusted_domain(
        self, domain: str, untrusted_host: str, project_id: Optional[UUID] = None
    ) -> ResearchHeuristics:
        """Add an untrusted host domain to the specified domain heuristics."""
        heuristic_in = ResearchHeuristicCreate(
            project_id=project_id,
            domain=domain,
            untrusted_domains=[untrusted_host],
        )
        return await self.create_or_update_heuristics(heuristic_in)

    async def add_effective_query_template(
        self, domain: str, template: str, project_id: Optional[UUID] = None
    ) -> ResearchHeuristics:
        """Add an effective query template to the domain heuristics."""
        heuristic_in = ResearchHeuristicCreate(
            project_id=project_id,
            domain=domain,
            effective_query_templates=[template],
        )
        return await self.create_or_update_heuristics(heuristic_in)

    async def add_verified_tool_pattern(
        self, domain: str, pattern: Dict[str, Any], project_id: Optional[UUID] = None
    ) -> ResearchHeuristics:
        """Add a verified tool execution pattern sequence to the domain heuristics."""
        heuristic_in = ResearchHeuristicCreate(
            project_id=project_id,
            domain=domain,
            verified_tool_patterns=[pattern],
        )
        return await self.create_or_update_heuristics(heuristic_in)

    async def add_failure_mode(
        self, domain: str, failure_mode: Dict[str, Any], project_id: Optional[UUID] = None
    ) -> ResearchHeuristics:
        """Record a failure mode to avoid in domain research."""
        heuristic_in = ResearchHeuristicCreate(
            project_id=project_id,
            domain=domain,
            failure_modes=[failure_mode],
        )
        return await self.create_or_update_heuristics(heuristic_in)

    async def list_heuristics(
        self, project_id: Optional[UUID] = None
    ) -> List[ResearchHeuristics]:
        """List all research heuristics."""
        stmt = select(ResearchHeuristics)
        if project_id:
            stmt = stmt.where(ResearchHeuristics.project_id == project_id)

        stmt = stmt.order_by(ResearchHeuristics.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def delete_heuristics(self, heuristic_id: UUID) -> bool:
        """Delete research heuristics by ID."""
        result = await self.db.execute(
            select(ResearchHeuristics).where(ResearchHeuristics.id == heuristic_id)
        )
        heuristics = result.scalar_one_or_none()
        if not heuristics:
            return False

        await self.db.delete(heuristics)
        await self.db.commit()
        return True
