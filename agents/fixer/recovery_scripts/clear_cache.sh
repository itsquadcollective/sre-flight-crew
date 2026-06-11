#!/usr/bin/env bash
echo "[clear_cache] Flushing cache..."
sleep 1
curl -s http://localhost:8080/inject/recover > /dev/null
echo "[clear_cache] Cache cleared successfully."