"""Unit tests for Persistent Project Memory Engine Services (Phase 12 Continuous Intelligence)."""
import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.base import Base
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
from app.services.heuristics_store_service import HeuristicsStoreService
from app.services.memory_context_injector import MemoryContextInjector
from app.services.project_memory_service import ProjectMemoryService


@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    await engine.dispose()


# --- 1. ProjectMemoryService Tests ---
@pytest.mark.asyncio
async def test_project_memory_service_crud_and_status_transitions(db_session: AsyncSession):
    service = ProjectMemoryService(db_session)
    proj_id = uuid.uuid4()
    sess_id = uuid.uuid4()

    # 1. Create memory items
    fact_in = ProjectMemoryItemCreate(
        project_id=proj_id,
        session_id=sess_id,
        memory_type=MemoryType.FACT.value,
        key="tam_2026",
        summary="Global TAM is $100B in 2026",
        content={"value_usd": 100000000000},
        confidence=0.95,
        human_approval_status=HumanApprovalStatus.APPROVED.value,
        tags=["market", "tam"],
    )
    fact_item = await service.create_memory_item(fact_in)
    assert fact_item.id is not None
    assert fact_item.key == "tam_2026"
    assert fact_item.memory_type == "FACT"
    assert fact_item.human_approval_status == "APPROVED"
    assert fact_item.validity_status == "ACTIVE"

    assump_in = ProjectMemoryItemCreate(
        project_id=proj_id,
        session_id=sess_id,
        memory_type=MemoryType.REUSABLE_ASSUMPTION.value,
        key="gpu_cost_drop",
        summary="GPU compute costs drop by 20% annually",
        confidence=0.8,
        human_approval_status=HumanApprovalStatus.PENDING.value,
        tags=["cost", "gpu"],
    )
    assump_item = await service.create_memory_item(assump_in)
    assert assump_item.human_approval_status == "PENDING"

    # 2. Get & List memory items
    item = await service.get_memory_item(fact_item.id)
    assert item is not None
    assert item.key == "tam_2026"

    items_list = await service.list_memory_items(project_id=proj_id)
    assert len(items_list) == 2

    # Filter by memory_type
    facts_only = await service.list_memory_items(project_id=proj_id, memory_type=MemoryType.FACT.value)
    assert len(facts_only) == 1
    assert facts_only[0].key == "tam_2026"

    # 3. Update approval status (PENDING -> APPROVED)
    approved_assump = await service.update_approval_status(
        assump_item.id, HumanApprovalStatus.APPROVED.value
    )
    assert approved_assump is not None
    assert approved_assump.human_approval_status == "APPROVED"

    # 4. Update validity status (ACTIVE -> INVALIDATED)
    invalidated_fact = await service.update_validity_status(
        fact_item.id, ValidityStatus.INVALIDATED.value
    )
    assert invalidated_fact is not None
    assert invalidated_fact.validity_status == "INVALIDATED"

    # 5. Update memory item details
    updated_item = await service.update_memory_item(
        assump_item.id,
        ProjectMemoryItemUpdate(summary="Updated GPU cost drop assumption", confidence=0.85),
    )
    assert updated_item is not None
    assert updated_item.summary == "Updated GPU cost drop assumption"
    assert updated_item.confidence == 0.85

    # 6. Delete memory item
    deleted = await service.delete_memory_item(fact_item.id)
    assert deleted is True
    assert await service.get_memory_item(fact_item.id) is None


