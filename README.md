# Dodge-AI — SAP Order-to-Cash (O2C) explorer

Monorepo for an O2C graph UI, natural-language-to-SQL chat (Groq + LangChain + MySQL), and supporting data pipelines.

## Repository layout

| Path | Purpose |
|------|--------|
| `o2c-app/frontend` | React + Vite app (force graph, chat) |
| `o2c-app/backend` | FastAPI API; NL→SQL pipeline lives in `o2c-app/backend/nl-to-sql/` |
| `graph-builder` | Graph assets; `load_to_mysql.py` loads entity CSVs into MySQL (uses backend `db` module) |
| `data-processing` | Preprocessing; entity CSVs under `data-processing/output/entities/` |

There is **no** top-level `nl-to-sql` folder; the canonical copy is **`o2c-app/backend/nl-to-sql`**.

## Prerequisites

- Python 3.11+ (recommended)
- Node.js 18+ (for the frontend)
- MySQL (local or hosted) with O2C tables populated

## Environment variables

Copy examples and fill in secrets (do **not** commit `.env` files).

**Backend** — `o2c-app/backend/.env`:

- `GROQ_API_KEY`, `GROQ_MODEL` — Groq LLM
- `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_NAME` — MySQL
- Optional: `LANGCHAIN_API_KEY`, `LANGCHAIN_TRACING_V2`, `LANGCHAIN_PROJECT` — LangSmith

The same `DB_*` values are read when running `graph-builder/load_to_mysql.py` (after loading `o2c-app/backend/.env`).

**Frontend** — `o2c-app/frontend/.env` (copy from `.env.example`):

- `VITE_API_URL` — backend base URL with **no** trailing slash (e.g. `https://sap-o2c-graph-chat.onrender.com` or `http://localhost:8000` for local dev).

On **Vercel** (or similar), set the same `VITE_API_URL` in the project environment variables; `.env` is gitignored and is not deployed from the repo by default.

## Local development

### Backend

```bash
cd o2c-app/backend
python -m venv venv
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Health check: `http://localhost:8000/api/health`

### Frontend

```bash
cd o2c-app/frontend
npm install
npm run dev
```

### Load CSVs into MySQL (optional)

From repo root, with `o2c-app/backend/.env` configured and entity CSVs present:

```bash
cd graph-builder
python -m venv venv && venv\Scripts\activate   # adjust for your OS
pip install -r requirements.txt
python load_to_mysql.py
```

## Deployment (summary)

- **Backend:** e.g. [Render](https://render.com) — root directory `o2c-app/backend`, build `pip install -r requirements.txt`, start `uvicorn main:app --host 0.0.0.0 --port $PORT`, set env vars on the host (no `.env` in Git).
- **Frontend:** e.g. [Vercel](https://vercel.com) — project root `o2c-app/frontend`, set production API URL to your deployed backend.
- **MySQL:** not provided by Render; use a managed MySQL service (e.g. [Railway](https://railway.app)) and set `DB_*` to match.

## Git and secrets

- This repo uses **`.gitignore` files** at the root and under major subfolders to exclude `venv/`, `node_modules/`, `.env`, caches, and editor noise.
- **Rotate any API keys or passwords** that were ever committed or shared before making the repository public.
