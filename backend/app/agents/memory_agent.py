"""Memory Agent for Project Memory & Research Heuristics (Phase 12).

Inspects finished research/decision run state, extracts durable facts and assumptions,
tags them, stores heuristics (untrusted domains, query templates), and submits
assumptions with human_approval_status = PENDING per AGENTS.md requirements.
"""
import logging
import uuid
from typing import Any, Dict, List, Optional, Union
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent, AgentConfig, StepResult
from app.agents.agent_contracts import MemoryAgentInput, MemoryAgentOutput
from app.models.project_memory import (
    HumanApprovalStatus,
    MemoryType,
    ValidityStatus,
)
from app.schemas.project_memory import (
    ProjectMemoryItemCreate,
    ProjectMemoryItemUpdate,
    ResearchHeuristicCreate,
)
from app.services.project_memory_service import ProjectMemoryService
from app.services.heuristics_store_service import HeuristicsStoreService
from app.services.memory_context_injector import MemoryContextInjector

logger = logging.getLogger(__name__)


class MemoryAgent(BaseAgent):
    """Specialist agent that manages long-term project memory, harvests durable facts,

    submits pending assumptions for HITL approval, and maintains domain heuristics.
    """

    def __init__(self, db_session: Optional[AsyncSession] = None, config: Optional[AgentConfig] = None):
        if config is None:
            config = AgentConfig(
                max_steps=5,
                max_tokens=10000,
                timeout_seconds=60,
                allowed_tools=["search_memory", "store_memory", "update_memory", "get_heuristics"],
            )
        super().__init__(config=config, agent_type="memory")
        self.db = db_session
        self._output_data: Optional[MemoryAgentOutput] = None

    async def step(self, input_data: Dict[str, Any]) -> StepResult:
        """Execute memory operations based on action requested."""
        try:
            if isinstance(input_data, MemoryAgentInput):
                validated_input = input_data
            else:
                action = str(input_data.get("action", "HARVEST")).upper()
                input_data["action"] = action
                validated_input = MemoryAgentInput(**input_data)
        except Exception as exc:
            logger.error(f"[MemoryAgent] Input validation error: {exc}")
            self._output_data = MemoryAgentOutput(
                is_success=False,
                action_performed=str(input_data.get("action", "UNKNOWN")),
                stop_reason="INPUT_VALIDATION_FAILED",
                message="Input validation failed.",
                error_message=str(exc),
            )
            return StepResult(
                action="error",
                result=self._output_data.model_dump(),
                tokens_used=10,
                should_continue=False,
                message=f"Validation failed: {exc}",
            )

        action = validated_input.action.upper()
        proj_uuid = uuid.UUID(validated_input.project_id) if validated_input.project_id else None
        sess_uuid = uuid.UUID(validated_input.session_id) if validated_input.session_id else None

        if action == "HARVEST":
            return await self._harvest_run_state(validated_input, input_data, proj_uuid, sess_uuid)
        elif action == "STORE":
            return await self._store_memory_item(validated_input, proj_uuid, sess_uuid)
        elif action == "RETRIEVE":
            return await self._retrieve_memory_context(validated_input, proj_uuid, sess_uuid)
        elif action == "UPDATE":
            return await self._update_memory_item(validated_input)
        elif action == "INVALIDATE":
            return await self._invalidate_memory_item(validated_input)
        elif action == "HEURISTIC_LOOKUP":
            return await self._lookup_heuristics(validated_input, proj_uuid)
        else:
            return await self._harvest_run_state(validated_input, input_data, proj_uuid, sess_uuid)

    async def _audit_tool_call(self, tool_name: str, input_data: Dict[str, Any]) -> Any:
        """Enforce AGENTS.md Rule 9 tool authorization, audit logging, and registry tracking."""
        if tool_name not in self.config.allowed_tools:
            logger.error(f"Agent '{self.state.agent_type}' attempted unauthorized tool call: '{tool_name}'")
            raise PermissionError(f"Agent '{self.state.agent_type}' not allowed to call tool: '{tool_name}'")

        logger.info(
            f"[TOOL_AUDIT] Agent '{self.state.agent_type}' (ID: {self.state.agent_id}) "
            f"invoking tool '{tool_name}' with params: {input_data}"
        )

        if self._tool_registry and hasattr(self._tool_registry, "call"):
            try:
                return await self.call_tool(tool_name, input_data)
            except Exception as exc:
                logger.warning(f"[TOOL_AUDIT] Tool registry call for '{tool_name}' encountered: {exc}")
        return None

    @staticmethod
    def _safe_extract_strings(raw_item: Any) -> List[str]:
        """Safely extract strings from primitive strings, dicts, or lists gracefully."""
        if raw_item is None:
            return []
        if isinstance(raw_item, str):
            cleaned = raw_item.strip()
            return [cleaned] if cleaned and cleaned.lower() != "none" else []
        if isinstance(raw_item, (int, float, bool)):
            return [str(raw_item)]
        if isinstance(raw_item, list):
            results = []
            for elem in raw_item:
                results.extend(MemoryAgent._safe_extract_strings(elem))
            return results
        if isinstance(raw_item, dict):
            text_val = (
                raw_item.get("text")
                or raw_item.get("summary")
                or raw_item.get("assumption")
                or raw_item.get("content")
                or raw_item.get("full_assumption")
            )
            if text_val is not None and text_val != raw_item:
                return MemoryAgent._safe_extract_strings(text_val)
            return [str(raw_item)]
        return [str(raw_item)]

    async def _harvest_run_state(
        self,
        validated_input: MemoryAgentInput,
        input_data: Dict[str, Any],
        proj_uuid: Optional[uuid.UUID],
        sess_uuid: Optional[uuid.UUID],
    ) -> StepResult:
        """Inspect finished research/decision run state, harvest durable facts and pending assumptions."""
        run_state = input_data.get("run_state") if isinstance(input_data, dict) else input_data
        if not isinstance(run_state, dict):
            run_state = {}

        raw_claims = run_state.get("claims", [])
        if not isinstance(raw_claims, list):
            raw_claims = [raw_claims] if raw_claims is not None else []

        decision_matrix = run_state.get("decision_matrix") or {}
        if not isinstance(decision_matrix, dict):
            decision_matrix = {}

        raw_assumptions = decision_matrix.get("assumptions") or run_state.get("assumptions", [])
        if not isinstance(raw_assumptions, list):
            raw_assumptions = [raw_assumptions] if raw_assumptions is not None else []

        domain = validated_input.domain or run_state.get("domain", "general")

        harvested_items: List[Dict[str, Any]] = []

        # 1. Harvest durable facts from verified claims
        for idx, claim in enumerate(raw_claims):
            if isinstance(claim, dict):
                extracted = MemoryAgent._safe_extract_strings(
                    claim.get("content") or claim.get("text") or claim.get("summary") or claim
                )
                c_content = extracted[0] if extracted else ""
                conf_val = claim.get("confidence", 0.9)
                try:
                    c_conf = float(conf_val) if conf_val is not None else 0.9
                except (ValueError, TypeError):
                    c_conf = 0.9
                raw_type = claim.get("type") or claim.get("claim_type") or "FACT"
                c_type = str(raw_type) if not isinstance(raw_type, (dict, list)) else "FACT"
            else:
                extracted = MemoryAgent._safe_extract_strings(claim)
                c_content = extracted[0] if extracted else ""
                c_conf = 0.9
                c_type = "FACT"

            if not c_content:
                continue

            item_key = f"fact_{int(uuid.uuid4().int % 1000000)}"
            item_dict = {
                "key": item_key,
                "memory_type": MemoryType.FACT.value,
                "summary": c_content[:255],
                "content": {"full_claim": c_content, "claim_type": c_type},
                "confidence": c_conf,
                "validity_status": ValidityStatus.ACTIVE.value,
                "human_approval_status": HumanApprovalStatus.APPROVED.value,
                "tags": ["harvested", "fact", str(domain)],
            }

            if self.db:
                item_create = ProjectMemoryItemCreate(
                    project_id=proj_uuid,
                    session_id=sess_uuid,
                    memory_type=MemoryType.FACT.value,
                    key=item_key,
                    summary=c_content[:255],
                    content={"full_claim": c_content, "claim_type": c_type},
                    confidence=c_conf,
                    validity_status=ValidityStatus.ACTIVE.value,
                    human_approval_status=HumanApprovalStatus.APPROVED.value,
                    tags=["harvested", "fact", str(domain)],
                )
                service = ProjectMemoryService(self.db)
                db_item = await service.create_memory_item(item_create)
                harvested_items.append({
                    "id": str(db_item.id),
                    "key": db_item.key,
                    "summary": db_item.summary,
                    "memory_type": db_item.memory_type,
                    "human_approval_status": db_item.human_approval_status,
                })
            else:
                item_dict["id"] = str(uuid.uuid4())
                harvested_items.append(item_dict)

        # 2. Harvest reusable assumptions with human_approval_status = PENDING
        for idx, assump in enumerate(raw_assumptions):
            a_text_list = MemoryAgent._safe_extract_strings(assump)
            for a_text in a_text_list:
                if not a_text:
                    continue

                item_key = f"assumption_{int(uuid.uuid4().int % 1000000)}"
                item_dict = {
                    "key": item_key,
                    "memory_type": MemoryType.REUSABLE_ASSUMPTION.value,
                    "summary": a_text[:255],
                    "content": {"full_assumption": a_text},
                    "confidence": 0.8,
                    "validity_status": ValidityStatus.ACTIVE.value,
                    "human_approval_status": HumanApprovalStatus.PENDING.value,
                    "tags": ["harvested", "assumption", str(domain)],
                }

                if self.db:
                    item_create = ProjectMemoryItemCreate(
                        project_id=proj_uuid,
                        session_id=sess_uuid,
                        memory_type=MemoryType.REUSABLE_ASSUMPTION.value,
                        key=item_key,
                        summary=a_text[:255],
                        content={"full_assumption": a_text},
                        confidence=0.8,
                        validity_status=ValidityStatus.ACTIVE.value,
                        human_approval_status=HumanApprovalStatus.PENDING.value,
                        tags=["harvested", "assumption", str(domain)],
                    )
                    service = ProjectMemoryService(self.db)
                    db_item = await service.create_memory_item(item_create)
                    harvested_items.append({
                        "id": str(db_item.id),
                        "key": db_item.key,
                        "summary": db_item.summary,
                        "memory_type": db_item.memory_type,
                        "human_approval_status": db_item.human_approval_status,
                    })
                else:
                    item_dict["id"] = str(uuid.uuid4())
                    harvested_items.append(item_dict)

        # 3. Store/Update domain research heuristics if domain provided
        heuristic_dict = None
        untrusted = run_state.get("untrusted_domains", []) if isinstance(run_state, dict) else []
        templates = run_state.get("effective_query_templates", []) if isinstance(run_state, dict) else []
        if self.db and domain and (untrusted or templates):
            h_service = HeuristicsStoreService(self.db)
            h_create = ResearchHeuristicCreate(
                project_id=proj_uuid,
                session_id=sess_uuid,
                domain=domain,
                untrusted_domains=untrusted,
                effective_query_templates=templates,
            )
            h_record = await h_service.create_or_update_heuristics(h_create)
            heuristic_dict = {
                "id": str(h_record.id),
                "domain": h_record.domain,
                "untrusted_domains": h_record.untrusted_domains,
                "effective_query_templates": h_record.effective_query_templates,
            }

        await self._audit_tool_call("store_memory", {"action": "HARVEST", "count": len(harvested_items)})
        if heuristic_dict:
            await self._audit_tool_call("get_heuristics", {"action": "SAVE_HEURISTICS", "domain": domain})

        msg = (
            f"Harvested {len(harvested_items)} memory items from run state. "
            f"Submitted assumptions with human_approval_status='PENDING'."
        )

        self._output_data = MemoryAgentOutput(
            is_success=True,
            action_performed="HARVEST",
            items=harvested_items,
            heuristic=heuristic_dict,
            stop_reason="OBJECTIVE_SATISFIED",
            message=msg,
        )

        return StepResult(
            action="harvest_run_state",
            result=self._output_data.model_dump(),
            tokens_used=100,
            should_continue=False,
            message=msg,
        )

    async def _store_memory_item(
        self,
        validated_input: MemoryAgentInput,
        proj_uuid: Optional[uuid.UUID],
        sess_uuid: Optional[uuid.UUID],
    ) -> StepResult:
        """Store a single project memory item."""
        mem_item = validated_input.memory_item or {}
        key = mem_item.get("key") or f"item_{uuid.uuid4().hex[:8]}"
        summary = mem_item.get("summary") or "Project memory item"
        mem_type = mem_item.get("memory_type") or validated_input.memory_type or MemoryType.FACT.value
        approval_status = mem_item.get("human_approval_status") or (
            HumanApprovalStatus.PENDING.value if mem_type == MemoryType.REUSABLE_ASSUMPTION.value else HumanApprovalStatus.APPROVED.value
        )

        if self.db:
            service = ProjectMemoryService(self.db)
            item_create = ProjectMemoryItemCreate(
                project_id=proj_uuid,
                session_id=sess_uuid,
                memory_type=mem_type,
                key=key,
                summary=summary,
                content=mem_item.get("content", {}),
                confidence=float(mem_item.get("confidence", 1.0)),
                validity_status=mem_item.get("validity_status", ValidityStatus.ACTIVE.value),
                human_approval_status=approval_status,
                tags=mem_item.get("tags", []),
            )
            created = await service.create_memory_item(item_create)
            stored_dict = {
                "id": str(created.id),
                "key": created.key,
                "summary": created.summary,
                "memory_type": created.memory_type,
                "human_approval_status": created.human_approval_status,
            }
        else:
            stored_dict = {
                "id": str(uuid.uuid4()),
                "key": key,
                "summary": summary,
                "memory_type": mem_type,
                "human_approval_status": approval_status,
            }

        await self._audit_tool_call("store_memory", {"action": "STORE", "key": key, "type": mem_type})

        msg = f"Stored memory item '{key}' ({mem_type}). Approval status: {approval_status}."
        self._output_data = MemoryAgentOutput(
            is_success=True,
            action_performed="STORE",
            items=[stored_dict],
            stop_reason="OBJECTIVE_SATISFIED",
            message=msg,
        )
        return StepResult(
            action="store_memory_item",
            result=self._output_data.model_dump(),
            tokens_used=50,
            should_continue=False,
            message=msg,
        )

    async def _retrieve_memory_context(
        self,
        validated_input: MemoryAgentInput,
        proj_uuid: Optional[uuid.UUID],
        sess_uuid: Optional[uuid.UUID],
    ) -> StepResult:
        """Retrieve structured memory context."""
        context_dict = None
        items_dict: List[Dict[str, Any]] = []

        if self.db:
            injector = MemoryContextInjector(self.db)
            ctx = await injector.build_memory_context(
                project_id=proj_uuid,
                session_id=sess_uuid,
                domain=validated_input.domain,
                query_text=validated_input.query,
            )
            context_dict = ctx.model_dump()
            items_dict = [f.model_dump() for f in ctx.active_facts] + [a.model_dump() for a in ctx.reusable_assumptions]

        await self._audit_tool_call("search_memory", {"action": "RETRIEVE", "domain": validated_input.domain, "query": validated_input.query})

        msg = f"Retrieved memory context for project {validated_input.project_id}."
        self._output_data = MemoryAgentOutput(
            is_success=True,
            action_performed="RETRIEVE",
            context=context_dict,
            items=items_dict,
            stop_reason="OBJECTIVE_SATISFIED",
            message=msg,
        )
        return StepResult(
            action="retrieve_memory_context",
            result=self._output_data.model_dump(),
            tokens_used=50,
            should_continue=False,
            message=msg,
        )

    async def _update_memory_item(self, validated_input: MemoryAgentInput) -> StepResult:
        """Update an existing memory item."""
        mem_id = validated_input.memory_id
        mem_item = validated_input.memory_item or {}
        updated_dict = {}

        if self.db and mem_id:
            service = ProjectMemoryService(self.db)
            up_create = ProjectMemoryItemUpdate(
                summary=mem_item.get("summary"),
                content=mem_item.get("content"),
                confidence=mem_item.get("confidence"),
                validity_status=mem_item.get("validity_status"),
                human_approval_status=mem_item.get("human_approval_status"),
                tags=mem_item.get("tags"),
            )
            up_item = await service.update_memory_item(uuid.UUID(mem_id), up_create)
            if up_item:
                updated_dict = {
                    "id": str(up_item.id),
                    "key": up_item.key,
                    "summary": up_item.summary,
                    "validity_status": up_item.validity_status,
                }

        await self._audit_tool_call("update_memory", {"action": "UPDATE", "memory_id": mem_id})

        msg = f"Updated memory item '{mem_id}'."
        self._output_data = MemoryAgentOutput(
            is_success=True,
            action_performed="UPDATE",
            items=[updated_dict] if updated_dict else [],
            stop_reason="OBJECTIVE_SATISFIED",
            message=msg,
        )
        return StepResult(
            action="update_memory_item",
            result=self._output_data.model_dump(),
            tokens_used=50,
            should_continue=False,
            message=msg,
        )

    async def _invalidate_memory_item(self, validated_input: MemoryAgentInput) -> StepResult:
        """Invalidate a memory item."""
        mem_id = validated_input.memory_id
        if self.db and mem_id:
            service = ProjectMemoryService(self.db)
            await service.update_validity_status(uuid.UUID(mem_id), ValidityStatus.INVALIDATED.value)

        await self._audit_tool_call("update_memory", {"action": "INVALIDATE", "memory_id": mem_id})

        msg = f"Invalidated memory item '{mem_id}'."
        self._output_data = MemoryAgentOutput(
            is_success=True,
            action_performed="INVALIDATE",
            stop_reason="OBJECTIVE_SATISFIED",
            message=msg,
        )
        return StepResult(
            action="invalidate_memory_item",
            result=self._output_data.model_dump(),
            tokens_used=30,
            should_continue=False,
            message=msg,
        )

    async def _lookup_heuristics(
        self, validated_input: MemoryAgentInput, proj_uuid: Optional[uuid.UUID]
    ) -> StepResult:
        """Lookup domain research heuristics."""
        domain = validated_input.domain or "general"
        h_dict = None
        if self.db:
            h_service = HeuristicsStoreService(self.db)
            h = await h_service.get_heuristics_by_domain(domain, project_id=proj_uuid)
            if h:
                h_dict = {
                    "id": str(h.id),
                    "domain": h.domain,
                    "untrusted_domains": h.untrusted_domains,
                    "effective_query_templates": h.effective_query_templates,
                }

        await self._audit_tool_call("get_heuristics", {"action": "HEURISTIC_LOOKUP", "domain": domain})

        msg = f"Looked up research heuristics for domain '{domain}'."
        self._output_data = MemoryAgentOutput(
            is_success=True,
            action_performed="HEURISTIC_LOOKUP",
            heuristic=h_dict,
            stop_reason="OBJECTIVE_SATISFIED",
            message=msg,
        )
        return StepResult(
            action="lookup_heuristics",
            result=self._output_data.model_dump(),
            tokens_used=40,
            should_continue=False,
            message=msg,
        )

    async def compile_output(self) -> Dict[str, Any]:
        """Compile final output."""
        if not self._output_data:
            self._output_data = MemoryAgentOutput(
                is_success=True,
                action_performed="NONE",
                stop_reason="OBJECTIVE_SATISFIED",
                message="No memory steps executed.",
            )
        return self._output_data.model_dump()

    async def execute(self, input_data: Union[Dict[str, Any], MemoryAgentInput]) -> Dict[str, Any]:
        """Direct execution interface returning MemoryAgentOutput dictionary."""
        if isinstance(input_data, MemoryAgentInput):
            inp_dict = input_data.model_dump()
        else:
            inp_dict = dict(input_data)
        await self.run(inp_dict)
        return await self.compile_output()
