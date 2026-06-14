from unittest.mock import patch

import pytest

from app.core.url_validation import validate_external_url


def test_valid_public_url():
    with patch("socket.getaddrinfo") as mock_getaddrinfo:
        mock_getaddrinfo.return_value = [
            (2, 1, 6, "", ("93.184.216.34", 0))
        ]
        result = validate_external_url("https://example.com")
        assert result == "https://example.com"


def test_valid_public_ip_direct():
    result = validate_external_url("https://93.184.216.34")
    assert result == "https://93.184.216.34"


def test_localhost():
    with pytest.raises(ValueError, match="loopback"):
        validate_external_url("http://localhost")


def test_127_0_0_1():
    with pytest.raises(ValueError, match="loopback"):
        validate_external_url("http://127.0.0.1")


def test_127_0_0_2():
    with pytest.raises(ValueError, match="loopback"):
        validate_external_url("http://127.0.0.2")


def test_private_ipv4_10():
    with pytest.raises(ValueError, match="private"):
        validate_external_url("http://10.0.0.1")


def test_private_ipv4_192_168():
    with pytest.raises(ValueError, match="private"):
        validate_external_url("http://192.168.1.1")


def test_private_ipv4_172():
    with pytest.raises(ValueError, match="private"):
        validate_external_url("http://172.16.0.1")


def test_link_local():
    with pytest.raises(ValueError, match="link-local"):
        validate_external_url("http://169.254.169.254")


def test_ipv6_loopback():
    with pytest.raises(ValueError, match="loopback"):
        validate_external_url("http://[::1]")


def test_ipv6_unique_local():
    with pytest.raises(ValueError, match="private"):
        validate_external_url("http://[fd00::1]")


def test_invalid_scheme():
    with pytest.raises(ValueError, match="scheme"):
        validate_external_url("ftp://example.com")


def test_invalid_scheme_file():
    with pytest.raises(ValueError, match="scheme"):
        validate_external_url("file:///etc/passwd")


def test_no_hostname():
    with pytest.raises(ValueError, match="hostname"):
        validate_external_url("https://")


def test_unspecified():
    with pytest.raises(ValueError, match="unspecified"):
        validate_external_url("http://0.0.0.0")


def test_multicast():
    with pytest.raises(ValueError, match="multicast"):
        validate_external_url("http://224.0.0.1")


@pytest.mark.skip(reason="Depends on DNS resolution environment")
def test_hostname_resolving_to_private():
    with pytest.raises(ValueError, match="private|loopback"):
        validate_external_url("http://internal.company.local")


def test_create_session_rejects_localhost(client):
    resp = client.post("/api/sessions", json={
        "company_name": "Test",
        "website_url": "http://localhost:8080",
        "research_objective": "Test",
    })
    assert resp.status_code == 422
    body = resp.json()
    assert "loopback" in str(body).lower()


def test_create_session_rejects_127_0_0_1(client):
    resp = client.post("/api/sessions", json={
        "company_name": "Test",
        "website_url": "http://127.0.0.1",
        "research_objective": "Test",
    })
    assert resp.status_code == 422
    body = resp.json()
    assert "loopback" in str(body).lower()


def test_create_session_rejects_private_ip(client):
    resp = client.post("/api/sessions", json={
        "company_name": "Test",
        "website_url": "http://192.168.1.1",
        "research_objective": "Test",
    })
    assert resp.status_code == 422
    body = resp.json()
    assert "private" in str(body).lower()


def test_create_session_rejects_invalid_scheme(client):
    resp = client.post("/api/sessions", json={
        "company_name": "Test",
        "website_url": "ftp://example.com",
        "research_objective": "Test",
    })
    assert resp.status_code == 422
    body = resp.json()
    assert "scheme" in str(body).lower()


def _mock_http_response(status_code, text="", headers=None, url="https://93.184.216.34"):
    from unittest.mock import MagicMock
    mock = MagicMock()
    mock.status_code = status_code
    mock.headers = headers or {}
    mock.text = text
    mock.url = url
    mock.raise_for_status = MagicMock()
    if status_code >= 400:
        from httpx import HTTPStatusError
        mock.raise_for_status.side_effect = HTTPStatusError(
            f"HTTP {status_code}", request=MagicMock(), response=mock
        )
    return mock


def test_ssrf_redirect_to_localhost():
    """Public URL redirecting to localhost should be rejected."""
    from app.services.source_collection import SourceCollectionService
    from unittest.mock import patch

    with patch("app.services.source_collection.httpx.get") as mock_get:
        mock_get.return_value = _mock_http_response(
            302, headers={"Location": "http://127.0.0.1/admin"},
            url="https://93.184.216.34",
        )
        result = SourceCollectionService.fetch_and_extract(
            session_id="test-session",
            website_url="https://93.184.216.34",
        )
        assert result.source_text == ""
        assert "website_fetch_failed" in result.errors


def test_ssrf_redirect_to_metadata():
    """Public URL redirecting to 169.254.169.254 should be rejected."""
    from app.services.source_collection import SourceCollectionService
    from unittest.mock import patch

    with patch("app.services.source_collection.httpx.get") as mock_get:
        mock_get.return_value = _mock_http_response(
            302, headers={"Location": "http://169.254.169.254/latest/meta-data/"},
            url="https://93.184.216.34",
        )
        result = SourceCollectionService.fetch_and_extract(
            session_id="test-session",
            website_url="https://93.184.216.34",
        )
        assert result.source_text == ""
        assert "website_fetch_failed" in result.errors


def test_ssrf_redirect_to_private():
    """Public URL redirecting to RFC1918 private address should be rejected."""
    from app.services.source_collection import SourceCollectionService
    from unittest.mock import patch

    with patch("app.services.source_collection.httpx.get") as mock_get:
        mock_get.return_value = _mock_http_response(
            302, headers={"Location": "http://192.168.1.1/admin"},
            url="https://93.184.216.34",
        )
        result = SourceCollectionService.fetch_and_extract(
            session_id="test-session",
            website_url="https://93.184.216.34",
        )
        assert result.source_text == ""
        assert "website_fetch_failed" in result.errors


def test_ssrf_safe_redirect_chain(db_session):
    """Public URL redirecting to another public URL should succeed."""
    from app.services.source_collection import SourceCollectionService
    from unittest.mock import patch

    with patch("app.services.source_collection.httpx.get") as mock_get:
        mock_get.side_effect = [
            _mock_http_response(
                302, headers={"Location": "https://93.184.216.34/page"},
                url="https://93.184.216.34",
            ),
            _mock_http_response(
                200, text="<html><body>Safe content</body></html>",
                headers={},
                url="https://93.184.216.34/page",
            ),
        ]
        result = SourceCollectionService.fetch_and_extract(
            session_id="test-session",
            website_url="https://93.184.216.34",
        )
        assert result.source_text != ""
        assert "Safe content" in result.source_text
        assert result.errors == []
