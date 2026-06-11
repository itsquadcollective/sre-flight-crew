# Runbook: MEMORY_SPIKE

## Symptoms

- Error token: MEMORY_SPIKE
- Log pattern: FATAL [system] MEMORY_SPIKE — service DOWN
- Failed requests logged as: -> 500 (MEMORY_SPIKE)
- Preceding signals:
  - WARN [cache] response cache entry count rising with no eviction policy hit
  - ERROR [runtime] MEMORY_SPIKE: heap usage critical, allocation failures in
    request handlers
  - FATAL [api] worker unresponsive >10s, returning HTTP 500

## Root Cause

The response cache grows unboundedly due to a missing or inactive eviction
policy, eventually consuming the majority of available heap memory. When heap
usage exceeds safe thresholds, the runtime begins failing memory allocations
inside request handlers. Worker processes become unresponsive and the API
returns HTTP 500 errors until the cache is cleared and memory is reclaimed.

## Recovery Action

clear_cache

## Verification

Recovery is confirmed when the following lines appear in sequence in
the log:

- INFO [recovery] executing 'clear_cache' ...
- INFO [recovery] 'clear_cache' succeeded — service RESTORED
- INFO [health] GET /health -> 200

The final health check returning 200 is the definitive signal that
the service is fully restored.
