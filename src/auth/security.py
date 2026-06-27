"""
Password hashing and JWT helpers for authentication.
"""

from datetime import datetime, timedelta

import bcrypt
import jwt
from fastapi import Header, HTTPException

from src.core.config import settings


def hash_password(password: str) -> str:
    """
    Hash a plaintext password with bcrypt.

    Args:
        password: The plaintext password.

    Returns:
        The bcrypt hash as a UTF-8 string suitable for storage.
    """
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """
    Check a plaintext password against a stored bcrypt hash.

    Args:
        password: The plaintext password to check.
        password_hash: The stored bcrypt hash.

    Returns:
        True if the password matches, False otherwise.
    """
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(username: str) -> str:
    """
    Create a signed JWT access token for a user.

    Args:
        username: The subject (username) to encode in the token.

    Returns:
        The encoded JWT string.
    """
    expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {"sub": username, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> str:
    """
    Decode a JWT and return the username it identifies.

    Args:
        token: The encoded JWT string.

    Returns:
        The username (the token's "sub" claim).

    Raises:
        HTTPException: 401 if the token is invalid, expired, or malformed.
    """
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    return username


def get_current_user(authorization: str = Header(None)) -> str:
    """
    FastAPI dependency that extracts the current user from the Bearer token.

    Args:
        authorization: The raw Authorization header ("Bearer <token>").

    Returns:
        The authenticated username.

    Raises:
        HTTPException: 401 if the header is missing or the token is invalid.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = authorization.split(" ", 1)[1].strip()
    return decode_token(token)
