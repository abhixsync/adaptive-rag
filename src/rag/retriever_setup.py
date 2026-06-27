"""
Retriever setup backed by a persistent, per-user Qdrant vector store.

All users' document chunks live in a single Qdrant collection. Each chunk's
payload carries a ``user_id`` and ``doc_id`` under its ``metadata``; retrieval is
always filtered by ``user_id`` so a user only ever sees their own documents.
"""

from langchain_core.documents import Document
from langchain_core.tools import create_retriever_tool
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from src.core.config import settings

embeddings = OpenAIEmbeddings()

COLLECTION = settings.USER_DOCS_COLLECTION

# Lazily initialized singletons (cheap, no network until first use).
_client = None
_vectorstore = None


def _get_client() -> QdrantClient:
    """Return a shared QdrantClient, creating it on first use."""
    global _client
    if _client is None:
        _client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY,
        )
    return _client


def _ensure_collection() -> None:
    """Create the collection and payload indexes if they don't exist yet."""
    client = _get_client()
    if not client.collection_exists(COLLECTION):
        # Derive the vector size from the embedding model so it always matches.
        dim = len(embeddings.embed_query("dimension probe"))
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config=qmodels.VectorParams(
                size=dim, distance=qmodels.Distance.COSINE
            ),
        )
        # Indexes make the user_id / doc_id filters fast and reliable.
        for field in ("metadata.user_id", "metadata.doc_id"):
            client.create_payload_index(
                collection_name=COLLECTION,
                field_name=field,
                field_schema=qmodels.PayloadSchemaType.KEYWORD,
            )


def _get_vectorstore() -> QdrantVectorStore:
    """Return a shared QdrantVectorStore over the user-documents collection."""
    global _vectorstore
    _ensure_collection()
    if _vectorstore is None:
        _vectorstore = QdrantVectorStore(
            client=_get_client(),
            collection_name=COLLECTION,
            embedding=embeddings,
        )
    return _vectorstore


def _user_filter(user_id: str) -> qmodels.Filter:
    """Build a Qdrant filter matching a single user's chunks."""
    return qmodels.Filter(
        must=[
            qmodels.FieldCondition(
                key="metadata.user_id",
                match=qmodels.MatchValue(value=user_id),
            )
        ]
    )


def retriever_chain(chunks: list[Document], user_id: str, doc_id: str) -> bool:
    """
    Store document chunks in Qdrant, tagged with the owning user and document.

    Args:
        chunks: The document chunks to embed and store.
        user_id: The owner of the document.
        doc_id: A unique identifier for this uploaded document.

    Returns:
        True if the chunks were stored successfully, False otherwise.
    """
    try:
        vectorstore = _get_vectorstore()
        for chunk in chunks:
            chunk.metadata = {
                **(chunk.metadata or {}),
                "user_id": user_id,
                "doc_id": doc_id,
            }
        vectorstore.add_documents(chunks)
        print(f"Stored {len(chunks)} chunks in Qdrant for user '{user_id}' (doc {doc_id})")
        return True
    except Exception as e:
        print(f"Error storing documents in Qdrant: {e}")
        return False


def get_retriever(user_id: str, description: str = None):
    """
    Get a retriever tool scoped to a single user's documents.

    Args:
        user_id: The user whose documents should be searchable.
        description: Optional text describing the user's documents, used in the
            tool instruction. Falls back to a generic phrase when absent.

    Returns:
        A LangChain retriever tool filtered to the given user's chunks.
    """
    vectorstore = _get_vectorstore()
    retriever = vectorstore.as_retriever(
        search_kwargs={"filter": _user_filter(user_id)}
    )

    desc = description or "the user's uploaded documents"
    return create_retriever_tool(
        retriever,
        "retriever_customer_uploaded_documents",
        f"Use this tool **only** to answer questions about: {desc}\n"
        "Don't use this tool to answer anything else.",
    )


def delete_document_vectors(user_id: str, doc_id: str) -> None:
    """
    Delete all stored vectors for a given document owned by a user.

    Args:
        user_id: The owner of the document.
        doc_id: The document identifier whose chunks should be removed.
    """
    client = _get_client()
    _ensure_collection()
    client.delete(
        collection_name=COLLECTION,
        points_selector=qmodels.FilterSelector(
            filter=qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="metadata.user_id",
                        match=qmodels.MatchValue(value=user_id),
                    ),
                    qmodels.FieldCondition(
                        key="metadata.doc_id",
                        match=qmodels.MatchValue(value=doc_id),
                    ),
                ]
            )
        ),
    )
