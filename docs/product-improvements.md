# Product Improvements

## 1. If you could redesign this system from scratch, what would you do differently?

**LangGraph checkpointer from day one.** The manual persistence layer in `_run_node` works but duplicates what `langgraph-checkpoint` provides: automatic state snapshots, crash recovery, and resumable workflows. Starting with the checkpointer would save ~15 lines of scaffolding per node and enable automatic state restoration.

**Celery or Redis Queue instead of daemon threads.** The current `threading.Thread` background execution in `WorkflowService._execute_workflow()` works for development but has no monitoring, no retry, no timeout enforcement, and no visibility into hung tasks. A proper task queue would provide heartbeat monitoring, dead letter queues, task retries with backoff, and worker process isolation.

**PostgreSQL from the start.** SQLite was the right call for the assignment scope, but redesigning from scratch for production would mean PostgreSQL — concurrent write support, connection pooling, and no `database is locked` errors.

**WebSocket push instead of polling.** Polling works at this scale, but a push-based approach would eliminate the 2-second latency, reduce total requests, and provide instant UI updates when nodes complete.

**Headless browser scraping.** The current `httpx`-based HTML text extraction fails on JavaScript-rendered SPAs. A headless browser (Playwright) would extract meaningful content from modern websites. It's heavy but necessary for reliable research.

## 2. Given more time, what improvements would you make to the system's architecture?

**Dedicated crawler service.** Extract website fetching into an independent microservice (or at least a standalone class) with rate limiting, polite crawling delays, robots.txt compliance, caching, and JS rendering. The current `SourceCollectionService` does one synchronous fetch — acceptable for demo, not for production.

**Multi-source research.** The architecture currently ingests exactly one URL. Adding sources like Crunchbase (company funding/leadership), LinkedIn (employee count, recent hires), news RSS (recent press coverage), and SEC filings (public companies) would dramatically improve report quality. Each source would be a pluggable collector implementing a common interface (`BaseSourceCollector`).

**Caching layer.** Repeated fetches of the same website URL in different sessions should hit a cache. An `functools.lru_cache`-like in-memory cache with TTL would reduce latency and avoid hammering target servers.