# --- 2. HeuristicsStoreService Tests ---
@pytest.mark.asyncio
async def test_heuristics_store_service(db_session: AsyncSession):
    service = HeuristicsStoreService(db_session)
    proj_id = uuid.uuid4()

    # 1. Create heuristics
    h_in = ResearchHeuristicCreate(
        project_id=proj_id,
        domain="healthcare",
        untrusted_domains=["unverified-med-blog.com"],
        effective_query_templates=["{disease} clinical trial results 2026"],
        verified_tool_patterns=[{"tools": ["pub_med", "clinical_trials"]}],
        failure_modes=[{"reason": "Paywall on medical journal"}],
    )
    h_record = await service.create_or_update_heuristics(h_in)
    assert h_record.id is not None
    assert h_record.domain == "healthcare"
    assert "unverified-med-blog.com" in h_record.untrusted_domains

    # 2. Augment heuristics
    await service.add_untrusted_domain("healthcare", "fake-pharma.org", project_id=proj_id)
    await service.add_effective_query_template("healthcare", "{drug} FDA approval status", project_id=proj_id)
    await service.add_verified_tool_pattern("healthcare", {"tools": ["fda_drug_search"]}, project_id=proj_id)
    await service.add_failure_mode("healthcare", {"reason": "Expired drug patent link"}, project_id=proj_id)

    updated_h = await service.get_heuristics_by_domain("healthcare", project_id=proj_id)
    assert updated_h is not None
    assert "fake-pharma.org" in updated_h.untrusted_domains
    assert len(updated_h.effective_query_templates) == 2
    assert len(updated_h.verified_tool_patterns) == 2

    # List & Delete
    h_list = await service.list_heuristics(project_id=proj_id)
    assert len(h_list) == 1

    deleted = await service.delete_heuristics(updated_h.id)
    assert deleted is True
    assert await service.get_heuristics_by_domain("healthcare", project_id=proj_id) is None


# --- 3. MemoryContextInjector Tests ---
@pytest.mark.asyncio
async def test_memory_context_injector(db_session: AsyncSession):
    mem_service = ProjectMemoryService(db_session)
    heur_service = HeuristicsStoreService(db_session)
    injector = MemoryContextInjector(db_session)

    proj_id = uuid.uuid4()
    sess_id = uuid.uuid4()

    # 1. Populate Memory Items
    # Active & Approved Fact
    await mem_service.create_memory_item(
        ProjectMemoryItemCreate(
            project_id=proj_id,
            session_id=sess_id,
            memory_type=MemoryType.FACT.value,
            key="fact_1",
            summary="Fact 1 summary",
            confidence=0.9,
            human_approval_status=HumanApprovalStatus.APPROVED.value,
        )
    )

    # Prior Conclusion
    await mem_service.create_memory_item(
        ProjectMemoryItemCreate(
            project_id=proj_id,
            session_id=sess_id,
            memory_type=MemoryType.PRIOR_CONCLUSION.value,
            key="conclusion_1",
            summary="Prior conclusion summary",
            human_approval_status=HumanApprovalStatus.NOT_REQUIRED.value,
        )
    )

    # Reusable Assumption
    await mem_service.create_memory_item(
        ProjectMemoryItemCreate(
            project_id=proj_id,
            session_id=sess_id,
            memory_type=MemoryType.REUSABLE_ASSUMPTION.value,
            key="assump_1",
            summary="Assumption 1 summary",
            human_approval_status=HumanApprovalStatus.APPROVED.value,
        )
    )

    # Rejected Item (should be excluded)
    await mem_service.create_memory_item(
        ProjectMemoryItemCreate(
            project_id=proj_id,
            session_id=sess_id,
            memory_type=MemoryType.FACT.value,
            key="rejected_fact",
            summary="Bad fact summary",
            human_approval_status=HumanApprovalStatus.REJECTED.value,
        )
    )

    # Lesson Learned
    await mem_service.create_memory_item(
        ProjectMemoryItemCreate(
            project_id=proj_id,
            session_id=sess_id,
            memory_type=MemoryType.LESSON_LEARNED.value,
            key="lesson_1",
            summary="Always check primary sources",
            human_approval_status=HumanApprovalStatus.NOT_REQUIRED.value,
        )
    )

    # Domain Heuristic
    await heur_service.create_or_update_heuristics(
        ResearchHeuristicCreate(
            project_id=proj_id,
            domain="finance",
            untrusted_domains=["spam-stock-forum.com"],
            effective_query_templates=["{ticker} 10-K SEC filing"],
        )
    )

    # 2. Build Memory Context
    ctx = await injector.build_memory_context(project_id=proj_id, session_id=sess_id, domain="finance")
    assert len(ctx.active_facts) == 1
    assert ctx.active_facts[0].key == "fact_1"
    assert len(ctx.prior_conclusions) == 1
    assert len(ctx.reusable_assumptions) == 1
    assert len(ctx.lessons_learned) == 1
    assert ctx.heuristics is not None
    assert ctx.heuristics.domain == "finance"

    # 3. Format Context for Prompt Injection
    prompt_str = injector.format_context_for_prompt(ctx)
    assert "### PERSISTENT PROJECT MEMORY CONTEXT ###" in prompt_str
    assert "Active Project Facts:" in prompt_str
    assert "fact_1" in prompt_str
    assert "Prior Decision Trails & Conclusions:" in prompt_str
    assert "Validated Reusable Assumptions:" in prompt_str
    assert "Lessons Learned:" in prompt_str
    assert "Domain Research Heuristics (finance):" in prompt_str
    assert "spam-stock-forum.com" in prompt_str


