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



