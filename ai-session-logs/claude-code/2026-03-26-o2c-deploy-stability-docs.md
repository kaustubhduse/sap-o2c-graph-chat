# 2026-03-26 - O2C deploy + stability + docs

## Objective
Set up and stabilize deployment for the O2C app (Render + Vercel + managed MySQL), fix frontend/backend integration issues, improve graph UX, and prepare project documentation/logging artifacts.

## Key prompts
- Deploy backend on Render and frontend on Vercel; include `nl-to-sql` with backend.
- Ensure `o2c-app` uses `nl-to-sql` inside backend.
- Run `graph-builder` after DB migration to Railway/Aiven.
- Fix frontend API base URL and CORS.
- Add README sections (architecture decisions, schema image, sample outputs, optional features).
- Add automation for exporting AI chat logs from `.jsonl` with redaction.

## Major decisions made
- Canonical NL-to-SQL path is `o2c-app/backend/nl-to-sql`.
- Backend now prefers `MYSQL_URL` / `DATABASE_URL` and normalizes provider URL format.
- Keep both API modes:
  - `POST /api/query` (non-stream)
  - `POST /api/query/stream` (SSE streaming)
- Keep startup resilient on Render (DB warm-up retries, non-fatal startup if DB is transient).
- Add AI log governance (`ai-session-logs/` structure + redaction workflow).

## Important fixes implemented
- **Backend import path:** forced to local `o2c-app/backend/nl-to-sql`.
- **DB connectivity:** added `MYSQL_URL` support; handled provider query-param incompatibilities.
- **Aiven loader issues:**
  - resolved `ssl-mode` arg issue for PyMySQL
  - handled `sql_require_primary_key=ON` during load session
- **Primary keys:** added surrogate PKs for all loaded tables in managed DB.
- **Frontend API URL:** switched to `VITE_API_URL` usage path.
- **CORS:** moved to env-driven origins (`FRONTEND_URL` / `CORS_ORIGINS`).
- **Streaming UX:** frontend now consumes SSE answer chunks and final payload.
- **Graph UX:** restored/adjusted fit behavior as requested over iterations; NodeDetail viewport constraints updated.
- **Render reliability:** runtime pinned to Python 3.11 via `o2c-app/backend/runtime.txt`.

## Files changed (high impact)
- `o2c-app/backend/main.py`
- `o2c-app/backend/runtime.txt`
- `o2c-app/backend/requirements.txt`
- `o2c-app/backend/nl-to-sql/chain.py`
- `o2c-app/backend/nl-to-sql/db.py`
- `o2c-app/backend/nl-to-sql/requirements.txt`
- `graph-builder/load_to_mysql.py`
- `graph-builder/requirements.txt`
- `o2c-app/frontend/src/hooks/useChat.js`
- `o2c-app/frontend/src/config.js`
- `o2c-app/frontend/src/components/GraphCanvas.jsx`
- `o2c-app/frontend/src/components/DraggableOverlay.jsx`
- `o2c-app/frontend/src/components/NodeDetail.jsx`
- `o2c-app/frontend/.env.example`
- `README.md`
- `.gitignore`
- `scripts/export_chat_logs.py`
- `ai-session-logs/summary.md`

## Outcome
- Backend live URL responded healthy and integrated with hosted MySQL.
- Frontend connected to backend through env-based API URL.
- Data loaded into managed MySQL and verified.
- README significantly expanded with architecture, deployment, schema, outputs, and logging guidance.
- Chat-log export automation with redaction is available and documented.

## Follow-up / next steps
- Keep Render env vars aligned with current DB provider (`MYSQL_URL`, CORS origins).
- Re-run `graph-builder/load_to_mysql.py` after source CSV updates.
- If reloading tables frequently on strict managed MySQL, automate post-load PK assignment.
- Optionally run `scripts/export_chat_logs.py` periodically to keep `ai-session-logs/cursor/` current.
