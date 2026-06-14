# AGENTS.md

## Project Mission

Build a production-quality but achievable AI Research Copilot for preparing sales or business meetings. The app must satisfy the assignment requirements: React frontend, Python/FastAPI backend, mandatory LangGraph workflow, persisted sessions/workflow outputs, structured research reports, follow-up chat, tests, and required documentation.

Treat all code as production code. Prefer small, focused, reversible changes. Do not over-engineer.

## Locked Stack Decisions

Never propose changing these locked decisions unless explicitly asked by the user.

### Frontend

- React + TypeScript
- Vite
- React Router
- Plain CSS or CSS Modules
- No heavy UI framework

### Backend

- Python + FastAPI
- Pydantic for request/response schemas
- SQLAlchemy for persistence
- SQLite for local persistence
- Uvicorn for local development

### AI Workflow

- LangGraph is mandatory and central.
- A single LLM call wrapped in an API is not acceptable.
- Use one workflow graph per research session.
- The graph must include multiple meaningful nodes, shared state, conditional routing, intermediate outputs, failure handling, and recoverability.
- Persist intermediate node outputs.

### LLM Integration

- Use an OpenAI-compatible chat model through environment variables.
- Do not hardcode API keys, model credentials, private URLs, or secrets.
- Fail clearly if required AI configuration is missing.
- Keep model access behind a small backend service/module so it can be swapped later.

### Workflow Execution

- Start workflow execution from a backend API.
- Use simple background task execution.
- Frontend polls workflow status.
- Do not add WebSockets for the first implementation.

### Research Sources

- Use the supplied company website URL as the primary source.
- Add lightweight HTTP fetching of the supplied website.
- Do not build broad web crawling in the first implementation.
- Put unsupported or missing information in `Unknowns`.

## Architecture

Recommended top-level architecture:

```text
frontend/  -> React application
backend/   -> FastAPI application, LangGraph workflow, persistence
docs/      -> assignment and project documentation
README.md  -> setup, testing, and demo instructions
```

Backend responsibilities:

- API routes for sessions, workflow execution/status, reports, chat, and health.
- Service layer for business logic.
- LangGraph workflow module for research orchestration.
- SQLAlchemy models and repository/database access.
- Configuration management.
- Logging and explicit error handling.

Frontend responsibilities:

- Session creation.
- Session history.
- Session detail page.
- Workflow progress UI.
- Intermediate output display.
- Structured report rendering.
- Follow-up chat.
- Loading, empty, and error states.
- Responsive layout.

LangGraph workflow shape:

1. `planner`
2. `source_collection`
3. `analysis`
4. `risk_unknowns`
5. `quality_check`
6. Conditional route for sufficient vs. insufficient research quality
7. `report_generation`
8. Failure handling path

The graph state should include session metadata, research objective, plan, source summaries, intermediate analysis, quality result, final report, errors, and warnings.

## Folder Conventions

Use this structure unless there is a clear reason to adjust within the locked stack:

```text
backend/
  app/
    api/
    core/
    db/
    models/
    schemas/
    services/
    workflow/
    main.py
  tests/
  requirements.txt

frontend/
  src/
    api/
    components/
    pages/
    styles/
    types/
    main.tsx
  package.json

docs/
  PROBLEM_STATEMENT.pdf
  architecture.md
  engineering-decisions.md
  product-improvements.md

README.md
AGENTS.md
```

Keep controllers/routes thin. Put business logic in services. Put LangGraph-specific orchestration in `backend/app/workflow/`.

## Required Product Features

Prioritize features evaluators will notice:

- Create a research session with company name, website, and research objective.
- Persist sessions.
- Execute a meaningful LangGraph workflow.
- Show workflow progress and intermediate outputs.
- Generate a structured report with:
  - Company Overview
  - Products & Services
  - Target Customers
  - Business Signals
  - Risks & Challenges
  - Suggested Discovery Questions
  - Suggested Outreach Strategy
  - Unknowns
  - Sources
- Allow follow-up chat grounded in the report/session context.
- Persist chat messages.
- Include clear loading and error states.
- Include required docs and demo instructions.

## API Conventions

Use `/api` routes. Suggested endpoints:

- `GET /api/health`
- `POST /api/sessions`
- `GET /api/sessions`
- `GET /api/sessions/{session_id}`
- `POST /api/sessions/{session_id}/run`
- `GET /api/sessions/{session_id}/workflow`
- `GET /api/sessions/{session_id}/report`
- `GET /api/sessions/{session_id}/chat`
- `POST /api/sessions/{session_id}/chat`

Validate inputs at API boundaries. Return explicit errors for missing sessions, invalid state transitions, missing reports, and missing AI configuration.

## Testing Commands

Inspect package/task files before assuming commands. Expected commands after implementation:

Backend:

```bash
cd backend
pytest
```

Frontend:

```bash
cd frontend
npm install
npm run build
```

If lint or additional test scripts are added to `package.json`, prefer the project scripts.

Minimum test coverage should include:

- Session creation/list/detail APIs.
- Missing session errors.
- Workflow state transitions.
- Required report shape.
- Insufficient source/failed fetch path.
- Chat endpoint validation and persistence.

## Risky Files And Areas

Treat these as high-risk and change carefully:

- `backend/app/workflow/`
  - LangGraph node definitions, shared state, conditional routing, and persistence behavior.
- `backend/app/models/`
  - Database schema and relationships.
- `backend/app/db/`
  - Session management, initialization, and persistence configuration.
- `backend/app/services/llm*`
  - Prompting, model configuration, structured output parsing, and secrets handling.
- `backend/app/api/`
  - Public API behavior and validation.
- `frontend/src/api/`
  - Client/server contract.
- Required docs:
  - `README.md`
  - `docs/architecture.md`
  - `docs/engineering-decisions.md`
  - `docs/product-improvements.md`

Do not make broad formatting-only changes in risky files while implementing behavior.

## What Not To Change

Do not change the locked stack unless explicitly asked.

Do not add:

- Authentication or user accounts.
- Team workspaces.
- Billing.
- CRM integrations.
- Email/calendar integrations.
- Vector database.
- Celery, Redis, or distributed workers.
- WebSockets.
- Broad web crawling.
- Search engine integration.
- Deployment automation.
- Admin dashboard.
- Complex design system.
- PDF export.
- Multi-provider model routing.

Do not hardcode secrets, credentials, tokens, API keys, private URLs, or local environment-specific values.

Do not silently invent unsupported company facts. Put uncertain or missing information in `Unknowns`.

## Documentation Requirements

Maintain these documents:

- `README.md`
  - Overview, setup, environment variables, backend/frontend run commands, test commands, demo flow, limitations.
- `docs/architecture.md`
  - System architecture, API responsibilities, LangGraph workflow, persistence model, failure/recovery approach.
- `docs/engineering-decisions.md`
  - 3 major engineering decisions, alternatives, tradeoffs, technical debt, biggest technical risk, what to improve with two more weeks.
- `docs/product-improvements.md`
  - Product weaknesses, top improvements, buyer/user/pay rationale, success metrics, AI roadmap, risks, feature to remove/add, 90-day roadmap.

## Final Response Format

Always include:

1. Summary of what changed
2. Files changed
3. Tests/checks run
4. Risks or assumptions
5. Manual verification steps

If tests cannot be run, explain the exact blocker and what should be run next.
