import pytest


@pytest.mark.asyncio
async def test_next_best_action_suggests_onboarding(client, student_token):
    resp = await client.get(
        "/next-action",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["student_id"]
    assert body["action"]
    assert body["action"]["id"]
    assert body["action"]["cta"]
    assert body["action"]["target"] is not None


@pytest.mark.asyncio
async def test_next_best_action_recruiter_default(client, recruiter_token):
    resp = await client.get(
        "/next-action",
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["action"]["type"] == "none"
