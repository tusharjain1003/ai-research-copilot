from fastapi.testclient import TestClient

SESSION_DATA = {
    "company_name": "Acme Corp",
    "website_url": "https://93.184.216.34",
    "research_objective": "Understand their product strategy",
}


def test_create_session(client: TestClient):
    resp = client.post("/api/sessions", json=SESSION_DATA)
    assert resp.status_code == 201
    body = resp.json()
    assert body["company_name"] == "Acme Corp"
    assert body["website_url"] == "https://93.184.216.34"
    assert body["research_objective"] == "Understand their product strategy"
    assert body["status"] == "draft"
    assert "id" in body
    assert "created_at" in body


def test_list_sessions(client: TestClient):
    client.post("/api/sessions", json=SESSION_DATA)
    client.post("/api/sessions", json={
        "company_name": "Beta Inc",
        "website_url": "https://93.184.216.34",
        "research_objective": "Competitive analysis",
    })

    resp = client.get("/api/sessions")
    assert resp.status_code == 200
    body = resp.json()
    assert "sessions" in body
    assert len(body["sessions"]) >= 2
    newest = body["sessions"][0]
    assert newest["company_name"] == "Beta Inc"


def test_get_session(client: TestClient):
    create_resp = client.post("/api/sessions", json=SESSION_DATA)
    session_id = create_resp.json()["id"]

    resp = client.get(f"/api/sessions/{session_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == session_id
    assert body["company_name"] == "Acme Corp"
    assert body["website_url"] == "https://93.184.216.34"


def test_get_session_not_found(client: TestClient):
    resp = client.get("/api/sessions/nonexistent-id")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_create_session_validation(client: TestClient):
    resp = client.post("/api/sessions", json={})
    assert resp.status_code == 422

    resp = client.post("/api/sessions", json={
        "company_name": "",
        "website_url": "https://example.com",
        "research_objective": "Test",
    })
    assert resp.status_code == 422
