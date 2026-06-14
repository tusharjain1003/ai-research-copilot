from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session as DBSession

from app.models.report import ResearchReport

SESSION_DATA = {
    "company_name": "Chat Corp",
    "website_url": "https://chat.example.com",
    "research_objective": "Test chat",
}

REPORT = {
    "company_overview": "Overview",
    "products_services": "Products",
    "target_customers": "Customers",
    "business_signals": "Signals",
    "risks_challenges": "Risks",
    "discovery_questions": "Questions",
    "outreach_strategy": "Strategy",
    "unknowns": "Unknowns",
    "sources": "Sources",
}


def _create_session(client: TestClient) -> str:
    resp = client.post("/api/sessions", json=SESSION_DATA)
    return resp.json()["id"]


def _create_report(db_session: DBSession, session_id: str) -> None:
    r = ResearchReport(session_id=session_id, **REPORT)
    db_session.add(r)
    db_session.commit()


def test_chat_get_messages_empty(client: TestClient):
    session_id = _create_session(client)
    resp = client.get(f"/api/sessions/{session_id}/chat")
    assert resp.status_code == 200
    body = resp.json()
    assert body["messages"] == []


def test_chat_get_messages_session_not_found(client: TestClient):
    resp = client.get("/api/sessions/nonexistent/chat")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_chat_send_message(client: TestClient, db_session):
    session_id = _create_session(client)
    _create_report(db_session, session_id)

    with patch("app.services.chat.LLMService") as mock_llm_cls:
        mock_llm = mock_llm_cls.return_value
        mock_llm.chat_messages.return_value = "They offer AI-powered analytics."
        resp = client.post(
            f"/api/sessions/{session_id}/chat",
            json={"message": "What products do they offer?"},
        )
    assert resp.status_code == 201
    body = resp.json()
    assert body["role"] == "assistant"
    assert body["content"] == "They offer AI-powered analytics."
    assert "id" in body
    assert "created_at" in body


def test_chat_send_message_persists(client: TestClient, db_session):
    session_id = _create_session(client)
    _create_report(db_session, session_id)

    with patch("app.services.chat.LLMService") as mock_llm_cls:
        mock_llm = mock_llm_cls.return_value
        mock_llm.chat_messages.return_value = "They serve enterprise clients."
        client.post(
            f"/api/sessions/{session_id}/chat",
            json={"message": "Tell me about their customers"},
        )

    resp = client.get(f"/api/sessions/{session_id}/chat")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["messages"]) == 2
    assert body["messages"][0]["role"] == "user"
    assert body["messages"][0]["content"] == "Tell me about their customers"
    assert body["messages"][1]["role"] == "assistant"
    assert body["messages"][1]["content"] == "They serve enterprise clients."


def test_chat_send_message_session_not_found(client: TestClient):
    resp = client.post(
        "/api/sessions/nonexistent/chat",
        json={"message": "Hello"},
    )
    assert resp.status_code == 404


def test_chat_send_message_validation(client: TestClient):
    session_id = _create_session(client)

    resp = client.post(
        f"/api/sessions/{session_id}/chat",
        json={"message": ""},
    )
    assert resp.status_code == 422

    resp = client.post(
        f"/api/sessions/{session_id}/chat",
        json={},
    )
    assert resp.status_code == 422


def test_chat_multiple_messages(client: TestClient, db_session):
    session_id = _create_session(client)
    _create_report(db_session, session_id)

    with patch("app.services.chat.LLMService") as mock_llm_cls:
        mock_llm = mock_llm_cls.return_value
        mock_llm.chat_messages.return_value = "Mock response"
        for msg in ["First question", "Second question", "Third question"]:
            resp = client.post(
                f"/api/sessions/{session_id}/chat",
                json={"message": msg},
            )
            assert resp.status_code == 201

    resp = client.get(f"/api/sessions/{session_id}/chat")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["messages"]) == 6

    for i, msg in enumerate(["First question", "Second question", "Third question"]):
        assert body["messages"][i * 2]["role"] == "user"
        assert body["messages"][i * 2]["content"] == msg


def test_chat_no_report_returns_409(client: TestClient, db_session):
    """Chat should reject messages when no report exists."""
    session_id = _create_session(client)

    resp = client.post(
        f"/api/sessions/{session_id}/chat",
        json={"message": "Any question"},
    )
    assert resp.status_code == 409
    assert "not yet available" in resp.json()["detail"].lower()


def test_chat_llm_not_configured_returns_503(client: TestClient, db_session):
    """When no LLM API key is configured, chat should return 503."""
    session_id = _create_session(client)
    _create_report(db_session, session_id)

    resp = client.post(
        f"/api/sessions/{session_id}/chat",
        json={"message": "Any question"},
    )
    assert resp.status_code == 503
    assert "not configured" in resp.json()["detail"].lower()
