"""Unit tests for Phase 12 Specialized Agents and Orchestrator Graph Integration.

Verifies MonitoringAgent, MemoryAgent, Supervisor memory context injection,
and LangGraph state workflow execution per AGENTS.md rules.
"""
import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.base import Base
from app.models.project_memory import HumanApprovalStatus, MemoryType, ValidityStatus
from app.schemas.project_memory import ProjectMemoryItemCreate, ResearchHeuristicCreate
from app.services.heuristics_store_service import HeuristicsStoreService
from app.services.project_memory_service import ProjectMemoryService
from app.services.monitoring_scheduler_service import MonitoringSchedulerService
from app.schemas.monitoring import MonitoringJobCreate

from app.agents.monitoring_agent import MonitoringAgent
from app.agents.memory_agent import MemoryAgent
from app.agents.supervisor import SupervisorAgent, SupervisorInput
from app.agents.graph import create_langgraph_workflow, run_graph_with_controls, AgentState


@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    await engine.dispose()


# --- 1. MonitoringAgent Tests ---
@pytest.mark.asyncio
async def test_monitoring_agent_standalone_evaluation():
    agent = MonitoringAgent()
    input_data = {
        "job_id": str(uuid.uuid4()),
        "alert_threshold": 0.5,
        "current_state": {
            "sub_scores": {"s_assumption": 0.8, "s_contradiction": 0.8, "s_matrix": 0.8, "s_source": 0.8},
            "diffs": {"summary": "High drift"},
        },
    }

    step_res = await agent.step(input_data)
    assert step_res.should_continue is False
    assert "evaluate_delta_standalone" in step_res.action

    output = await agent.compile_output()
    assert output["job_id"] == input_data["job_id"]
    assert output["materiality_score"] >= 0.8
    assert output["materiality_level"] in ["HIGH", "CRITICAL"]
    assert output["alert_triggered"] is True
    assert output["status"] == "ALERT_TRIGGERED"


@pytest.mark.asyncio
async def test_monitoring_agent_db_backed_execution(db_session: AsyncSession):
    scheduler = MonitoringSchedulerService(db_session)
    job = await scheduler.create_job(
        MonitoringJobCreate(
            name="Test Market Job",
            interval_seconds=3600,
            alert_threshold=0.4,
        )
    )

    agent = MonitoringAgent(db_session=db_session)
    exec_res = await agent.execute({
        "job_id": str(job.id),
        "alert_threshold": 0.4,
        "current_state": {
            "sub_scores": {"s_assumption": 0.5, "s_contradiction": 0.5, "s_matrix": 0.5, "s_source": 0.5},
        },
    })

    assert exec_res["job_id"] == str(job.id)
    assert exec_res["materiality_score"] == 0.5
    assert exec_res["alert_triggered"] is True
    assert exec_res["status"] == "ALERT_TRIGGERED"
    assert exec_res["execution_log_id"] != ""


# --- 2. MemoryAgent Tests ---
@pytest.mark.asyncio
async def test_memory_agent_harvest_run_state(db_session: AsyncSession):
    agent = MemoryAgent(db_session=db_session)
    proj_id = str(uuid.uuid4())
    sess_id = str(uuid.uuid4())

    run_state = {
        "claims": [
            {"content": "Quantum processor qubit count reached 1000", "confidence": 0.95, "type": "FACT"},
            {"content": "Error rates reduced by 50%", "confidence": 0.9, "type": "FACT"},
        ],
        "decision_matrix": {
            "assumptions": [
                "Cooling costs remain under $1M annually",
                "Fiducial calibration takes under 2 hours",
            ]
        },
        "untrusted_domains": ["unverified-forum.org"],
        "effective_query_templates": ["quantum qubit benchmark {year}"],
    }

    res = await agent.execute({
        "action": "HARVEST",
        "project_id": proj_id,
        "session_id": sess_id,
        "domain": "quantum_computing",
        "run_state": run_state,
    })

    assert res["is_success"] is True
    assert res["action_performed"] == "HARVEST"
    items = res["items"]
    assert len(items) == 4  # 2 claims + 2 assumptions

    # Check that facts are APPROVED and assumptions are PENDING
    facts = [i for i in items if i["memory_type"] == "FACT"]
    assumptions = [i for i in items if i["memory_type"] == "REUSABLE_ASSUMPTION"]

    assert len(facts) == 2
    assert len(assumptions) == 2
    for f in facts:
        assert f["human_approval_status"] == "APPROVED"
    for a in assumptions:
        assert a["human_approval_status"] == "PENDING"


