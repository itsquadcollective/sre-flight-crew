# Dev Setup — SRE Flight Crew

Owned by the DevOps cell. Questions → WEBSTAR.

## Quick start

```bash
git clone <repo-url> && cd sre-flight-crew
python -m venv .venv
# Windows:  .venv\Scripts\activate     macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then fill in Azure values (agent devs only)
```

## Run the simulated production server (the "Target")

```bash
uvicorn simulator.mock_server:app --port 8090
```

> ⚠️ Windows often blocks port 8080 (Hyper-V reserved range, winerror 10013).
> We default to **8090** everywhere. If 8090 is also blocked, pick a free port,
> set it in `.env` (`MOCK_SERVER_PORT` + `HEALTH_CHECK_URL`), and pass it to uvicorn.
```bash
```

| Endpoint | Purpose |
|---|---|
| `GET /health` | 200 when healthy, 500 when crashed — the Watchman polls this |
| `GET /api/orders` | Sample business endpoint, 500s during a crash |
| `POST /sim/inject/{db_crash\|memory_spike}` | Crash the server |
| `POST /sim/recover/{restart_db\|clear_cache}` | Fix it (must match the failure, wrong action → 409) |
| `GET /sim/state` | JSON state for the dashboard |

Logs stream to `logs/server.log` — that file is the **Watchman's input**.
Failure error types in logs match `shared/schemas.py` → `ErrorEvent.error_type`
(`DB_CRASH`, `MEMORY_SPIKE`).

## Crash it / fix it

```bash
python -m simulator.failure_injector db_crash      # or memory_spike, or --random
bash agents/fixer/recovery_scripts/restart_db.sh   # what the Fixer agent runs
```

## Contracts — read before coding your agent

- **Data shapes:** `shared/schemas.py` (do NOT define your own — change it there)
- **Event topics:** `shared/event_bus.py` (`error.detected` → `error.diagnosed` → `error.fixed`)
- **Config/env:** import from `shared/config.py`, never `os.getenv` directly

Failure → recovery mapping (Diagnoser must output exactly these):

| error_type | recovery_action | script |
|---|---|---|
| `DB_CRASH` | `restart_db` | `agents/fixer/recovery_scripts/restart_db.sh` |
| `MEMORY_SPIKE` | `clear_cache` | `agents/fixer/recovery_scripts/clear_cache.sh` |

## Tests

```bash
pytest tests/ -v
```

## Git workflow

- `dev` is the integration branch — branch off it: `feature/<your-area>`
- PR into `dev`; keep `main` demo-ready
- Never commit `.env` (gitignored) — secrets stay local
