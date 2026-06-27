"""
Login / signup page. Authenticates against the FastAPI backend and stores the
access token in the session before redirecting to the chat page.
"""

import logging

import streamlit as st

from utils.api_client import login, signup

st.set_page_config(
    page_title="LangGraph Chat - Login",
    initial_sidebar_state="collapsed",
)

# Fully hide the sidebar (and its expand arrow) on the login page.
hide_sidebar_style = """
    <style>
        [data-testid="stSidebar"] { display: none; }
        [data-testid="stSidebarNav"] { display: none; }
        [data-testid="stSidebarCollapsedControl"] { display: none; }
    </style>
"""
st.markdown(hide_sidebar_style, unsafe_allow_html=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="app.log",
    filemode="a",
)

# Already logged in? Go straight to chat.
if st.session_state.get("token"):
    st.switch_page("pages/chat.py")

st.title("🔐 Welcome to LangGraph Assistant")

mode = st.radio("Choose action:", ["Login", "Create Account"], horizontal=True)

with st.form("auth_form"):
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    submit = st.form_submit_button("Submit")

if submit:
    if not username or not password:
        st.error("Username and password required.")
    else:
        action = signup if mode == "Create Account" else login
        result = action(username, password)
        if "access_token" in result:
            st.session_state["token"] = result["access_token"]
            st.session_state["username"] = result["username"]
            st.switch_page("pages/chat.py")
        else:
            st.error(result.get("error", "Authentication failed."))
