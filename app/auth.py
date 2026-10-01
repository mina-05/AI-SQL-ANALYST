import hashlib
import hmac
import os
import time

import jwt
from fastapi import Header, HTTPException

from . import config, store

_ITERATIONS = 200_000


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
    return f"pbkdf2${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt_hex, digest_hex = stored.split("$")
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), _ITERATIONS)
        return hmac.compare_digest(digest.hex(), digest_hex)
    except ValueError:
        return False


# Used when a username does not exist, so login takes the same time either way.
DUMMY_HASH = hash_password("not-a-real-password")


def make_token(user_id: int) -> str:
    now = int(time.time())
    payload = {"sub": str(user_id), "iat": now, "exp": now + config.TOKEN_HOURS * 3600}
    return jwt.encode(payload, config.SECRET_KEY, algorithm="HS256")


def current_user(authorization: str | None = Header(default=None)) -> dict:
    """FastAPI dependency: returns {"id", "username"} or raises 401."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Sign in to continue.")
    try:
        payload = jwt.decode(authorization[7:].strip(), config.SECRET_KEY, algorithms=["HS256"])
        user = store.get_user(int(payload["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(401, "Your session expired. Sign in again.")
    if not user:
        raise HTTPException(401, "Your session expired. Sign in again.")
    return user
