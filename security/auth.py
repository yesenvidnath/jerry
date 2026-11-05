"""Demo authentication backed by server-side token-to-role assignments.

Replace local fallback tokens before deploying beyond a private demo environment.
"""

import os
import secrets
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

from fastapi import Header, HTTPException


@dataclass(frozen=True)
class DemoUser:
    user_id: str
    role: str


DEFAULT_DEMO_USERS = {
    "viewer_demo": ("VIEWER_DEMO_TOKEN", "viewer-demo-token", "Viewer"),
    "analyst_demo": ("ANALYST_DEMO_TOKEN", "analyst-demo-token", "Analyst"),
    "admin_demo": ("ADMIN_DEMO_TOKEN", "admin-demo-token", "Administrator"),
}


def token_for_user(user_id: str) -> str:
    if user_id not in DEFAULT_DEMO_USERS:
        raise KeyError(user_id)
    env_name, fallback, _role = DEFAULT_DEMO_USERS[user_id]
    return os.getenv(env_name, fallback)


def authenticate_token(token: str | None) -> DemoUser:
    if not token:
        raise HTTPException(status_code=401, detail="A valid X-Demo-Token is required.")
    for user_id, (env_name, fallback, role) in DEFAULT_DEMO_USERS.items():
        configured = os.getenv(env_name, fallback)
        if secrets.compare_digest(token, configured):
            return DemoUser(user_id=user_id, role=role)
    raise HTTPException(status_code=401, detail="Invalid demo credentials.")


async def get_current_user(x_demo_token: str | None = Header(default=None, alias="X-Demo-Token")) -> DemoUser:
    return authenticate_token(x_demo_token)
