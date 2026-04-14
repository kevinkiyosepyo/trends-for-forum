from datetime import datetime, timezone


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def hours_ago(n: int) -> datetime:
    from datetime import timedelta
    return datetime.now(timezone.utc) - timedelta(hours=n)
