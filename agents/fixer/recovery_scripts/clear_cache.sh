#!/usr/bin/env bash
echo "[clear_cache] Flushing cache..."
sleep 1
curl -s -X POST http://localhost:8090/sim/recover/clear_cache > /dev/null
echo "[clear_cache] Cache cleared successfully."