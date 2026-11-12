"""Job dates preserve the precision and offset supplied by the publisher."""

from datetime import date, datetime, timezone


def parse_job_date(value: object) -> date | datetime | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    try:
        if len(value) == 10 and value[4] == value[7] == "-":
            return date.fromisoformat(value)
        timestamp = datetime.fromisoformat(value)
    except ValueError:
        return None
    return timestamp if timestamp.utcoffset() is not None else None


def job_expired(deadline: date | datetime, now: date | datetime) -> bool:
    if isinstance(deadline, datetime):
        return isinstance(now, datetime) and deadline <= now
    today = now.astimezone(timezone.utc).date() if isinstance(now, datetime) else now
    return deadline < today


def job_not_yet_published(publication: date | datetime, now: datetime) -> bool:
    if isinstance(publication, datetime):
        return publication > now
    return publication > now.astimezone(timezone.utc).date()
