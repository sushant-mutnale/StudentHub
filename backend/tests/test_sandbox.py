import pytest
from .conftest import auth_headers


@pytest.mark.asyncio
async def test_sandbox_execute_success(client, student_token):
    resp = await client.post(
        "/sandbox/execute",
        json={
            "code": "print('Hello, Sandbox!')",
            "language": "python",
            "stdin": "",
            "timeout_ms": 3000
        },
        headers=auth_headers(student_token)
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "success"
    assert "Hello, Sandbox!" in data["output"]
    assert data["exit_code"] == 0
    assert data["timeout"] is False
    assert data["oom_killed"] is False


@pytest.mark.asyncio
async def test_sandbox_execute_syntax_error(client, student_token):
    resp = await client.post(
        "/sandbox/execute",
        json={
            "code": "print('Hello' + 123", # SyntaxError
            "language": "python"
        },
        headers=auth_headers(student_token)
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "error"
    assert data["exit_code"] != 0


@pytest.mark.asyncio
async def test_sandbox_execute_timeout(client, student_token):
    resp = await client.post(
        "/sandbox/execute",
        json={
            "code": "import time\ntime.sleep(6)", # Exceeds default limit
            "language": "python",
            "timeout_ms": 2000
        },
        headers=auth_headers(student_token)
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["timeout"] is True
    assert "timed out" in data["error"].lower()


@pytest.mark.asyncio
async def test_sandbox_validate_problem(client, student_token):
    # Valid solution for two_sum problem
    code = """
import sys
import json

def main():
    lines = sys.stdin.read().splitlines()
    if len(lines) < 2:
        return
    nums = json.loads(lines[0])
    target = int(lines[1])
    
    # Simple two sum logic
    d = {}
    for i, num in enumerate(nums):
        diff = target - num
        if diff in d:
            print(json.dumps([d[diff], i]))
            return
        d[num] = i
    print("[]")

if __name__ == "__main__":
    main()
"""
    resp = await client.post(
        "/sandbox/validate",
        json={
            "code": code,
            "problem_id": "two_sum",
            "language": "python"
        },
        headers=auth_headers(student_token)
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["success"] is True
    assert data["all_passed"] is True
    assert data["passed"] == data["total"]
    
    # Verify hidden cases are masked
    results = data["results"]
    hidden_found = False
    for r in results:
        if r["hidden"]:
            hidden_found = True
            assert "masked" in r["input"].lower()
            assert "masked" in r["expected"].lower()
            assert "masked" in r["actual"].lower()
            assert r["error"] is None or "masked" in r["error"].lower()
    assert hidden_found is True
