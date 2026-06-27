"""
Document upload and processing module.
"""

import os
import tempfile
import uuid

from fastapi import UploadFile, File, HTTPException
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.rag.retriever_setup import retriever_chain
from src.tools.common_tools import enhance_description_with_llm


def documents(description: str, file: UploadFile, user_id: str) -> dict:
    """
    Process and store an uploaded document for a specific user.

    Validates the file type, loads and chunks the content, enhances the
    description with the LLM, and stores the chunks in Qdrant tagged with the
    user and a freshly generated document id.

    Args:
        description: User-provided document description.
        file: The uploaded file (PDF or TXT).
        user_id: The owner of the document.

    Returns:
        A dict with keys: success (bool), doc_id (str), filename (str),
        description (str, LLM-enhanced), chunk_count (int).

    Raises:
        HTTPException: If the file type is unsupported or loading fails.
    """
    filename = file.filename
    print(filename)
    if not filename.endswith(".pdf") and not filename.endswith(".txt"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF and TXT files are supported"
        )

    file_bytes = file.file.read()

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=os.path.splitext(filename)[1]
    ) as tmp_file:
        tmp_file.write(file_bytes)
        tmp_path = tmp_file.name

    if filename.endswith(".pdf"):
        loader = PyPDFLoader(tmp_path)
    else:
        loader = TextLoader(tmp_path, encoding="utf-8")

    try:
        docs = loader.load()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error loading file: {e}"
        )
    finally:
        os.unlink(tmp_path)

    # Enhance the description using the LLM (used as the retriever tool scope).
    description_llm = enhance_description_with_llm(description)

    # Split documents into chunks.
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150
    )
    chunks = splitter.split_documents(docs)

    doc_id = str(uuid.uuid4())
    success = retriever_chain(chunks, user_id=user_id, doc_id=doc_id)

    return {
        "success": success,
        "doc_id": doc_id,
        "filename": filename,
        "description": description_llm,
        "chunk_count": len(chunks),
    }
