from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status

from mac_access_api.config import settings


def enforce_schedule() -> None:
    if not settings.schedule_enabled:
        return

    start = settings.schedule_start_hour
    end = settings.schedule_end_hour

    # Guard against ambiguous zero-width window
    if start == end:
        return

    try:
        now = datetime.now(ZoneInfo(settings.schedule_timezone))
    except Exception:
        return  # bad timezone string — fail open rather than lock out

    h = now.hour
    if start < end:
        allowed = start <= h <= end
    else:
        # Overnight window e.g. 22:00 – 06:00
        allowed = h >= start or h <= end

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=(
                f"API locked by schedule. Allowed: {start:02d}:00\u2013{end:02d}:59 "
                f"({settings.schedule_timezone})"
            ),
        )