@pytest.mark.asyncio
async def test_memory_agent_crud_actions(db_session: AsyncSession):
    agent = MemoryAgent(db_session=db_session)
    proj_id = str(uuid.uuid4())

    # 1. STORE
    store_res = await agent.execute({
        "action": "STORE",
        "project_id": proj_id,
        "memory_type": "FACT",
        "memory_item": {
            "key": "market_size_key",
            "summary": "Market size is $50B",
            "confidence": 0.9,
        },
    })
    assert store_res["is_success"] is True
    item_id = store_res["items"][0]["id"]

    # 2. RETRIEVE
    ret_res = await agent.execute({
        "action": "RETRIEVE",
        "project_id": proj_id,
    })
    assert ret_res["is_success"] is True
    assert len(ret_res["items"]) >= 1

    # 3. INVALIDATE
    inv_res = await agent.execute({
        "action": "INVALIDATE",
        "memory_id": item_id,
    })
    assert inv_res["is_success"] is True


# --- 3. Supervisor & Graph Integration Tests ---
@pytest.mark.asyncio
async def test_supervisor_memory_context_injection():
    from unittest.mock import AsyncMock
    mock_llm = AsyncMock()
    mock_llm.generate_structured = AsyncMock(return_value=type("Plan", (), {"objectives": []})())

    agent = SupervisorAgent()
    agent.set_llm_provider(mock_llm)
    input_data = {
        "query_text": "Analyze quantum computing scalability",
        "session_id": str(uuid.uuid4()),
        "project_id": str(uuid.uuid4()),
        "domain": "tech",
    }

    step_res = await agent.step(input_data)
    assert step_res.action in ["plan_research", "spawn_agents", "cap_research", "error"]
    assert agent.internal_state["query"] == "Analyze quantum computing scalability"
    assert agent.internal_state["project_id"] == input_data["project_id"]
    assert agent.internal_state["domain"] == "tech"


@pytest.mark.asyncio
async def test_graph_workflow_execution_with_memory_and_monitoring():
    initial_state: AgentState = {
        "query_id": str(uuid.uuid4()),
        "text": "Evaluates continuous monitoring and project memory integration",
        "mode": "comprehensive",
        "plan": [],
        "steps": [],
        "snippets": [],
        "chunks": [],
        "claims": [{"id": "c1", "content": "System operational", "confidence": 0.95}],
        "scored_sources": [],
        "claim_source_links": [],
        "contradictions": [],
        "source_groups": [],
        "stale_source_ids": [],
        "fact_check_results": [],
        "verification_loop_count": 0,
        "decision_matrix": {"recommendation": "Deploy", "confidence": 0.9, "assumptions": ["API uptime > 99.9%"]},
        "data_analysis_results": None,
        "visualization_spec": None,
        "search_queries": [],
        "summary": "",
        "confidence": 0.9,
        "hypotheses": [],
        "falsification_results": [],
        "critique_report": None,
        "overall_severity": "LOW",
        "replan_count": 0,
        "max_replan_iterations": 3,
        "audit_passed": True,
        "audit_issues": [],
        "is_complete": False,
        "current_step": 0,
        "run_id": str(uuid.uuid4()),
        "is_paused": False,
        "is_cancelled": False,
        "pause_requested": False,
        "cancel_requested": False,
        "active_checkpoint_id": None,
        "project_id": str(uuid.uuid4()),
        "session_id": str(uuid.uuid4()),
        "domain": "software",
        "memory_context": None,
        "harvested_memory_items": None,
        "monitoring_job_id": None,
        "monitoring_output": None,
    }

    final_state = await run_graph_with_controls(initial_state, run_id=initial_state["run_id"])
    assert final_state["is_complete"] is True

    step_agent_types = [s["agent_type"] for s in final_state["steps"]]
    assert "Memory Agent" in step_agent_types
    assert "Monitoring Agent" in step_agent_types
    assert final_state.get("harvested_memory_items") is not None
    assert final_state.get("monitoring_output") is not None


