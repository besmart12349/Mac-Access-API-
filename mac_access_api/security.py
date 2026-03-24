from __future__ import annotations

import hmac
import time
from collections import defaultdict
from threading import Lock

from fastapi import Header, HTTPException, Request, status

from mac_access_api.config import settings

# Simple in-process rate limiter: max 60 requests per 60s per IP
_rate_store: dict[str, list[float]] = defaultdict(list)
_rate_lock = Lock()
RATE_LIMIT = 60
RATE_WINDOW = 60.0


def _check_rate_limit(ip: str) -> None:
    now = time.monotonic()
    with _rate_lock:
        timestamps = _rate_store[ip]
        _rate_store[ip] = [t for t in timestamps if now - t < RATE_WINDOW]
        if len(_rate_store[ip]) >= RATE_LIMIT:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Max 60 requests per 60 seconds.",
            )
        _rate_store[ip].append(now)


async def verify_api_key(
    request: Request,
    x_api_key: str | None = Header(default=None),
) -> None:
    # Reject the hardcoded default key — forces user to set a real key
    if settings.api_key == "change-me-now":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API key is not configured. Set MAC_ACCESS_API_KEY in your .env file.",
        )
    if x_api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    # Constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(x_api_key, settings.api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    # Rate limit by client IP
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)
