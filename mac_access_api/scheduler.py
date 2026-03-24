from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status

from mac_access_api.config import settings


def enforce_schedule() -> None:
    if not settings.schedule_enabled:
        return

    now = datetime.now(ZoneInfo(settings.schedule_timezone))
    current_hour = now.hour
    start_hour = settings.schedule_start_hour
    end_hour = settings.schedule_end_hour

    if start_hour <= end_hour:
        allowed = start_hour <= current_hour <= end_hour
    else:
        allowed = current_hour >= start_hour or current_hour <= end_hour

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=(
                f"API access locked by schedule. Allowed hours: {start_hour:02d}:00"
                f"-{end_hour:02d}:59 ({settings.schedule_timezone})"
            ),
        )
