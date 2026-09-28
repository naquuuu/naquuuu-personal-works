"""Small, tested runtime guards for the pinned Hermes relay."""
from __future__ import annotations

import asyncio


def transient(exc: Exception) -> bool:
    status = getattr(exc, "status_code", None) or getattr(getattr(exc, "response", None), "status_code", None)
    return status in (408, 429, 500, 502, 503, 504) or isinstance(exc, (TimeoutError, ConnectionError))


async def retry_primary(call, *, retries=2, sleep=asyncio.sleep):
    """At most two retries; callers retain their existing fallback ladder."""
    for attempt in range(min(2, max(0, retries)) + 1):
        try:
            return await call()
        except Exception as exc:
            if not transient(exc) or attempt >= min(2, max(0, retries)):
                raise
            await sleep(2 ** attempt)


async def vision_budget(call, *, timeout=45):
    """Bound the complete vision stage, including retries and fallbacks."""
    return await asyncio.wait_for(call(), timeout=timeout)
