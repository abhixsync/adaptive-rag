"""
API client for communicating with the RAG backend (auth-gated).
"""

import logging

import requests

logger = logging.getLogger(__name__)

# Backend service URL (FastAPI: auth + RAG, requires a Bearer token).
PYTHON_BASE_URL = "http://127.0.0.1:8000"


def _auth_headers(token: str) -> dict:
    """Build the Authorization header for a Bearer token."""
    return {"Authorization": f"Bearer {token}"}


def signup(username: str, password: str) -> dict:
    """
    Register a new account.

    Args:
        username: Desired username.
        password: Desired password.

    Returns:
        On success, a dict with ``access_token`` and ``username``. On failure, a
        dict with an ``error`` message.
    """
    try:
        response = requests.post(
            f"{PYTHON_BASE_URL}/auth/signup",
            json={"username": username, "password": password},
        )
        if response.status_code == 200:
            return response.json()
        return {"error": response.json().get("detail", "Signup failed")}
    except requests.RequestException as e:
        logger.exception("Signup request failed: %s", e)
        return {"error": "Could not reach the server."}


def login(username: str, password: str) -> dict:
    """
    Authenticate and obtain an access token.

    Args:
        username: Account username.
        password: Account password.

    Returns:
        On success, a dict with ``access_token`` and ``username``. On failure, a
        dict with an ``error`` message.
    """
    try:
        response = requests.post(
            f"{PYTHON_BASE_URL}/auth/login",
            json={"username": username, "password": password},
        )
        if response.status_code == 200:
            return response.json()
        return {"error": response.json().get("detail", "Login failed")}
    except requests.RequestException as e:
        logger.exception("Login request failed: %s", e)
        return {"error": "Could not reach the server."}


def query_backend(query: str, token: str) -> str:
    """
    Send a query to the RAG backend.

    Args:
        query: The user's query text.
        token: The user's access token.

    Returns:
        Response text from the backend or an error message.
    """
    url = f"{PYTHON_BASE_URL}/rag/query"
    try:
        response = requests.post(
            url,
            json={"query": query},
            headers=_auth_headers(token),
            allow_redirects=False,
        )
        if response.status_code == 200:
            return response.json()["result"]["content"]
        return f"Error: {response.status_code} - {response.text}"
    except requests.RequestException as e:
        logger.exception("Query request failed: %s", e)
        return "Error: could not reach the server."


def document_upload_rag(file, description: str, token: str) -> bool:
    """
    Upload a document to the RAG system.

    Args:
        file: File object to upload.
        description: Description of the document.
        token: The user's access token.

    Returns:
        True if upload succeeds, False otherwise.
    """
    url = f"{PYTHON_BASE_URL}/rag/documents/upload"
    headers = {**_auth_headers(token), "X-Description": description}

    if not file:
        return False

    try:
        files = {"file": (file.name, file, file.type)}
        response = requests.post(url, files=files, headers=headers)
        return response.status_code == 200 and response.json().get("status") is True
    except requests.RequestException as e:
        logger.exception("Upload request failed: %s", e)
        return False


def list_documents(token: str) -> list:
    """
    List the current user's uploaded documents.

    Args:
        token: The user's access token.

    Returns:
        A list of document records (possibly empty).
    """
    try:
        response = requests.get(
            f"{PYTHON_BASE_URL}/rag/documents",
            headers=_auth_headers(token),
        )
        if response.status_code == 200:
            return response.json().get("documents", [])
        return []
    except requests.RequestException as e:
        logger.exception("List documents request failed: %s", e)
        return []


def delete_document(doc_id: str, token: str) -> bool:
    """
    Delete one of the current user's documents.

    Args:
        doc_id: The id of the document to delete.
        token: The user's access token.

    Returns:
        True if the document was deleted, False otherwise.
    """
    try:
        response = requests.delete(
            f"{PYTHON_BASE_URL}/rag/documents/{doc_id}",
            headers=_auth_headers(token),
        )
        return response.status_code == 200
    except requests.RequestException as e:
        logger.exception("Delete document request failed: %s", e)
        return False
