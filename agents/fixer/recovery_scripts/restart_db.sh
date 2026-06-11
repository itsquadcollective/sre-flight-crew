#!/usr/bin/env bash
echo "[restart_db] Stopping PostgreSQL container..."
sleep 1
echo "[restart_db] Starting PostgreSQL container..."
curl -s -X POST http://localhost:8090/sim/recover/restart_db > /dev/null
sleep 1
echo "[restart_db] Database restarted successfully."