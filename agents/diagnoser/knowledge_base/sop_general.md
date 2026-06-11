# Standard Operating Procedure: QuadShop Production System

## System Overview

QuadShop is a simulated e-commerce platform running as a FastAPI web server.
The system serves a public website, a REST API for order management, and a
health-check endpoint used by the monitoring pipeline.

## Architecture

```
[Internet / Client]
       |
  [FastAPI Server]  (port 8090)
       |
  ├── GET  /            Landing page
  ├── GET  /health      Health check (200=ok, 500=down)
  ├── GET  /api/orders  Business endpoint (returns order data)
       |
  ├── [Database Layer]    PostgreSQL connection pool
  ├── [Cache Layer]       In-memory response cache
  └── [Runtime]           Python process with heap management
```

## Services and Failure Modes

### Database Layer
- **Normal state**: Connection pool serves queries with <100ms latency.
- **Failure mode (DB_CRASH)**: Connection pool exhaustion when a deadlock
  holds all connections. All upstream queries fail. API returns HTTP 500.
- **Recovery**: `restart_db` — releases stale locks, restarts the pool.
- **Log signatures**: `ERROR [db-pool]`, `deadlock detected`, `connection timed out`.

### Cache Layer
- **Normal state**: Response cache holds ~10K entries with eviction policy.
- **Failure mode (MEMORY_SPIKE)**: Cache grows unbounded when eviction fails.
  Heap usage exceeds 90%. GC thrashing causes worker unresponsiveness.
- **Recovery**: `clear_cache` — flushes the response cache, frees heap.
- **Log signatures**: `WARN [cache]`, `heap 97%`, `allocation failures`.

### Application Runtime
- **Normal state**: Workers process requests with <200ms response time.
- **Failure mode (service crash)**: Unhandled exceptions or worker death.
  The service stops responding entirely.
- **Recovery**: `restart_service` — restarts the application process.
- **Log signatures**: `FATAL [api]`, `worker unresponsive`, `service DOWN`.

## General Troubleshooting Methodology

When analyzing an incident with no direct runbook match:

1. **Identify the error level**: Is it WARN, ERROR, or FATAL?
   - WARN = degraded but functional → lower severity
   - ERROR = failing requests → investigate immediately
   - FATAL = service DOWN → highest priority

2. **Trace the causal chain**: Errors often cascade.
   - A database timeout may cause API 500 errors
   - Memory pressure may cause cache failures which cause OOM
   - Look for the FIRST error in the sequence — that is usually the root cause

3. **Map to the closest recovery action**:
   - Database-related errors → `restart_db`
   - Memory/cache-related errors → `clear_cache`
   - Application-level crashes → `restart_service`
   - Resource exhaustion → `scale_memory`
   - If genuinely unsure → `escalate_to_human`

4. **Assess confidence honestly**:
   - Direct runbook match with matching log patterns → 0.85-1.0
   - Partial match or reasonable inference → 0.6-0.84
   - Ambiguous or novel error → below 0.6 → escalate

## Log Format

All logs from the QuadShop server follow this format:

```
YYYY-MM-DDTHH:MM:SS+ZZZZ LEVEL [component] message
```

Example:
```
2026-06-11T03:14:22+0000 ERROR [db-pool] connection 14/15/16 timed out after 30000ms
2026-06-11T03:14:22+0000 FATAL [api] DB_CRASH: all upstream queries failing
```

## Health Check Contract

- `GET /health` returns `200 {"status": "ok"}` when healthy
- `GET /health` returns `500 {"status": "error", "error_type": "..."}` when down
- The Watchman polls this endpoint every few seconds
- Recovery is confirmed ONLY when health returns 200 again
