"""HTTP dependency enforcing per-user API rate limits."""

from fastapi import Depends, HTTPException

from core.rate_limit import limiter
from security.auth import DemoUser, get_current_user


async def enforce_rate_limit(user: DemoUser = Depends(get_current_user)) -> None:
    allowed, retry_after, _remaining = limiter.consume(user.user_id)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Rate limit reached. Please wait before sending another request.",
            headers={"Retry-After": str(max(1, retry_after))},
        )
