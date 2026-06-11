#!/usr/bin/env bash
echo "[restart_db] Stopping PostgreSQL container..."
sleep 1
echo "[restart_db] Starting PostgreSQL container..."
curl -s http://localhost:8080/inject/recover > /dev/null
sleep 1
echo "[restart_db] Database restarted successfully."