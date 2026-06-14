from unittest.mock import patch

from fastapi.testclient import TestClient

SESSION_DATA = {
    "company_name": "Chat Corp",
    "website_url": "https://chat.example.com",
    "research_objective": "Test chat",
}


def _create_session(client: TestClient) -> str:
    resp = client.post("/api/sessions", json=SESSION_DATA)
    return resp.json()["id"]


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


def test_chat_send_message(client: TestClient):
    session_id = _create_session(client)

    resp = client.post(
        f"/api/sessions/{session_id}/chat",
        json={"message": "What products do they offer?"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["role"] == "assistant"
    assert body["content"] != ""
    assert "id" in body
    assert "created_at" in body


def test_chat_send_message_persists(client: TestClient):
    session_id = _create_session(client)

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


def test_chat_multiple_messages(client: TestClient):
    session_id = _create_session(client)

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


def test_chat_llm_not_configured_returns_unsupported(client: TestClient):
    """When no LLM API key is configured, the chat should return the unsupported response."""
    session_id = _create_session(client)

    resp = client.post(
        f"/api/sessions/{session_id}/chat",
        json={"message": "Any question"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert "don't have enough information" in body["content"].lower()
