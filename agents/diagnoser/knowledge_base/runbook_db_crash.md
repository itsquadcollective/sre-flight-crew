# Runbook: DB_CRASH

## Symptoms

- Error token: DB_CRASH
- Log pattern: FATAL [system] DB_CRASH — service DOWN
- Failed requests logged as: -> 500 (DB_CRASH)
- Preceding signals:
  - ERROR [db-pool] connection timed out after 30000ms
  - ERROR [db-pool] deadlock detected on a table transaction
  - FATAL [api] DB_CRASH: all upstream queries failing, returning HTTP 500

## Root Cause

The database connection pool becomes fully exhausted and a deadlock is
detected on an active table transaction. With all connections held or
timed out, the API layer can no longer route any queries upstream and
begins returning HTTP 500 errors across all endpoints. The service
enters a DOWN state until the database is restarted and connections
are re-established.

**Classified as:** database_lock

## Recovery Action

restart_db

## Verification

Recovery is confirmed when the following lines appear in sequence in
the log:

- INFO [recovery] executing 'restart_db' ...
- INFO [recovery] 'restart_db' succeeded — service RESTORED
- INFO [health] GET /health -> 200

The final health check returning 200 is the definitive signal that
the service is fully restored.
