import pytest


@pytest.mark.asyncio
async def test_recruiter_can_create_list_delete_saved_search(client, recruiter_token):
    headers = {"Authorization": f"Bearer {recruiter_token}"}

    # Create
    create_resp = await client.post(
        "/recruiter/saved-searches",
        headers=headers,
        json={
            "name": "React devs in Pune",
            "skill": "React",
            "location": "Pune",
            "alert_enabled": True,
        },
    )
    assert create_resp.status_code == 201
    data = create_resp.json()
    search_id = data["id"]
    assert data["name"] == "React devs in Pune"
    assert data["filters"]["skill"] == "React"
    assert data["alert_enabled"] is True

    # List
    list_resp = await client.get("/recruiter/saved-searches", headers=headers)
    assert list_resp.status_code == 200
    assert any(s["id"] == search_id for s in list_resp.json())

    # Get by id
    get_resp = await client.get(f"/recruiter/saved-searches/{search_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == search_id

    # Delete
    del_resp = await client.delete(f"/recruiter/saved-searches/{search_id}", headers=headers)
    assert del_resp.status_code == 204

    # Confirm gone
    get2 = await client.get(f"/recruiter/saved-searches/{search_id}", headers=headers)
    assert get2.status_code == 404


@pytest.mark.asyncio
async def test_student_cannot_create_saved_search(client, student_token):
    resp = await client.post(
        "/recruiter/saved-searches",
        headers={"Authorization": f"Bearer {student_token}"},
        json={"name": "Blocked search"},
    )
    assert resp.status_code == 403
