#!/usr/bin/env bash
# Recovery script: flush the (simulated) response cache to relieve memory pressure.
# Called by the Fixer agent when the Diagnoser returns recovery_action="clear_cache".
set -euo pipefail

SERVER_URL="${MOCK_SERVER_URL:-http://127.0.0.1:8090}"

echo "[clear_cache] flushing response cache..."
sleep 1
echo "[clear_cache] forcing garbage collection cycle..."

HTTP_CODE=$(curl -s -o /tmp/clear_cache_resp.json -w "%{http_code}" -X POST "$SERVER_URL/sim/recover/clear_cache")
cat /tmp/clear_cache_resp.json
echo ""

if [ "$HTTP_CODE" = "200" ]; then
    echo "[clear_cache] ✓ recovery complete — service restored"
    exit 0
else
    echo "[clear_cache] ✗ recovery failed (HTTP $HTTP_CODE)"
    exit 1
fi
