"""End-to-End Test Script for Phase 5 Self-Challenge Pipeline.
Executes complete adversarial self-challenge workflow:
  1. Session & Query creation
  2. Alternative hypothesis generation (3-7 competing hypotheses)
  3. Disconfirming query falsification per hypothesis
  4. Red-team critic audit report generation
  5. Full self-challenge pipeline with dynamic replanning & circuit breaker check
"""
import asyncio
import httpx
from httpx import AsyncClient, ASGITransport
import logging

from app.main import app
from app.db.engine import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_e2e_self_challenge")


async def run_e2e_self_challenge():
    logger.info("==================================================")
    logger.info(" Starting Phase 5 Self-Challenge E2E Verification ")
    logger.info("==================================================")

    await init_db()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test", timeout=60.0) as client:
        # Step 1: Create Session
        logger.info("\n1. Creating Research Session...")
        session_res = await client.post("/api/v1/sessions/", json={"title": "E2E Phase 5 Self-Challenge Test"})
        assert session_res.status_code == 201, f"Session creation failed: {session_res.text}"
        session = session_res.json()
        session_id = session["id"]
        logger.info(f"   [SUCCESS] Session created: {session_id}")

        # Step 2: Create Query
        logger.info("\n2. Submitting Investigation Query...")
        query_payload = {
            "text": "Analyze autonomous vehicle safety regulations and edge-case failure modes",
            "mode": "comprehensive"
        }
        query_res = await client.post(f"/api/v1/sessions/{session_id}/queries/", json=query_payload)
        assert query_res.status_code == 201, f"Query creation failed: {query_res.text}"
        query = query_res.json()
        query_id = query["id"]
        logger.info(f"   [SUCCESS] Query created: {query_id}")

        # Step 3: Generate Competing Hypotheses
        logger.info("\n3. Generating Competing Hypotheses...")
        hyp_res = await client.post(f"/api/v1/queries/{query_id}/hypotheses/generate")
        assert hyp_res.status_code == 201, f"Hypothesis generation failed: {hyp_res.text}"
        hypotheses = hyp_res.json()
        logger.info(f"   [SUCCESS] Generated {len(hypotheses)} hypotheses:")
        for h in hypotheses:
            logger.info(f"     - [{h['status'].upper()}] Confidence {h['confidence']}: {h['statement'][:70]}...")

        assert len(hypotheses) >= 3, "Fewer than 3 hypotheses generated!"
        first_hyp_id = hypotheses[0]["id"]

        # Step 4: Run Falsification Search for First Hypothesis
        logger.info(f"\n4. Triggering Falsification Search for Hypothesis {first_hyp_id}...")
        fals_res = await client.post(f"/api/v1/hypotheses/{first_hyp_id}/falsify")
        assert fals_res.status_code == 200, f"Falsification failed: {fals_res.text}"
        fals_data = fals_res.json()
        logger.info(f"   [SUCCESS] Falsification complete: Status={fals_data.get('status')}, Updated Confidence={fals_data.get('confidence')}")

        # Step 5: Trigger Red-Team Critique Pass
        logger.info("\n5. Executing Red-Team Critic Audit...")
        crit_res = await client.post(f"/api/v1/queries/{query_id}/critique")
        assert crit_res.status_code == 201, f"Critique pass failed: {crit_res.text}"
        critique = crit_res.json()
        logger.info(f"   [SUCCESS] Critic Report generated: Overall Severity={critique['overall_severity']}, Re-plan Recommended={critique['replan_triggered']}")
        logger.info(f"             Findings count: {len(critique['findings'])}, Recommendations: {len(critique['recommendations'])}")

        # Step 6: Fetch Critique Reports History
        logger.info("\n6. Fetching Critique Reports History...")
        crit_hist_res = await client.get(f"/api/v1/queries/{query_id}/critique")
        assert crit_hist_res.status_code == 200
        hist_data = crit_hist_res.json()
        logger.info(f"   [SUCCESS] Total Critique Reports: {hist_data['total']}")
        assert hist_data["total"] >= 1

        # Step 7: Execute Full Self-Challenge Pipeline
        logger.info("\n7. Executing Full Self-Challenge Pipeline with Replanning Loop...")
        self_challenge_payload = {
            "max_replan_iterations": 3,
            "confidence_threshold": 0.5
        }
        sc_res = await client.post(f"/api/v1/queries/{query_id}/self-challenge", json=self_challenge_payload)
        assert sc_res.status_code == 200, f"Self-challenge pipeline failed: {sc_res.text}"
        sc_data = sc_res.json()

        logger.info(f"   [SUCCESS] Self-Challenge Pipeline Completed:")
        logger.info(f"     - Query ID: {sc_data['query_id']}")
        logger.info(f"     - Final Status: {sc_data['final_status']}")
        logger.info(f"     - Re-plan Count: {sc_data['replan_count']}")
        logger.info(f"     - Finalized With Caveats: {sc_data['finalized_with_caveats']}")
        logger.info(f"     - Evaluated Hypotheses: {len(sc_data['hypotheses'])}")
        logger.info(f"     - Total Critique Reports: {len(sc_data['critique_reports'])}")

        assert "final_status" in sc_data
        assert sc_data["final_status"] in ("passed_cleanly", "finalized_with_caveats", "completed")
        logger.info("\n==================================================")
        logger.info(" [SUCCESS] Phase 5 E2E Self-Challenge Passed! ")
        logger.info("==================================================")

if __name__ == "__main__":
    asyncio.run(run_e2e_self_challenge())
