import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from bson import ObjectId


@pytest.mark.asyncio
async def test_calendar_deadlines_returns_events(client, student_token):
    resp = await client.get(
        "/calendar/deadlines",
        headers={"Authorization": f"Bearer {student_token}"},
        params={"limit": 50},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "events" in body
    assert "total" in body
    assert isinstance(body["events"], list)


@pytest.mark.asyncio
async def test_calendar_ical_returns_icalendar(client, student_token):
    resp = await client.get(
        "/calendar/deadlines/ical",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/calendar")
    text = resp.text
    assert "BEGIN:VCALENDAR" in text
    assert "END:VCALENDAR" in text
