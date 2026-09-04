"""Service layer for Decision Intelligence management."""
from typing import Any, Dict, List, Optional
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.decision import Decision
from app.models.query import Query
from app.schemas.decision import (
    DecisionCreateRequest,
    SensitivityRequest,
    ScenarioRequest,
)
from app.agents.decision import DecisionAgent
from app.tools.decision_tools import (
    run_scenario,
    run_sensitivity,
    calculate_expected_value,
)


class DecisionService:
    """Orchestrates decision analysis persistence, queries, sensitivity, and scenario updates."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_decision(self, data: DecisionCreateRequest) -> Decision:
        """Run decision agent analysis and save results to DB."""
        # 1. Verify target query exists
        query_res = await self.db.execute(select(Query).where(Query.id == data.query_id))
        query_obj = query_res.scalar_one_or_none()
        if not query_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Query with ID '{data.query_id}' not found."
            )

        alts_dicts = [a.model_dump() for a in data.alternatives]
        crits_dicts = [c.model_dump() for c in data.criteria]
        scenarios_dicts = [s.model_dump() for s in data.scenarios] if data.scenarios else []

        # 2. Run DecisionAgent analysis
        agent = DecisionAgent()
        agent_input = {
            "alternatives": alts_dicts,
            "criteria": crits_dicts,
            "scenarios": scenarios_dicts,
            "assumptions": data.assumptions or []
        }
        agent_output = await agent.run(agent_input)

        # 3. Create & persist Decision model
        decision = Decision(
            query_id=data.query_id,
            recommendation=agent_output.get("recommendation", "Option A"),
            confidence=float(agent_output.get("confidence", 0.80)),
            rationale=agent_output.get("rationale", ""),
            alternatives=agent_output.get("alternatives", alts_dicts),
            criteria=agent_output.get("criteria", crits_dicts),
            weighted_matrix=agent_output.get("weighted_matrix", {}),
            scenarios=agent_output.get("scenarios", {}),
            sensitivity_analysis=agent_output.get("sensitivity_analysis", {}),
            expected_values=agent_output.get("expected_values", {}),
            key_risks=agent_output.get("key_risks", []),
            assumptions=agent_output.get("assumptions", data.assumptions or []),
            decision_triggers=agent_output.get("decision_triggers", []),
            metadata_=data.metadata or {}
        )

        self.db.add(decision)
        await self.db.commit()
        await self.db.refresh(decision)
        return decision

    async def get_decision(self, decision_id: UUID) -> Optional[Decision]:
        """Fetch decision by ID."""
        result = await self.db.execute(select(Decision).where(Decision.id == decision_id))
        return result.scalar_one_or_none()

    async def list_decisions_for_query(self, query_id: UUID) -> List[Decision]:
        """List all decisions associated with a query."""
        result = await self.db.execute(
            select(Decision)
            .where(Decision.query_id == query_id)
            .order_by(Decision.created_at.desc())
        )
        return list(result.scalars().all())

    async def rerun_sensitivity(self, decision_id: UUID, req: SensitivityRequest) -> Optional[Decision]:
        """Re-run sensitivity analysis with custom delta and update decision record."""
        decision = await self.get_decision(decision_id)
        if not decision:
            return None

        alts = decision.alternatives or []
        crits = decision.criteria or []
        step_size = req.weight_delta

        res = run_sensitivity(alts, crits, step_size=step_size)
        decision.sensitivity_analysis = res

        await self.db.commit()
        await self.db.refresh(decision)
        return decision

    async def rerun_scenarios(self, decision_id: UUID, req: ScenarioRequest) -> Optional[Decision]:
        """Re-run scenario analysis with custom scenarios and update decision record."""
        decision = await self.get_decision(decision_id)
        if not decision:
            return None

        alts = decision.alternatives or []
        scenarios_dicts = [s.model_dump() for s in req.scenarios]

        res = run_scenario(alts, scenarios_dicts)
        decision.scenarios = res

        # Recalculate expected values if scenarios are returned
        try:
            sc_list = res.get("scenarios", [])
            if sc_list:
                ev_res = calculate_expected_value(sc_list)
                decision.expected_values = ev_res
        except Exception:
            pass

        await self.db.commit()
        await self.db.refresh(decision)
        return decision
