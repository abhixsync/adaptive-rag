"""
User account storage backed by MongoDB.
"""

from datetime import datetime
from typing import Optional

from src.db.mongo_client import db

collection = db["users"]

_index_ready = False


async def _ensure_index() -> None:
    """Create the unique index on username once per process."""
    global _index_ready
    if not _index_ready:
        await collection.create_index("username", unique=True)
        _index_ready = True


async def get_user(username: str) -> Optional[dict]:
    """
    Fetch a user document by username.

    Args:
        username: The username to look up.

    Returns:
        The user document, or None if no such user exists.
    """
    await _ensure_index()
    return await collection.find_one({"username": username})


async def create_user(username: str, password_hash: str) -> None:
    """
    Insert a new user document.

    Args:
        username: The unique username.
        password_hash: The bcrypt hash of the user's password.

    Raises:
        pymongo.errors.DuplicateKeyError: If the username already exists.
    """
    await _ensure_index()
    await collection.insert_one({
        "username": username,
        "password_hash": password_hash,
        "created_at": datetime.utcnow(),
    })
