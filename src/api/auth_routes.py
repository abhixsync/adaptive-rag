"""
Authentication routes: signup and login.
"""

from fastapi import APIRouter, HTTPException
from pymongo.errors import DuplicateKeyError

from src.auth.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from src.db.users import create_user, get_user
from src.models.auth_request import AuthRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=TokenResponse)
async def signup(req: AuthRequest):
    """
    Create a new user account and return an access token.

    Args:
        req: The username and password to register.

    Returns:
        A token response with a JWT for the new user.

    Raises:
        HTTPException: 400 if the username is taken or input is empty.
    """
    if not req.username or not req.password:
        raise HTTPException(status_code=400, detail="Username and password required")

    try:
        await create_user(req.username, hash_password(req.password))
    except DuplicateKeyError:
        raise HTTPException(status_code=400, detail="Username already exists")

    token = create_access_token(req.username)
    return TokenResponse(access_token=token, username=req.username)


@router.post("/login", response_model=TokenResponse)
async def login(req: AuthRequest):
    """
    Authenticate a user and return an access token.

    Args:
        req: The username and password to verify.

    Returns:
        A token response with a JWT on success.

    Raises:
        HTTPException: 401 if the credentials are invalid.
    """
    user = await get_user(req.username)
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token(req.username)
    return TokenResponse(access_token=token, username=req.username)
