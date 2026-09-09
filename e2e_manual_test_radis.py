import asyncio
import logging
import json
import sys
import os

sys.path.insert(0, os.path.abspath("backend"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("e2e_manual_test")

async def test_fusion_query():
    logger.info("=== MANUAL TEST 1: Deep Tech / Physics Query ===")
    query_text = "Inertial Confinement Fusion Breakeven Scaling and Target Hybrid Architectures"
    
    from app.agents.graph import run_graph_with_controls
    
    initial_state = {
        "query_id": "manual-test-fusion-01",
        "text": query_text,
        "mode": "deep",
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
        "data_analysis_results": None,
        "visualization_spec": None,
        "search_queries": [],
        "summary": "",
        "confidence": 0.0,
        "hypotheses": [],
        "falsification_results": [],
        "critique_report": None,
        "overall_severity": "LOW",
        "replan_count": 0,
        "max_replan_iterations": 2,
        "audit_passed": True,
        "audit_issues": [],
        "is_complete": False,
        "current_step": 0,
        "run_id": "run-fusion-01",
        "domain": "Deep Tech / Physics"
    }

    try:
        final_state = await run_graph_with_controls(initial_state, run_id="run-fusion-01")
        logger.info("Graph execution finished successfully!")
        
        dm = final_state.get("decision_matrix", {})
        report = dm.get("research_report", "")
        
        print("\n" + "="*80)
        print("GENERATED EXECUTIVE RESEARCH REPORT:")
        print("="*80)
        print(report[:1500])
        print("\n... [Report Truncated for View] ...\n")
        
        # Validations
        assert "Executive Summary" in report or "Definitive Recommendation" in report, "Missing Executive Summary"
        assert "Comparison Table" in report or "|" in report, "Missing Comparison Table"
        assert "```mermaid" in report or "graph TD" in report, "Missing Mermaid Diagram"
        assert "Failure Scenario" in report or "Mitigation" in report, "Missing Failure Scenarios"
        assert "Tipping-Point" in report or "If" in report, "Missing Tipping Points"
        assert "Roadmap" in report or "Phase 1" in report, "Missing 3-Phase Roadmap"
        assert "Option 1: Core" not in report, "Leaked mechanical option title!"
        assert "regional buffer architecture" not in report.lower(), "Leaked generic boilerplate jargon!"
        
        print("[OK] All structural & visual markdown validations PASSED for Fusion Query!")
        return True
    except Exception as e:
        logger.error(f"Manual Test 1 Failed: {e}", exc_info=True)
        return False

async def test_software_query():
    logger.info("=== MANUAL TEST 2: Software Architecture Query ===")
    query_text = "Distributed Event-Driven Event Sourcing vs CQRS Architecture for Microservices"
    
    from app.agents.graph import run_graph_with_controls
    
    initial_state = {
        "query_id": "manual-test-software-02",
        "text": query_text,
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
        "data_analysis_results": None,
        "visualization_spec": None,
        "search_queries": [],
        "summary": "",
        "confidence": 0.0,
        "hypotheses": [],
        "falsification_results": [],
        "critique_report": None,
        "overall_severity": "LOW",
        "replan_count": 0,
        "max_replan_iterations": 2,
        "audit_passed": True,
        "audit_issues": [],
        "is_complete": False,
        "current_step": 0,
        "run_id": "run-software-02",
        "domain": "Software Architecture"
    }

    try:
        final_state = await run_graph_with_controls(initial_state, run_id="run-software-02")
        dm = final_state.get("decision_matrix", {})
        report = dm.get("research_report", "")
        
        print("\n" + "="*80)
        print("GENERATED SOFTWARE ARCHITECTURE REPORT:")
        print("="*80)
        print(report[:1200])
        print("\n... [Report Truncated for View] ...\n")

        try:
            assert "confidence" in report.lower(), "Missing confidence score"
            assert "Option 1: Strategic" not in report, "Leaked mechanical option title!"
            assert "supply chain optimization" not in report.lower(), "Leaked generic jargon!"
            print("[OK] All validations PASSED for Software Architecture Query!")
            return True
        except AssertionError as ae:
            logger.error(f"Software report assertion failed: {ae}. Full report content:\n{report}")
            return False
    except Exception as e:
        logger.error(f"Manual Test 2 Failed: {e}", exc_info=True)
        return False

async def main():
    t1 = await test_fusion_query()
    t2 = await test_software_query()
    
    if t1 and t2:
        print("\n" + "="*80)
        print("ALL MANUAL E2E INTEGRATION & REPORT FORMAT TESTS PASSED CLEANLY!")
        print("="*80)
        sys.exit(0)
    else:
        print("\n[FAIL] MANUAL E2E TESTS FAILED!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
