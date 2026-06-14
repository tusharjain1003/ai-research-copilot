# AI Research Copilot

Prepare structured sales and business meeting research reports with a multi-step AI workflow. Enter a company name, website, and research objective, then watch a LangGraph pipeline plan, scrape, analyze, quality-check, and produce a 9-section report — with follow-up chat grounded in the research.

## Key Features

- **Session management** — create, list, and view research sessions
- **Multi-step LangGraph workflow** — 8 nodes: planner, source collection, analysis, risk/unknowns, quality check, enrichment loop, report generation, failure handling
- **Structured report** — Company Overview, Products & Services, Target Customers, Business Signals, Risks & Challenges, Discovery Questions, Outreach Strategy, Unknowns, Sources
- **Grounded follow-up chat** — ask questions about the research; answers are constrained to collected data
- **Persistent state** — sessions, workflow runs, steps, reports, and chat messages stored in SQLite
- **Intermediate progress** — frontend polls workflow status and displays step-by-step progress

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React, TypeScript, Vite, React Router, CSS Modules |
| Backend | Python, FastAPI, SQLAlchemy, SQLite, LangGraph |
| AI | OpenAI-compatible LLM (configurable via env vars) |

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- An OpenAI-compatible API key

### Setup

```bash
# Clone and enter the project
git clone <repo-url>
cd ai-research-copilot

# Backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
```

### Environment Variables

Create a `.env` file in `backend/` or set these directly:

| Variable | Default | Required | Description |
|---|---|---|---|
| `RESEARCH_COPILOT_LLM_API_KEY` | — | Yes | OpenAI-compatible API key |
| `RESEARCH_COPILOT_LLM_BASE_URL` | `https://api.openai.com/v1` | No | Custom API base URL |
| `RESEARCH_COPILOT_LLM_MODEL` | `gpt-4o-mini` | No | Model name |
| `RESEARCH_COPILOT_DATABASE_URL` | `sqlite:///./research.db` | No | Database URL |
| `RESEARCH_COPILOT_DEBUG` | `false` | No | Enable debug logging |

### Run

```bash
# Terminal 1 — Backend (from backend/)
uvicorn app.main:app --reload

# Terminal 2 — Frontend (from frontend/)
npm run dev
```

Open http://localhost:5173.

### Run Tests

```bash
cd backend
python -m pytest tests/ -v
```

## Demo Flow

1. Open http://localhost:5173
2. Click **New Session**
3. Enter company name (e.g. "Acme Corp"), website URL, and research objective
4. Click **Start Research**
5. Watch the workflow progress timeline update in real time (polling every 2s)
6. Review the generated structured report
7. Ask follow-up questions in the chat panel

## Limitations

- No JavaScript rendering — single-page app websites may yield minimal text
- Single website source — no multi-source research (news, social, etc.)
- No authentication — single-user by design
- Daemon threads for background work — not suitable for production scale
- LLM hallucinations are mitigated but not eliminated; unknown/unverifiable claims are flagged