@pytest.mark.asyncio
async def test_memory_context_injector_pending_and_rejected_filtering(db_session: AsyncSession):
    """BUG-12-01: Verify ONLY APPROVED and NOT_REQUIRED memory items are injected; PENDING and REJECTED items are blocked."""
    mem_service = ProjectMemoryService(db_session)
    injector = MemoryContextInjector(db_session)
    proj_id = uuid.uuid4()

    # Approved item
    await mem_service.create_memory_item(
        ProjectMemoryItemCreate(
            project_id=proj_id,
            memory_type=MemoryType.FACT.value,
            key="approved_fact",
            summary="Approved Fact",
            human_approval_status=HumanApprovalStatus.APPROVED.value,
        )
    )

    # Not Required item
    await mem_service.create_memory_item(
        ProjectMemoryItemCreate(
            project_id=proj_id,
            memory_type=MemoryType.REUSABLE_ASSUMPTION.value,
            key="not_req_assump",
            summary="Not Required Assumption",
            human_approval_status=HumanApprovalStatus.NOT_REQUIRED.value,
        )
    )

    # Pending item (MUST BE BLOCKED)
    await mem_service.create_memory_item(
        ProjectMemoryItemCreate(
            project_id=proj_id,
            memory_type=MemoryType.REUSABLE_ASSUMPTION.value,
            key="pending_assump",
            summary="Pending Assumption",
            human_approval_status=HumanApprovalStatus.PENDING.value,
        )
    )

    # Rejected item (MUST BE BLOCKED)
    await mem_service.create_memory_item(
        ProjectMemoryItemCreate(
            project_id=proj_id,
            memory_type=MemoryType.FACT.value,
            key="rejected_fact",
            summary="Rejected Fact",
            human_approval_status=HumanApprovalStatus.REJECTED.value,
        )
    )

    ctx = await injector.build_memory_context(project_id=proj_id)
    fact_keys = [f.key for f in ctx.active_facts]
    assump_keys = [a.key for a in ctx.reusable_assumptions]

    assert "approved_fact" in fact_keys
    assert "rejected_fact" not in fact_keys
    assert "not_req_assump" in assump_keys
    assert "pending_assump" not in assump_keys


@pytest.mark.asyncio
async def test_heuristics_store_tenant_isolation_when_project_id_none(db_session: AsyncSession):
    """BUG-12-06: Verify get_heuristics_by_domain(domain, project_id=None) returns only global heuristics."""
    service = HeuristicsStoreService(db_session)
    proj_id = uuid.uuid4()

    # Create project-specific heuristic
    await service.create_or_update_heuristics(
        ResearchHeuristicCreate(
            project_id=proj_id,
            domain="cybersecurity",
            untrusted_domains=["bad-sec-site.com"],
        )
    )

    # Query with project_id=None -> should NOT leak the project-specific heuristic
    global_h = await service.get_heuristics_by_domain("cybersecurity", project_id=None)
    assert global_h is None

    # Query with project_id -> should return project heuristic
    proj_h = await service.get_heuristics_by_domain("cybersecurity", project_id=proj_id)
    assert proj_h is not None
    assert "bad-sec-site.com" in proj_h.untrusted_domains
