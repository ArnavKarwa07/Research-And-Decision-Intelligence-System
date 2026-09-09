import asyncio
import httpx
import json
import sys

BASE_URL = "http://127.0.0.1:8000/api/v1"

async def run_e2e_verification():
    prompt = "Validate fusion energy net-gain claims and scaling benchmarks"
    print(f"=== Running E2E Verification for Prompt: '{prompt}' ===")
    
    async with httpx.AsyncClient(timeout=180.0) as client:
        # 1. Check health
        h_res = await client.get("http://127.0.0.1:8000/health")
        print(f"1. Health Check Response: {h_res.status_code} {h_res.json()}")
        assert h_res.status_code == 200, "Health check failed"

        # 2. Create Session
        s_res = await client.post(f"{BASE_URL}/sessions/", json={"title": "E2E Fusion Energy Verification"})
        assert s_res.status_code == 201, f"Session creation failed: {s_res.text}"
        session_id = s_res.json()["id"]
        print(f"2. Created Session ID: {session_id}")

        # 3. Create Query
        q_payload = {
            "text": prompt,
            "mode": "deep"
        }
        q_res = await client.post(f"{BASE_URL}/sessions/{session_id}/queries/", json=q_payload)
        assert q_res.status_code == 201, f"Query creation failed: {q_res.text}"
        query_id = q_res.json()["id"]
        print(f"3. Created Query ID: {query_id}")

        # 4. Stream SSE Events
        print("4. Streaming SSE events...")
        events = []
        async with client.stream("GET", f"{BASE_URL}/queries/{query_id}/stream") as response:
            async for line in response.aiter_lines():
                if line.startswith("data:"):
                    raw_data = line[5:].strip()
                    if not raw_data:
                        continue
                    try:
                        payload = json.loads(raw_data)
                        events.append(payload)
                        evt_type = payload.get("event_type")
                        data = payload.get("data", {})
                        if evt_type == "step":
                            agent = data.get("agent_type", "unknown")
                            msg = data.get("message", "")
                            print(f"   [STEP] ({agent}): {msg[:100]}")
                        elif evt_type == "complete":
                            print(f"   [COMPLETE] Summary: {data.get('summary', '')[:120]}...")
                            break
                        elif evt_type == "error":
                            print(f"   [ERROR] {data.get('message')}")
                            break
                    except Exception as e:
                        print(f"   [SSE Parse Error] {e} | line: {line}")

        # 5. Fetch completed query record
        print("5. Fetching completed Query record from DB...")
        query_data = {}
        for _ in range(30):
            res = await client.get(f"{BASE_URL}/sessions/{session_id}/queries/{query_id}")
            if res.status_code == 200:
                query_data = res.json()
                if query_data.get("status") in ["completed", "failed"]:
                    break
            await asyncio.sleep(1.0)
            
        print(f"   Query status: {query_data.get('status')}")

        # 6. Fetch Evidence items
        ev_res = await client.get(f"{BASE_URL}/queries/{query_id}/evidence")
        evidence_items = ev_res.json() if ev_res.status_code == 200 else []
        print(f"6. Fetched Evidence Items Count: {len(evidence_items)}")

        # Print all evidence URLs
        arxiv_count = 0
        live_web_count = 0
        total_urls = 0
        urls = []
        for ev in evidence_items:
            url = ev.get("url") or ev.get("source_url") or ""
            if url:
                urls.append(url)
                total_urls += 1
                if "arxiv.org" in url.lower():
                    arxiv_count += 1
                else:
                    live_web_count += 1
                print(f"   - Evidence URL: {url} | Title: {ev.get('title', '')[:60]}")

        print(f"\n--- URL Breakdown ---")
        print(f"Total Evidence URLs: {total_urls}")
        print(f"Live Web/News/Wiki URLs: {live_web_count}")
        print(f"arXiv URLs: {arxiv_count}")
        if total_urls > 0:
            web_ratio = (live_web_count / total_urls) * 100
            print(f"Live Web Percentage: {web_ratio:.1f}%")

        # Fetch Decision / Synthesis output (strategic options)
        print(f"\n--- Decision / Strategic Options Check ---")
        # Check synthesis or options in query_data or step data
        synthesized_data = query_data.get("result_data") or query_data.get("summary") or ""
        print(f"Summary / Synthesis Snippet:\n{str(synthesized_data)[:500]}")

        # Save details to file for inspection
        with open("e2e_output_log.json", "w") as f:
            json.dump({
                "query_data": query_data,
                "evidence_items": evidence_items,
                "events_count": len(events)
            }, f, indent=2)

if __name__ == "__main__":
    asyncio.run(run_e2e_verification())
