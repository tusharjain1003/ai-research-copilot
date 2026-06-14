# Engineering Decisions

## 1. SQLite over PostgreSQL

**Decision**: Use SQLite as the database backend instead of PostgreSQL.

**Alternatives considered**: PostgreSQL, DuckDB

**Rationale**: The project scope is a single-user development/research tool. SQLite requires zero configuration — no daemon process, no connection pool tuning, no schema migrations. The entire database is a single file that can be inspected with any SQLite tool. PostgreSQL would add operational overhead (install, configure, run) with no benefit at the expected scale (one user, one session at a time).

**Tradeoffs**: SQLite does not support concurrent writes. If two background workflows tried to write simultaneously, one would get a `database is locked` error. For a single-user app where workflows run sequentially, this is acceptable. SQLite also lacks row-level locking, CHECK constraints, and advanced data types — none of which this project needs.

**Technical debt**: The codebase uses SQLAlchemy, so switching to PostgreSQL requires only changing the connection string and potentially removing SQLite-specific workarounds (e.g., JSON column handling).

**Biggest technical risk**: Thread safety with SQLite. The background daemon thread creates its own SQLAlchemy session, so concurrent access is possible. Mitigated by using `check_same_thread=False` in the connection string and ensuring each thread uses its own session.

## 2. Polling over WebSockets

**Decision**: Frontend polls `GET /api/sessions/{id}/workflow` every 2 seconds to track progress instead of using WebSockets.

**Alternatives considered**: WebSockets (via `websockets` or FastAPI's built-in WebSocket support), Server-Sent Events

**Rationale**: The workflow runs in seconds to tens of seconds. A 2-second polling interval provides adequate UX granularity without significant overhead. WebSockets add complexity: persistent connection management, reconnection logic, connection lifecycle tied to background task lifetimes, and potential resource leaks if connections are orphaned. Polling is stateless, trivially cacheable, and requires no special infrastructure.

**Tradeoffs**: Each poll triggers a database query. At 2-second intervals during a 10-second workflow, that's ~5 extra queries per session — negligible. The polling interval cannot give sub-second updates, but LangGraph node execution times make sub-second granularity irrelevant. Polling generates more total network requests than push-based approaches.

**Technical debt**: If the app grows to dozens of concurrent sessions with longer workflows, polling should be replaced. The frontend polling logic is isolated in the `WorkflowProgress` component, making it straightforward to swap to WebSockets by subscribing to a channel and removing the `setInterval` loop.

**Biggest technical risk**: Polling creates tight coupling between the frontend polling interval and backend response times. If a node hangs, the frontend continues polling until timeout. Mitigated by the backend's 120-second default HTTP timeout in `httpx` on the fetch side, though LangGraph itself has no timeout.

## 3. Manual LangGraph Persistence over Built-in Checkpointer

**Decision**: Persist workflow state manually by writing each node's input/output to `WorkflowStep` records, rather than using LangGraph's built-in checkpointer.

**Alternatives considered**: `langgraph-checkpoint` library, full state snapshotting

**Rationale**: LangGraph's built-in persistence requires a checkpointer implementation (e.g., `SqliteSaver` from `langgraph-checkpoint`) and stores serialized graph state in opaque blobs. Manual persistence gives full control over what gets stored: each `WorkflowStep` has typed `input_data` and `output_data` JSON columns, making the workflow history queryable in standard SQL without deserializing graph internals. This also avoids adding a dependency on `langgraph-checkpoint`.

**Tradeoffs**: No automatic state restoration on crash. If the daemon thread dies mid-workflow, the session stays `in_progress` permanently (no timeout mechanism to reset it). The manual persistence code in `_run_node` (`nodes.py`) adds ~10 lines of scaffolding per node that a checkpointer would handle automatically. State cannot be resumed from a checkpoint — on failure, the workflow must be retried from scratch.

**Technical debt**: After every LangGraph upgrade, the manual persistence layer needs verification that the state interface hasn't changed. The `GraphState` keys must stay synchronized with the persistence code.

**Biggest technical risk**: If a node writes output but the subsequent node crashes before persisting its step, the DB contains an orphaned `WorkflowStep` for the crashed node (created before the work function) with status `running`. No cleanup mechanism exists for orphaned running steps.