@pytest.mark.asyncio
async def test_memory_agent_harvest_malformed_run_state_bug_12_13(db_session: AsyncSession):
    """Test MemoryAgent._harvest_run_state handles malformed claims and assumptions gracefully (BUG-12-13)."""
    agent = MemoryAgent(db_session=db_session)
    proj_id = str(uuid.uuid4())

    malformed_run_state = {
        "claims": [
            None,
            "Valid primitive claim string",
            12345,
            ["Nested claim 1", "Nested claim 2"],
            {"text": "Dict claim text", "confidence": "invalid_float_string", "type": ["list", "type"]},
            {"content": None},
        ],
        "decision_matrix": {
            "assumptions": [
                None,
                "Valid string assumption",
                42,
                ["Sub-assumption list item 1", "Sub-assumption list item 2"],
                {"text": "Dict assumption text"},
                {"summary": "Dict summary assumption"},
                {"other_key": "Unknown dict key assumption"},
            ]
        },
        "untrusted_domains": ["bad-site.com"],
        "effective_query_templates": ["query {template}"],
    }

    res = await agent.execute({
        "action": "HARVEST",
        "project_id": proj_id,
        "domain": "finance",
        "run_state": malformed_run_state,
    })

    assert res["is_success"] is True
    assert res["action_performed"] == "HARVEST"
    items = res["items"]
    assert len(items) > 0
    summaries = [item["summary"] for item in items]
    assert "Valid primitive claim string" in summaries
    assert "Valid string assumption" in summaries
    assert "Sub-assumption list item 1" in summaries


@pytest.mark.asyncio
async def test_execution_control_concurrency_bug_12_14():
    """Test ExecutionControl thread-safe and async lock protection (BUG-12-14)."""
    import asyncio
    from app.agents.graph import ExecutionControl

    run_ids = [f"run-concurrent-{i}" for i in range(50)]

    async def _toggle_status(run_id: str):
        await ExecutionControl.request_pause_async(run_id)
        assert ExecutionControl.get_status(run_id) == "paused"
        await ExecutionControl.request_resume_async(run_id)
        assert ExecutionControl.get_status(run_id) == "running"
        await ExecutionControl.request_cancel_async(run_id)
        assert ExecutionControl.get_status(run_id) == "cancelled"

    await asyncio.gather(*[_toggle_status(rid) for rid in run_ids])
    ExecutionControl.clear()


@pytest.mark.asyncio
async def test_tool_call_audit_logging_bug_12_15(caplog):
    """Test tool call audit logging in MonitoringAgent and MemoryAgent per Rule 9 (BUG-12-15)."""
    import logging
    caplog.set_level(logging.INFO)

    mon_agent = MonitoringAgent()
    await mon_agent.execute({
        "job_id": str(uuid.uuid4()),
        "alert_threshold": 0.5,
        "current_state": {"s_assumption": 0.9, "s_contradiction": 0.9, "s_matrix": 0.9, "s_source": 0.9},
    })

    assert any("[TOOL_AUDIT]" in record.message for record in caplog.records)

    mem_agent = MemoryAgent()
    await mem_agent.execute({
        "action": "STORE",
        "memory_type": "FACT",
        "memory_item": {"key": "test_audit_key", "summary": "Audit test summary"},
    })

    assert any("store_memory" in record.message for record in caplog.records)

