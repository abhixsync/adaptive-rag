"""
API routes for RAG operations (auth-gated, per-user).
"""

from fastapi import APIRouter, UploadFile, File, Header, Depends, HTTPException
from langchain_core.messages import HumanMessage, AIMessage

from src.auth.security import get_current_user
from src.db.documents import add_document, delete_document, list_documents
from src.memory.chat_history_mongo import ChatHistory
from src.models.query_request import QueryRequest
from src.rag.document_upload import documents
from src.rag.graph_builder import builder
from src.rag.retriever_setup import delete_document_vectors

router = APIRouter()


async def _retriever_description(user_id: str) -> str:
    """
    Build the retriever tool's scope text from a user's document descriptions.

    Args:
        user_id: The user whose documents describe the retriever scope.

    Returns:
        A joined description string, or a generic fallback if the user has none.
    """
    docs = await list_documents(user_id)
    descriptions = [d["description"] for d in docs if d.get("description")]
    if not descriptions:
        return "the user's uploaded documents"
    return "\n".join(descriptions)


@router.post("/rag/query")
async def rag_query(req: QueryRequest, user: str = Depends(get_current_user)):
    """
    Process a RAG query for the authenticated user and return the result.

    Args:
        req: The query request containing the query text.
        user: The authenticated username (from the Bearer token).

    Returns:
        The generated response from the RAG pipeline.
    """
    # Chat history is keyed by user so it persists across logins.
    chat_history = ChatHistory.get_session_history(user)
    await chat_history.add_message(HumanMessage(content=req.query))

    messages = await chat_history.get_messages()
    result = builder.invoke({
        "messages": messages,
        "user_id": user,
        "retriever_description": await _retriever_description(user),
    })
    output_text = result["messages"][-1].content

    await chat_history.add_message(AIMessage(content=output_text))

    return {"result": result["messages"][-1]}


@router.post("/rag/documents/upload")
async def upload_file(
    file: UploadFile = File(...),
    description: str = Header(..., alias="X-Description"),
    user: str = Depends(get_current_user),
):
    """
    Upload a document for the authenticated user.

    Args:
        file: The file to upload (PDF or TXT).
        description: Document description provided via header.
        user: The authenticated username (from the Bearer token).

    Returns:
        Upload status and the new document's id.
    """
    result = documents(description, file, user_id=user)

    if result["success"]:
        await add_document(
            user_id=user,
            doc_id=result["doc_id"],
            filename=result["filename"],
            description=result["description"],
            chunk_count=result["chunk_count"],
        )

    return {"status": result["success"], "doc_id": result["doc_id"]}


@router.get("/rag/documents")
async def get_documents(user: str = Depends(get_current_user)):
    """
    List the authenticated user's uploaded documents.

    Args:
        user: The authenticated username (from the Bearer token).

    Returns:
        A list of the user's document records.
    """
    return {"documents": await list_documents(user)}


@router.delete("/rag/documents/{doc_id}")
async def remove_document(doc_id: str, user: str = Depends(get_current_user)):
    """
    Delete one of the authenticated user's documents (vectors + registry).

    Args:
        doc_id: The id of the document to delete.
        user: The authenticated username (from the Bearer token).

    Returns:
        Deletion status.

    Raises:
        HTTPException: 404 if the document doesn't exist for this user.
    """
    deleted = await delete_document(user, doc_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")

    delete_document_vectors(user, doc_id)
    return {"status": "deleted", "doc_id": doc_id}
