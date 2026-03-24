from __future__ import annotations

from fastapi import Header, HTTPException, status

from mac_access_api.config import settings


async def verify_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if settings.api_key == "change-me-now" and not settings.allow_insecure_default_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Default API key is not allowed. Run ./scripts/bootstrap.sh to generate a secure key.",
        )

    if x_api_key != settings.api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
