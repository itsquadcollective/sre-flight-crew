#!/usr/bin/env bash
# Recovery script: restart the (simulated) database service.
# Called by the Fixer agent when the Diagnoser returns recovery_action="restart_db".
set -euo pipefail

SERVER_URL="${MOCK_SERVER_URL:-http://127.0.0.1:8090}"

echo "[restart_db] stopping database service..."
sleep 1
echo "[restart_db] releasing stale locks on table 'orders'..."
sleep 1
echo "[restart_db] starting database service..."

HTTP_CODE=$(curl -s -o /tmp/restart_db_resp.json -w "%{http_code}" -X POST "$SERVER_URL/sim/recover/restart_db")
cat /tmp/restart_db_resp.json
echo ""

if [ "$HTTP_CODE" = "200" ]; then
    echo "[restart_db] ✓ recovery complete — service restored"
    exit 0
else
    echo "[restart_db] ✗ recovery failed (HTTP $HTTP_CODE)"
    exit 1
fi
