import time
from unittest.mock import patch

from fastapi.testclient import TestClient
from app.models.report import ResearchReport

SESSION_DATA = {
    "company_name": "Workflow Corp",
    "website_url": "https://93.184.216.34",
    "research_objective": "Test workflow execution",
}


def _create_session(client: TestClient) -> str:
    resp = client.post("/api/sessions", json=SESSION_DATA)
    return resp.json()["id"]


def test_start_workflow(client: TestClient):
    session_id = _create_session(client)

    with patch("app.services.workflow._execute_workflow") as mock_exec:
        resp = client.post(f"/api/sessions/{session_id}/run")
        assert resp.status_code == 201
        body = resp.json()
        assert body["session_id"] == session_id
        assert body["status"] == "pending"
        assert "run_id" in body
        time.sleep(0.05)
        mock_exec.assert_called_once_with(session_id)


def test_start_workflow_session_not_found(client: TestClient):
    resp = client.post("/api/sessions/nonexistent/run")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_workflow_status_no_run(client: TestClient):
    session_id = _create_session(client)

    resp = client.get(f"/api/sessions/{session_id}/workflow")
    assert resp.status_code == 200
    body = resp.json()
    assert body["run"] is None
    assert body["steps"] == []


def test_workflow_status_after_start(client: TestClient):
    session_id = _create_session(client)

    with patch("app.services.workflow._execute_workflow"):
        client.post(f"/api/sessions/{session_id}/run")

    resp = client.get(f"/api/sessions/{session_id}/workflow")
    assert resp.status_code == 200
    body = resp.json()
    assert body["run"] is not None
    assert body["run"]["session_id"] == session_id
    assert body["run"]["status"] in ("pending", "running", "completed", "failed")


def test_workflow_status_session_not_found(client: TestClient):
    resp = client.get("/api/sessions/nonexistent/workflow")
    assert resp.status_code == 404


def test_report_not_found(client: TestClient):
    session_id = _create_session(client)
    resp = client.get(f"/api/sessions/{session_id}/report")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_report_session_not_found(client: TestClient):
    resp = client.get("/api/sessions/nonexistent/report")
    assert resp.status_code == 404


def test_report_shape(client: TestClient, db_session):
    session_id = _create_session(client)

    r = ResearchReport(
        session_id=session_id,
        company_overview="Overview text",
        products_services="Products text",
        target_customers="Customers text",
        business_signals="Signals text",
        risks_challenges="Risks text",
        discovery_questions="Questions text",
        outreach_strategy="Strategy text",
        unknowns="Unknowns text",
        sources="Sources text",
    )
    db_session.add(r)
    db_session.commit()

    resp = client.get(f"/api/sessions/{session_id}/report")
    assert resp.status_code == 200
    body = resp.json()
    assert body["company_overview"] == "Overview text"
    assert body["products_services"] == "Products text"
    assert body["target_customers"] == "Customers text"
    assert body["business_signals"] == "Signals text"
    assert body["risks_challenges"] == "Risks text"
    assert body["discovery_questions"] == "Questions text"
    assert body["outreach_strategy"] == "Strategy text"
    assert body["unknowns"] == "Unknowns text"
    assert body["sources"] == "Sources text"


def test_report_shape_all_fields_present(client: TestClient, db_session):
    session_id = _create_session(client)

    r = ResearchReport(session_id=session_id)
    db_session.add(r)
    db_session.commit()

    resp = client.get(f"/api/sessions/{session_id}/report")
    assert resp.status_code == 200
    body = resp.json()
    expected_keys = [
        "company_overview",
        "products_services",
        "target_customers",
        "business_signals",
        "risks_challenges",
        "discovery_questions",
        "outreach_strategy",
        "unknowns",
        "sources",
    ]
    for key in expected_keys:
        assert key in body, f"Missing report field: {key}"


def test_workflow_conflict(client: TestClient):
    session_id = _create_session(client)

    with patch("app.services.workflow._execute_workflow"):
        resp1 = client.post(f"/api/sessions/{session_id}/run")
        assert resp1.status_code == 201

        resp2 = client.post(f"/api/sessions/{session_id}/run")
        assert resp2.status_code == 409
        assert "active" in resp2.json()["detail"].lower()


def _seed_run(db_session, session_id: str) -> str:
    """Create a pending WorkflowRun and return its id."""
    from app.models.workflow import WorkflowRun
    from app.models.enums import WorkflowRunStatus
    run = WorkflowRun(
        session_id=session_id,
        status=WorkflowRunStatus.pending,
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)
    return run.id


def test_report_rejects_during_active_run(client: TestClient, db_session):
    session_id = _create_session(client)

    from app.models.report import ResearchReport
    r = ResearchReport(session_id=session_id, company_overview="Overview")
    db_session.add(r)

    from app.models.workflow import WorkflowRun
    from app.models.enums import WorkflowRunStatus
    run = WorkflowRun(session_id=session_id, status=WorkflowRunStatus.running)
    db_session.add(run)
    db_session.commit()

    resp = client.get(f"/api/sessions/{session_id}/report")
    assert resp.status_code == 409
    assert "currently running" in resp.json()["detail"].lower()


