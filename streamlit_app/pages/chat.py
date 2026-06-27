"""
Chat page for the Streamlit application (requires login).
"""

import streamlit as st

from utils.api_client import (
    delete_document,
    document_upload_rag,
    list_documents,
    query_backend,
)

# Configure page settings
st.set_page_config(
    page_title="LangGraph Chat",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get help": None,
        "Report a Bug": None,
        "About": None
    }
)

# Require authentication.
token = st.session_state.get("token")
if not token:
    st.warning("Please log in first.")
    st.stop()

# Header: title + logged-in user + logout.
col1, col2 = st.columns([8, 2])
with col1:
    st.title("💬 LangGraph Chat")
with col2:
    st.caption(f"Signed in as **{st.session_state.get('username', '')}**")
    if st.button("🔒 Logout", use_container_width=True):
        st.session_state.clear()
        st.switch_page("home.py")

# Sidebar: upload + the user's document library.
with st.sidebar:
    st.header("📂 Upload Documents")

    uploaded_file = st.file_uploader("Upload a PDF or TXT file", type=["pdf", "txt"])

    if uploaded_file:
        file_description = st.text_input(
            "📄 Describe your document (required)",
            max_chars=300,
            placeholder="E.g. LangGraph tutorial with workflows and code examples"
        )

        if "uploaded_files" not in st.session_state:
            st.session_state.uploaded_files = {}

        file_key = f"{uploaded_file.name}_{file_description}"

        if file_description:
            if file_key not in st.session_state.uploaded_files:
                with st.spinner("Uploading & indexing..."):
                    success = document_upload_rag(uploaded_file, file_description, token)
                if success:
                    st.success(f"Uploaded: {uploaded_file.name}")
                    st.session_state.uploaded_files[file_key] = True
                    st.rerun()
                else:
                    st.error(f"Document Upload Failed: {uploaded_file.name}")
            else:
                st.info(f"Uploaded: {uploaded_file.name}")
        else:
            st.warning("Please describe your document before uploading.")

    st.divider()

    # My Documents: list + delete.
    docs = list_documents(token)
    st.header(f"📚 My Documents ({len(docs)})")
    if not docs:
        st.caption("No documents yet. Upload one above.")
    for doc in docs:
        d_col1, d_col2 = st.columns([5, 1])
        with d_col1:
            st.write(f"📄 {doc['filename']}")
        with d_col2:
            if st.button("🗑️", key=f"del_{doc['doc_id']}", help="Delete"):
                if delete_document(doc["doc_id"], token):
                    st.toast(f"Deleted {doc['filename']}")
                    st.rerun()
                else:
                    st.error("Delete failed.")

# Initialize chat history
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Display existing chat history
for role, text in st.session_state.chat_history:
    st.chat_message(role).write(text)

# User input
user_input = st.chat_input("Ask a question...")

# Process user input and get response
if user_input:
    # Show the user's question immediately, before the backend call.
    st.session_state.chat_history.append(("user", user_input))
    st.chat_message("user").write(user_input)

    # Stream the answer area with a spinner while the backend works.
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = query_backend(user_input, token)
        st.write(response)

    st.session_state.chat_history.append(("assistant", response))
