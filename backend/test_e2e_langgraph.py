import asyncio
import httpx
import json

BASE_URL = "http://127.0.0.1:8000/api/v1"

async def test_end_to_end():
    async with httpx.AsyncClient(timeout=60.0) as client:
        # 1. Create Session
        print("1. Creating session...")
        res = await client.post(f"{BASE_URL}/sessions/", json={"title": "End-to-End LangGraph Test"})
        assert res.status_code == 201, f"Failed session creation: {res.text}"
        session_id = res.json()["id"]
        print(f"   Session created: {session_id}")

        # 2. Submitting Query
        print("2. Submitting investigation query...")
        query_payload = {
            "text": "Analyze Q3 semiconductor supply chain risks and export controls",
            "mode": "deep"
        }
        res = await client.post(f"{BASE_URL}/sessions/{session_id}/queries/", json=query_payload)
        assert res.status_code == 201, f"Failed query creation: {res.text}"
        query_id = res.json()["id"]
        print(f"   Query created: {query_id}")

        # 3. Stream SSE Events
        print("3. Listening to SSE stream...")
        current_event_type = None
        
        async with client.stream("GET", f"{BASE_URL}/queries/{query_id}/stream") as response:
            async for line in response.aiter_lines():
                if line.startswith("event:"):
                    current_event_type = line[6:].strip()
                elif line.startswith("data:"):
                    raw_data = line[5:].strip()
                    if not raw_data:
                        continue
                    try:
                        payload = json.loads(raw_data)
                        event_type = payload.get("event_type") or current_event_type
                        event_data = payload.get("data", {})
                        
                        if event_type == "step":
                            print(f"   [SSE STEP] {event_data.get('agent_type')}: {event_data.get('message')}")
                        elif event_type == "complete":
                            print(f"   [SSE COMPLETE] Summary: {event_data.get('summary')}")
                            print(f"   [SSE COMPLETE] Evidence Items: {len(event_data.get('evidence', []))}")
                            break
                        elif event_type == "error":
                            print(f"   [SSE ERROR] {event_data.get('message')}")
                            break
                    except Exception as e:
                        print(f"   [PARSE ERROR] {e}")

        # 4. Verify Database Record
        print("4. Verifying database state...")
        await asyncio.sleep(2.0)
        res = await client.get(f"{BASE_URL}/sessions/{session_id}/queries/{query_id}")
        assert res.status_code == 200
        query_data = res.json()
        print(f"   Final Query Status: {query_data['status']}")
        print(f"   Final Summary: {query_data['summary']}")
        print(f"   Final Confidence: {query_data['confidence']}")

        # 5. Verify Evidence Record
        res = await client.get(f"{BASE_URL}/queries/{query_id}/evidence")
        assert res.status_code == 200
        evidence_list = res.json()
        print(f"   Fetched DB Evidence Count: {len(evidence_list)}")

if __name__ == "__main__":
    asyncio.run(test_end_to_end())
