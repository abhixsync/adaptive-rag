"""
Query request model.
"""

from typing import Optional

from pydantic import BaseModel


class QueryRequest(BaseModel):
    """Request model for RAG queries.

    Chat history is keyed by the authenticated user, so ``session_id`` is
    optional and retained only for backward compatibility.
    """

    query: str
    session_id: Optional[str] = None