**Pluggable LLM provider interface.** The `LLMService` assumes an OpenAI-compatible API. A provider abstraction (similar to LangChain's `BaseChatModel`) would allow swapping between OpenAI, Anthropic, local Ollama, or AWS Bedrock without touching consumer code.

## 3. What trade-offs did you make—and why?

| Trade-off | Chosen approach | Why |
|---|---|---|
| Task execution | Daemon thread over Celery/Redis | Zero infrastructure, no Redis dependency, adequate for single-user demo |
| Database | SQLite over PostgreSQL | Zero-config, file-based, assignment-appropriate |
| Real-time updates | Polling over WebSockets | Faster to implement, adequate for 2s node execution intervals |
| State persistence | Manual step recording over LangGraph checkpointer | Full control over stored data, queryable via SQL, no extra dependency |
| Website scraping | Basic HTML stripping over Playwright | No heavy browser dependency, works for 80% of sites |
| Report building | Deterministic over LLM-generated | Reliable, testable, no hallucination risk in the final output |
| Anti-hallucination | Skip LLM on empty source over fallback prompts | Prevents confident-but-wrong analysis on no data |

## 4. What's the most impactful improvement you would prioritise?

**Multi-source research.** A single website URL is often insufficient for a quality report. Adding even one additional source — such as a news search or Crunchbase lookup — would double the useful information in the report. The architecture already supports this at the state level: `source_text` could become `sources: dict[str, str]`, with each collector populating its key. The quality check would evaluate collectively rather than on a single source. This improvement directly addresses the most common failure mode: "not enough information to research."

## 5. Are there any significant security considerations in this system?

**No authentication.** All endpoints are unauthenticated. Anyone who can reach the server can create sessions, run workflows, and read reports. This is acceptable for the current scope (development/demo) but must be addressed before any production deployment.

**SSRF via website URL.** The `SourceCollectionService.fetch_website()` makes HTTP requests to user-supplied URLs. A malicious user could supply `http://localhost:8000/admin` or `http://169.254.169.254/latest/meta-data/` (AWS metadata endpoint). Mitigation options: URL validation against an allowlist, blocking private IP ranges, adding a request timeout (currently 10s in `httpx`).

**LLM API key exposure.** The API key is read from environment variables (good practice) but exists in process memory for the lifetime of the server. A process dump or `/proc` access could leak it. Minimal risk for a development tool.

**Input length attacks.** API fields (`research_objective`, chat messages) could accept arbitrarily long strings, potentially causing LLM token overflow or storage bloat. Pydantic validation with `max_length` on all string fields is the mitigation.

**LLM output safety.** The system does not validate or sanitize LLM output before displaying it to users. An LLM prompted with malicious context could theoretically produce harmful content. For a business research tool, the risk is low but worth noting.

## 6. What monitoring/observability would you add in production?

**Structured JSON logging.** Every API request should emit a log line with `timestamp`, `method`, `path`, `status_code`, `duration_ms`, and `session_id`. Python's `structlog` or `python-json-logger` would replace the current basic `logging` setup.

**Workflow node timing.** Each `WorkflowStep` should record `started_at` and `completed_at` (already partially done via `created_at` and `updated_at`). A dashboard would show p50/p95/p99 node execution times, helping identify slow LLM calls.

**LLM call telemetry.** Track per-call: model, prompt token count, completion token count, latency, and error rate. This is critical for cost management and detecting model degradation.

**Error rate alerting.** Spike in 5xx responses, LLM API failures, or workflow failures should trigger alerts. For a single-user tool, even a simple health-check endpoint with step failure counters would help.

**Background worker heartbeat.** The daemon thread should periodically update a heartbeat timestamp on the `WorkflowRun` record. A separate monitor process (or a health-check endpoint) would detect stale runs (running for > 5 minutes without heartbeat) and mark them as failed.

## 7. What testing improvements would you make?

**End-to-end workflow test with real LLM.** Current tests mock all LLM calls. An integration test that exercises the full graph with a cheap, fast model (`gpt-4o-mini` or a local Ollama instance) would catch regressions in prompt formatting, structured output parsing, and state passing. This test would be tagged `slow` and excluded from CI pre-merge but run nightly.

**Property-based tests for report generation.** The `ReportGenerationService` has deterministic logic (building discovery questions from unknowns, outreach strategy from company name + products, etc.). Property-based tests with `hypothesis` would verify invariants: "every section is a string", "discovery questions always reference at least one unknown", "outreach strategy always mentions the company name".

**Frontend snapshot tests.** Components like `ReportView`, `WorkflowProgress`, and `ChatPanel` would benefit from Vitest snapshot tests to detect accidental UI changes.

**Load test for polling.** A test that creates N sessions (N=10, N=50) and simulates frontend polling behavior to verify the backend can handle concurrent status requests without connection pool exhaustion.

## 8. How would the system handle a company website that is a single-page app requiring JavaScript?

**Current behavior:** The `SourceCollectionService.fetch_website()` fetches the raw HTML with `httpx`. For a JS-rendered SPA, the initial HTML contains minimal content (often just `<div id="root"></div>` plus script tags). The HTML text extraction returns near-empty `source_text`. Downstream nodes handle this gracefully:

1. `source_collection` returns `source_text=""` with a warning about minimal content
2. `analysis` detects empty `source_text` and returns default "Information not available" values with no LLM call
3. `quality_check` fails — source length < 500, all analysis sections missing
4. `enrich_unknowns` runs an LLM call but has no source text to work with, so produces minimal enrichment
5. After `MAX_ENRICH_RETRIES=1`, the workflow proceeds to `report_generation`
6. The report contains mostly "Information not available." for data-driven sections. The `Unknowns` section lists the missing information. `Sources` documents the attempted URL.

**Improvement:** A headless browser (Playwright) would evaluate JavaScript, wait for render completion, and extract the post-render DOM text. This would be activated only when the initial HTTP fetch returns fewer than 500 characters of text — keeping the fast path for traditional websites.

## 9. How would the system handle a drastically incomplete research output?

The system handles incompleteness through its quality-check loop and graceful degradation:

1. **Quality gate**: The `quality_check` node evaluates source length (≥500 chars), analysis section completeness (all 4 sections non-empty), and unknowns presence. If any check fails, it triggers the enrichment loop.

2. **Enrichment loop (up to 1 retry)**: `enrich_unknowns` re-prompts the LLM specifically about missing sections. If the underlying website truly has no content, enrichment adds nothing new.

3. **Warnings accumulation**: Throughout the workflow, warnings about missing data are collected: `state["warnings"]` may contain `["Source text is empty or minimal", "Could not extract products and services from the available content"]`.

4. **Graceful report generation**: `ReportGenerationService` never crashes on missing data. It uses Python dict `.get()` with fallback defaults. Report sections default to `"Information not available."` or `"N/A"`. Discovery questions are derived from whatever unknowns exist. Outreach strategy is derived from whatever overview exists.

5. **Failure handler safety net**: If any node throws an unhandled exception, `_run_node` catches it, persists the error, appends to `state["errors"]`, and routes to `failure_handler`. The workflow always reaches END — either through `report_generation` or `failure_handler`.

**Result**: The user always gets a rendered report. Its quality directly reflects the available source data, with clear labeling of what is missing and why.

## 10. What would be required to make this multi-tenant with user authentication?

**Database changes:**
- Add `User` and `Organization` models (id, name, email, password_hash, org_id)
- Add `user_id` foreign key to `ResearchSession`
- Create an `organization_members` association table for org-user membership

**Backend changes:**
- JWT-based auth: login endpoint returns access + refresh tokens
- FastAPI dependency (`get_current_user`) that decodes the JWT and attaches the user to the request
- Row-level security: every session/chat/workflow query filters by `user_id`
- Password hashing via `bcrypt` or `argon2`
- Rate limiting on login endpoint
- Session middleware for token refresh

**Frontend changes:**
- Login/register pages
- Auth context storing JWT in memory/localStorage
- Protected route wrapper that redirects to login
- Axios/Fetch interceptor attaching `Authorization: Bearer <token>` header
- Token refresh logic in the interceptor

**Infrastructure changes:**
- PostgreSQL (SQLite does not support concurrent writes from multiple users)
- Connection pooling (e.g., PgBouncer) for multiple simultaneous users
- HTTPS in production (required for cookie-based auth if used instead of JWT)
- CORS configuration scoped to the frontend origin

**Not required for MVP:**
- Role-based access control (admin vs. user)
- Team workspaces or shared sessions
- Audit logging
- OAuth/SSO

The current service layer already isolates data by `session_id`, so the main change is adding the `user_id` filter to every query in `SessionService`, `ChatService`, and `WorkflowService`.
