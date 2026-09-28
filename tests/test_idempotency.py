"""
Idempotency middleware tests.

Verifies first-write-wins semantics:
- First request with a key is processed normally
- Second request with the same key returns the identical response
"""

import uuid
from fastapi.testclient import TestClient


def _make_idempotent_post(client, token, url, json_data, idempotency_key):
    """Helper: POST with idempotency header."""
    return client.post(
        url,
        json=json_data,
        headers={
            "Authorization": f"Bearer {token}",
            "X-Idempotency-Key": idempotency_key,
        },
    )


def test_first_request_processed_second_returns_same(client, student_token):
    """Two requests with the same idempotency key return the same response body."""
    key = str(uuid.uuid4())
    payload = {"code": "print('idempotent')", "language": "python", "stdin": ""}

    resp1 = _make_idempotent_post(client, student_token, "/sandbox/execute", payload, key)
    assert resp1.status_code == 200, resp1.text

    resp2 = _make_idempotent_post(client, student_token, "/sandbox/execute", payload, key)
    assert resp2.status_code == 200, resp2.text

    # Bodies must be identical
    assert resp1.json() == resp2.json(), (
        f"Idempotency broken: first={resp1.json()}, second={resp2.json()}"
    )


def test_different_keys_get_independent_responses(client, student_token):
    """Different idempotency keys are independent."""
    payload = {"code": "print('x')", "language": "python", "stdin": ""}

    resp1 = _make_idempotent_post(
        client, student_token, "/sandbox/execute", payload, str(uuid.uuid4())
    )
    resp2 = _make_idempotent_post(
        client, student_token, "/sandbox/execute", payload, str(uuid.uuid4())
    )

    assert resp1.status_code == 200
    assert resp2.status_code == 200
    # Both should succeed but are independent requests


def test_no_key_header_processes_normally(client, student_token):
    """Requests without X-Idempotency-Key are processed normally."""
    resp1 = client.post(
        "/sandbox/execute",
        json={"code": "print('no-key')", "language": "python"},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    resp2 = client.post(
        "/sandbox/execute",
        json={"code": "print('no-key')", "language": "python"},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert resp1.status_code == 200
    assert resp2.status_code == 200
