import time
import requests

BASE_URL = "http://localhost:8000"

faults = [
    "LATENCY_SPIKE",
    "LLM_FAILURE",
    "RAG_DEGRADATION",
    "TOOL_FAILURE",
    "COST_SPIKE",
    "AGENT_LOOP",
]

print("=== TRIGGERING ALL 6 FAULT TYPES ONE BY ONE ===")
results = []

for fault in faults:
    # 1. Reset simulation to normal
    requests.post(f"{BASE_URL}/api/simulation/reset")
    time.sleep(1)

    # 2. Inject fault
    inject_resp = requests.post(
        f"{BASE_URL}/api/simulation/inject",
        json={"fault_type": fault, "severity": "high", "duration_seconds": 30}
    )
    # Wait for tick to process and ML detection to create incident
    time.sleep(3)

    # 3. Fetch latest incidents
    inc_resp = requests.get(f"{BASE_URL}/api/incidents?limit=5")
    incidents = inc_resp.json()
    latest = incidents[0] if incidents else None

    if latest:
        results.append({
            "injected_fault": fault,
            "incident_id": latest.get("id"),
            "failure_type": latest.get("failure_type"),
            "confidence": latest.get("confidence"),
            "title": latest.get("title"),
        })
        print(f"[{fault:15}] -> Incident Failure Type: {latest.get('failure_type'):15} Conf: {latest.get('confidence')} Title: {latest.get('title')[:50]}")
    else:
        print(f"[{fault:15}] -> No incident found!")

# Reset to normal
requests.post(f"{BASE_URL}/api/simulation/reset")
print("\n=== COMPLETED LIVE FAULT TRIGGER TEST ===")
