from __future__ import annotations

import os
from datetime import timedelta
from typing import Optional

from fastapi import Request, Response
from itsdangerous import BadSignature, URLSafeTimedSerializer
from passlib.context import CryptContext

from app.settings import settings


import bcrypt

serializer = URLSafeTimedSerializer(settings.SESSION_SECRET, salt="session")

SESSION_COOKIE = "astro_session"
SESSION_MAX_AGE_SECONDS = int(timedelta(days=7).total_seconds())


def hash_password(password: str) -> str:
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False


def set_session(response: Response, user_id: int) -> None:
    token = serializer.dumps({"user_id": user_id})
    is_prod_https = settings.SECURE_COOKIES and (os.environ.get("VERCEL") == "1" or not settings.DATABASE_URL.startswith("sqlite:///."))
    response.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        max_age=SESSION_MAX_AGE_SECONDS,
        samesite="lax",
        secure=is_prod_https,
    )


def clear_session(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE)


def get_user_id_from_request(request: Request) -> Optional[int]:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    try:
        data = serializer.loads(token, max_age=SESSION_MAX_AGE_SECONDS)
    except BadSignature:
        return None
    user_id = data.get("user_id")
    return int(user_id) if user_id is not None else None

