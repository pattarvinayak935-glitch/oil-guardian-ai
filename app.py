import os
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components

# Configure page
st.set_page_config(
    page_title="OIL Guardian AI - SIH26165 Operations Hub",
    page_icon="🦺",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom CSS for seamless Streamlit iframe container integration
st.markdown(
    """
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .block-container {
            padding-top: 0rem !important;
            padding-bottom: 0rem !important;
            padding-left: 0rem !important;
            padding-right: 0rem !important;
            max-width: 100% !important;
        }
        iframe {
            border: none !important;
            width: 100% !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"

def load_html(file_name: str) -> str:
    file_path = FRONTEND_DIR / file_name
    if file_path.exists():
        return file_path.read_text(encoding="utf-8")
    return f"<h1>Error: {file_name} not found</h1>"

# Streamlit Sidebar Navigation
st.sidebar.title("🦺 OIL Guardian AI")
st.sidebar.caption("SIH26165 · Enterprise Safety Operations")

view_mode = st.sidebar.radio(
    "Select View Mode",
    [
        "🌟 Main Enterprise Hub",
        "🦺 Employee Field Terminal",
        "📊 Safety Officer Command Center",
    ],
)

if view_mode == "🌟 Main Enterprise Hub":
    html_content = load_html("index.html")
    components.html(html_content, height=950, scrolling=True)

elif view_mode == "🦺 Employee Field Terminal":
    html_content = load_html("employee.html")
    components.html(html_content, height=950, scrolling=True)

elif view_mode == "📊 Safety Officer Command Center":
    html_content = load_html("officer.html")
    components.html(html_content, height=950, scrolling=True)
