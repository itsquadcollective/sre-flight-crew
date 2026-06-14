import time
import json
from typing import List, Dict, Any

# =====================================================================
# 1. DEFINE YOUR CURRENT SCENARIOS (GROUND TRUTH)
# =====================================================================
SCENARIOS: List[Dict[str, Any]] = [
    {
        "id": 1,
        "scenario_key": "DB_CRASH",
        "name": "Database Crash Scenario",
        "mock_logs": "[CRITICAL] PostgreSQL connection terminated unexpectedly. Code: 57P01. Shared memory segment corrupted.",
        "expected_fix": "restart_db"
    },
    {
        "id": 2,
        "scenario_key": "MEMORY_SPIKE",
        "name": "Memory Spike Scenario",
        "mock_logs": "[WARN] Heap memory usage at 96%. GC overhead limit exceeded. Worker pool throttling active.",
        "expected_fix": "clear_cache"
    }
]

# =====================================================================
# 2. MOCK DIAGNOSER FOR SIMULATION
# Replace this section with your actual Diagnoser agent call when ready!
# =====================================================================
class MockDiagnoser:
    def analyze(self, scenario_key: str, logs: str) -> str:
        # Simulating the exact strict JSON format required by the judges
        if scenario_key == "DB_CRASH":
            return json.dumps({
                "root_cause": "The PostgreSQL primary instance crashed unexpectedly due to a corrupted shared memory segment.",
                "recommended_fix": "restart_db",
                "confidence": 0.94
            })
        elif scenario_key == "MEMORY_SPIKE":
            return json.dumps({
                "root_cause": "The Redis cache is exhausted causing a critical memory leak.",
                "recommended_fix": "clear_cache",
                "confidence": 0.88
            })
        return "{}"

# =====================================================================
# 3. EVALUATION HARNESS VALIDATION LOGIC
# =====================================================================
def validate_response(raw_output: str, expected_fix: str) -> tuple[bool, str]:
    """Validates the output against the strict rules provided by the manager."""
    clean_output = raw_output.strip()
    
    # Rule 1: Strict JSON checks (No extra markdown backticks)
    if clean_output.startswith("```") or clean_output.endswith("
```"):
        return False, "Failed: Output contains markdown wrappers outside the JSON object."
        
    try:
        data = json.loads(clean_output)
    except json.JSONDecodeError:
        return False, "Failed: Output is not valid parseable JSON."

    root_cause = data.get("root_cause", "")
    recommended_fix = data.get("recommended_fix", "")
    confidence = data.get("confidence", 0.0)

    # Rule 2: recommended_fix matches exactly
    if recommended_fix != expected_fix:
        return False, f"Failed: Fix '{recommended_fix}' does not match expected '{expected_fix}'."

    # Rule 3: root_cause is a complete sentence (starts with capital, ends with punctuation)
    if not root_cause or not root_cause[0].isupper() or not root_cause.endswith(('.', '!', '?')):
        return False, "Failed: root_cause must be a complete sentence starting with a capital letter and ending with punctuation."

    # Rule 4: confidence is a decimal between 0.70 and 0.95
    if not isinstance(confidence, (int, float)) or not (0.70 <= confidence <= 0.95):
        return False, f"Failed: Confidence {confidence} is out of the required [0.70 - 0.95] boundary."

    return True, "Passed"

def run_evaluation():
    print("🚀 Starting SRE Flight Crew Automated Evaluation Harness...")
    print(f"Running {len(SCENARIOS)} configured production scenarios.\n")
    
    agent = MockDiagnoser() # TODO: Connect your actual agent instance here
    
    passed_count = 0
    total_time = 0.0
    results = []

    for case in SCENARIOS:
        print(f"Testing Case #{case['id']} [{case['scenario_key']}]: {case['name']}...")
        
        start_time = time.time()
        raw_agent_response = agent.analyze(case['scenario_key'], case['mock_logs'])
        elapsed_time = time.time() - start_time
        total_time += elapsed_time
        
        is_valid, status_msg = validate_response(raw_agent_response, case['expected_fix'])
        
        if is_valid:
            passed_count += 1
            status_icon = "✅"
        else:
            status_icon = "❌"
            print(f"🚨 ALERT! Validation failed for {case['scenario_key']}.")
            print(f"Returned Payload:\n{raw_agent_response}\nReason: {status_msg}\n")
            
        results.append({
            "id": case["id"],
            "name": case["name"],
            "status": status_icon,
            "notes": status_msg,
            "time": f"{elapsed_time * 1000:.1f}ms"
        })

    print("\n" + "="*75)
    print("FINAL EVALUATION METRICS RECORD")
    print("="*75)
    print(f"{'ID':<4} | {'Scenario Name':<25} | {'Status':<6} | {'Time':<8} | {'Notes':<25}")
    print("-"*75)
    for r in results:
        print(f"{r['id']:<4} | {r['name']:<25} | {r['status']:<6} | {r['time']:<8} | {r['notes']:<25}")
    print("="*75)
    
    success_rate = (passed_count / len(SCENARIOS)) * 100
    avg_latency = (total_time / len(SCENARIOS)) * 1000
    
    print(f"📊 Scenario Success Rate: {success_rate:.1f}% ({passed_count}/{len(SCENARIOS)})")
    print(f"⏱️  Average Recovery/Analysis Latency: {avg_latency:.1f} ms")
    print("="*75)

if __name__ == "__main__":
    run_evaluation()
