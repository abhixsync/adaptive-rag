"""
Per-user document registry backed by MongoDB.

Stores metadata about each uploaded document (not the file bytes or vectors):
the owning user, a document id matching the Qdrant payload, the filename, the
LLM-enhanced description, and the chunk count.
"""

from datetime import datetime
from typing import List

from src.db.mongo_client import db

collection = db["documents"]


async def add_document(
    user_id: str,
    doc_id: str,
    filename: str,
    description: str,
    chunk_count: int,
) -> None:
    """
    Insert a document registry record.

    Args:
        user_id: The owner of the document.
        doc_id: Unique id, matching the Qdrant ``metadata.doc_id`` payload.
        filename: Original uploaded filename.
        description: LLM-enhanced description of the document.
        chunk_count: Number of chunks stored in the vector store.
    """
    await collection.insert_one({
        "user_id": user_id,
        "doc_id": doc_id,
        "filename": filename,
        "description": description,
        "chunk_count": chunk_count,
        "created_at": datetime.utcnow(),
    })


async def list_documents(user_id: str) -> List[dict]:
    """
    List a user's documents, newest first.

    Args:
        user_id: The owner whose documents to list.

    Returns:
        A list of document records (without the Mongo ``_id`` field).
    """
    cursor = collection.find(
        {"user_id": user_id}, {"_id": 0}
    ).sort("created_at", -1)
    return await cursor.to_list(length=1000)


async def delete_document(user_id: str, doc_id: str) -> int:
    """
    Delete a user's document record.

    Args:
        user_id: The owner of the document.
        doc_id: The document id to delete.

    Returns:
        The number of records deleted (0 if not found / not owned by the user).
    """
    result = await collection.delete_one({"user_id": user_id, "doc_id": doc_id})
    return result.deleted_count
