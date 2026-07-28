from __future__ import annotations

from typing import Optional

from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session

from app.auth import get_user_id_from_request
from app.models import User


def current_user(request: Request, session: Session) -> Optional[User]:
    user_id = get_user_id_from_request(request)
    if not user_id:
        return None
    u = session.get(User, user_id)
    if u and getattr(u, "is_suspended", False):
        return None
    return u


def require_user(request: Request, session: Session) -> User:
    u = current_user(request, session)
    if not u:
        raise HTTPException(status_code=401, detail="Not signed in")
    return u
