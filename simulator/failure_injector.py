"""Failure injector — the demo "chaos" button.

Usage:
    python -m simulator.failure_injector db_crash
    python -m simulator.failure_injector memory_spike
    python -m simulator.failure_injector --random
    python -m simulator.failure_injector --list
"""
import argparse
import random
import sys

import requests

from shared.config import MOCK_SERVER_URL

FAILURES = ["db_crash", "memory_spike", "service_crash"]


def inject(failure: str) -> int:
    try:
        r = requests.post(f"{MOCK_SERVER_URL}/sim/inject/{failure}", timeout=5)
    except requests.ConnectionError:
        print(f"✗ mock server not reachable at {MOCK_SERVER_URL} — start it first:")
        print("    uvicorn simulator.mock_server:app --port 8090")
        return 1
    if r.status_code != 200:
        print(f"✗ injection failed: {r.status_code} {r.text}")
        return 1
    data = r.json()
    print(f"💥 injected '{data['injected']}' ({data['error_type']}) — server is now DOWN")
    print(f"   state: {data['state']}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Inject a failure into the mock server")
    p.add_argument("failure", nargs="?", choices=FAILURES, help="failure to inject")
    p.add_argument("--random", action="store_true", help="pick a random failure")
    p.add_argument("--list", action="store_true", help="list available failures")
    args = p.parse_args()

    if args.list:
        print("\n".join(FAILURES))
        return 0
    failure = random.choice(FAILURES) if args.random else args.failure
    if not failure:
        p.print_help()
        return 1
    return inject(failure)


if __name__ == "__main__":
    sys.exit(main())