def test_quality_check_scoring(db_session, client):
    from app.workflow.nodes import quality_check
    from app.models.session import ResearchSession
    from app.models.enums import SessionStatus
    import uuid

    session = ResearchSession(
        id=str(uuid.uuid4()),
        company_name="Score Test",
        website="https://example.com",
        research_objective="Test scoring",
        status=SessionStatus.draft,
    )
    db_session.add(session)
    db_session.commit()
    _seed_run(db_session, session.id)

    state = {
        "session_id": session.id,
        "company_name": "Score Test",
        "website_url": "https://example.com",
        "research_objective": "Test scoring",
        "plan": {},
        "source_text": "x" * 2000,
        "source_metadata": [],
        "analysis_output": {
            "company_overview": "Overview",
            "products_and_services": "Products",
            "target_customers": "Customers",
            "business_signals": "Signals",
        },
        "risks_and_unknowns": {"unknowns": ["gap1", "gap2", "gap3"]},
        "quality_result": {},
        "final_report": {},
        "warnings": [],
        "errors": [],
        "workflow_status": "running",
    }

    result = quality_check(state)
    qr = result.get("quality_result", {})

    assert "research_quality_score" in qr, "Missing research_quality_score"
    assert "confidence" in qr, "Missing confidence"
    assert qr["passed"] is True
    assert qr["missing_sections"] == []
    # source_coverage: 2000/2000*40=40, completeness: (1-0/5)*40=40, unknowns: 3/5*20=12 → total 92
    assert qr["research_quality_score"] == 92, f"Expected 92, got {qr['research_quality_score']}"
    assert qr["confidence"] == "high"


def test_quality_check_scoring_low_quality(db_session, client):
    from app.workflow.nodes import quality_check
    from app.models.session import ResearchSession
    from app.models.enums import SessionStatus
    import uuid

    session = ResearchSession(
        id=str(uuid.uuid4()),
        company_name="Low Quality",
        website="https://example.com",
        research_objective="Test low quality",
        status=SessionStatus.draft,
    )
    db_session.add(session)
    db_session.commit()
    _seed_run(db_session, session.id)

    state = {
        "session_id": session.id,
        "company_name": "Low Quality",
        "website_url": "https://example.com",
        "research_objective": "Test low quality",
        "plan": {},
        "source_text": "short",
        "source_metadata": [],
        "analysis_output": {},
        "risks_and_unknowns": {"unknowns": []},
        "quality_result": {},
        "final_report": {},
        "warnings": [],
        "errors": [],
        "workflow_status": "running",
    }

    result = quality_check(state)
    qr = result.get("quality_result", {})

    assert qr["passed"] is False
    assert len(qr["missing_sections"]) == 5
    assert qr["confidence"] == "low"
    # source_coverage: 5/2000*40=0.1, completeness: (1-5/5)*40=0, unknowns: 0/5*20=0 → total ~0
    assert qr["research_quality_score"] == 0


def test_enrich_unknowns_generates_gaps(db_session, client):
    from app.workflow.nodes import enrich_unknowns
    from app.models.session import ResearchSession
    from app.models.enums import SessionStatus
    import uuid

    session = ResearchSession(
        id=str(uuid.uuid4()),
        company_name="Gap Test",
        website="https://example.com",
        research_objective="Test gaps",
        status=SessionStatus.draft,
    )
    db_session.add(session)
    db_session.commit()
    _seed_run(db_session, session.id)

    state = {
        "session_id": session.id,
        "company_name": "Gap Test",
        "website_url": "https://example.com",
        "research_objective": "Test gaps",
        "plan": {},
        "source_text": "",
        "source_metadata": [],
        "analysis_output": {},
        "risks_and_unknowns": {"unknowns": []},
        "quality_result": {
            "passed": False,
            "missing_sections": ["company_overview", "products_and_services"],
            "enrich_retries": 0,
        },
        "final_report": {},
        "warnings": [],
        "errors": [],
        "workflow_status": "running",
    }

    result = enrich_unknowns(state)
    ru = result.get("risks_and_unknowns", {})
    enriched_items = ru.get("enriched_items", [])

    assert len(enriched_items) == 2, f"Expected 2 enriched items, got {len(enriched_items)}"

    sections_found = {item["section"] for item in enriched_items}
    assert "company_overview" in sections_found
    assert "products_and_services" in sections_found

    for item in enriched_items:
        assert "research_gap" in item
        assert "why_missing" in item
        assert "recommended_source" in item
        assert item["confidence"] == "low"

    assert result["quality_result"]["enrich_retries"] == 1
    assert len(result["warnings"]) == 1


def test_enrich_loop_routes_to_quality_check():
    from app.workflow.graph import build_research_graph

    g = build_research_graph()
    enrich_edges = [(s, e) for s, e in g.edges if s == "enrich_unknowns"]
    assert len(enrich_edges) == 1, f"Expected 1 edge from enrich_unknowns, got {len(enrich_edges)}"
    assert enrich_edges[0] == ("enrich_unknowns", "quality_check"), (
        f"enrich_unknowns should route to quality_check, got {enrich_edges[0]}"
    )

    # Verify quality_check has conditional edges to enrich_unknowns
    assert "quality_check" in g.branches, "quality_check should have conditional branches"
    branch = g.branches["quality_check"]["route_after_quality"]
    assert branch.ends.get("enrich") == "enrich_unknowns", (
        "quality_check 'enrich' path should go to enrich_unknowns"
    )
    assert branch.ends.get("sufficient") == "report_generation"
    assert branch.ends.get("errors") == "failure_handler"



