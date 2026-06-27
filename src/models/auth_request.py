"""
Request/response models for authentication endpoints.
"""

from pydantic import BaseModel


class AuthRequest(BaseModel):
    """Credentials for signup and login."""

    username: str
    password: str


class TokenResponse(BaseModel):
    """Issued access token returned on successful login."""

    access_token: str
    username: str
