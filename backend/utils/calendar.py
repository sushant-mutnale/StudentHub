from datetime import datetime
from uuid import uuid4


def build_ics_event(
    uid_prefix: str,
    title: str,
    description: str,
    start: datetime,
    end: datetime,
    organizer_email: str,
    attendee_email: str,
    location: str | None = None,
    timezone: str = "UTC",
) -> str:
    uid = f"{uid_prefix}-{uuid4()}@studenthub"
    dt_format = "%Y%m%dT%H%M%SZ"
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//StudentHub//Scheduling//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:REQUEST",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{datetime.utcnow().strftime(dt_format)}",
        f"DTSTART:{start.strftime(dt_format)}",
        f"DTEND:{end.strftime(dt_format)}",
        f"SUMMARY:{title}",
        f"DESCRIPTION:{description}",
        f"ORGANIZER:mailto:{organizer_email}",
        f"ATTENDEE;CN={attendee_email}:mailto:{attendee_email}",
    ]
    if location:
        lines.append(f"LOCATION:{location}")
    lines.extend(["END:VEVENT", "END:VCALENDAR"])
    return "\r\n".join(lines)


