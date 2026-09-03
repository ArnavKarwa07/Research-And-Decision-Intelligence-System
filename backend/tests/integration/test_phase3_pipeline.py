import pytest
from app.agents.graph import create_langgraph_workflow

@pytest.mark.asyncio
async def test_phase3_pipeline():
    workflow = create_langgraph_workflow()
    
    initial_state = {
        "query_id": "test-query",
        "text": "Analyze the impact of AGI.",
        "mode": "comprehensive",
        "plan": [],
        "steps": [],
        "snippets": [],
        "chunks": [],
        "claims": [],
        "scored_sources": [],
        "claim_source_links": [],
        "contradictions": [],
        "source_groups": [],
        "stale_source_ids": [],
        "fact_check_results": [],
        "verification_loop_count": 0,
        "decision_matrix": None,
        "search_queries": [],
        "summary": "",
        "confidence": 0.0,
        "audit_passed": False,
        "audit_issues": [],
        "is_complete": False,
        "current_step": 0
    }
    
    final_state = None
    async for output in workflow.astream(initial_state):
        for node_name, state in output.items():
            final_state = state
            
    assert final_state is not None
    assert final_state.get("is_complete") is True
    assert "audit_passed" in final_state
    assert final_state.get("current_step") > 0
