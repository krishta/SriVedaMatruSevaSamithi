from datetime import datetime


def current_period(as_of: datetime | None = None) -> str:
    """Calendar-month numbering period key: "YYYY-MM", e.g. "2026-09" (PRD SY-01)."""
    dt = as_of or datetime.now()
    return f"{dt.year:04d}-{dt.month:02d}"