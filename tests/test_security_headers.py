"""
Security header tests.

Verifies every response carries the expected hardening headers.
"""


def test_security_headers_present(client):
    """Health/any endpoint must include all security headers."""
    resp = client.get("/health")
    assert resp.status_code == 200, resp.text

    headers = resp.headers
    assert headers.get("x-frame-options") == "DENY"
    assert headers.get("x-content-type-options") == "nosniff"
    assert headers.get("referrer-policy") == "strict-origin-when-cross-origin"
    assert headers.get("permissions-policy") is not None
    assert headers.get("content-security-policy") is not None
    assert "frame-ancestors 'none'" in headers.get("content-security-policy", "")
    assert "default-src 'self'" in headers.get("content-security-policy", "")


def test_security_headers_on_api_response(client, student_token):
    """Authenticated API responses also carry security headers."""
    resp = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers.get("x-frame-options") == "DENY"
    assert resp.headers.get("x-content-type-options") == "nosniff"
