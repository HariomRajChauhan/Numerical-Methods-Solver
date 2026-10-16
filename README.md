# Numerical Methods Solver

All-in-one web platform that solves numerical methods problems for engineering
students (ENSH 252, IOE / Tribhuvan University): final answer, exam-style
step-by-step working, interactive graphs, error/convergence info, and a
downloadable report.

## Stack

- **Frontend:** React + Vite + TypeScript, Tailwind CSS, React Router, Zustand,
  Plotly.js, KaTeX, mathjs (input preview/validation only)
- **Backend:** Python 3.11+, FastAPI, Pydantic v2, NumPy, SciPy, SymPy
- **Tests:** pytest (backend), Vitest (frontend)
- **Packaging:** Docker + docker-compose, `.env` config

## Quick start (local dev)

Backend:

```bash
cd backend
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e . --group dev   # or: pip install . && pip install pytest httpx ruff mypy
uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev            # http://localhost:5173, API base from .env
```

Copy `.env.example` to `.env` and adjust as needed.

## Quick start (Docker)

```bash
docker compose up --build
# frontend: http://localhost:5173   backend API: http://localhost:8000/api
```

## Checks

```bash
cd backend && ruff check . && mypy && pytest
cd frontend && npm run lint && npm test && npm run build
```

## Repository layout

See the folder structure in the project prompt: `backend/app` (core, api,
solvers per chapter, reports) and `frontend/src` (api, components, pages,
store, hooks, utils, types).

## How to add a new method

See the guide added in Phase 7.
