import os
import sys
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

# Configure Streamlit page for PC and Mobile devices
st.set_page_config(
    page_title="OIL Guardian AI - SIH26165 Operations Hub",
    page_icon="🦺",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Load trained Python ML modules (XGBoost / Joblib models)
ML_MODULES_LOADED = False
try:
    from ml_modules.near_miss.inference import analyze as analyze_nm
    from ml_modules.unsafe_act.inference import analyze as analyze_ua
    from ml_modules.unsafe_condition.inference import analyze as analyze_uc
    ML_MODULES_LOADED = True
except Exception as e:
    print(f"ML Modules notice: {e}")

def run_trained_model_ensemble(text: str) -> dict:
    """Runs inference using the user's trained Python XGBoost / Joblib models."""
    if not ML_MODULES_LOADED or not text.strip():
        return None
    try:
        res_nm = analyze_nm(text)
        res_ua = analyze_ua(text)
        res_uc = analyze_uc(text)

        all_results = [res_nm, res_ua, res_uc]
        dominant = max(all_results, key=lambda r: r.get("confidence", 0.0))
        overall_conf = dominant.get("confidence", 0.0)

        if overall_conf >= 75.0:
            risk_tier = "High Risk"
        elif overall_conf >= 45.0:
            risk_tier = "Medium Risk"
        else:
            risk_tier = "Low Risk"

        return {
            "category": dominant.get("module", "Unsafe Condition"),
            "risk_tier": risk_tier,
            "sif_prob": f"{overall_conf:.1f}%",
            "iogp_rule": dominant.get("iogp_rule", "Operational Safety"),
            "extracted_text": text,
            "ensemble_breakdown": {
                "near_miss": res_nm.get("confidence", 0.0),
                "unsafe_act": res_ua.get("confidence", 0.0),
                "unsafe_condition": res_uc.get("confidence", 0.0)
            }
        }
    except Exception as exc:
        print(f"Inference execution notice: {exc}")
        return None

# Responsive styling for Mobile & Desktop displays
st.markdown(
    """
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .block-container {
            padding: 0rem !important;
            max-width: 100% !important;
        }
        iframe {
            border: none !important;
            width: 100% !important;
            min-height: 100vh !important;
            -webkit-overflow-scrolling: touch !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

FRONTEND_DIR = BASE_DIR / "frontend"

def load_html(file_name: str) -> str:
    file_path = FRONTEND_DIR / file_name
    if file_path.exists():
        return file_path.read_text(encoding="utf-8")
    return f"<h1>Error: {file_name} not found</h1>"

# Streamlit Sidebar Navigation
st.sidebar.title("🦺 OIL Guardian AI")
st.sidebar.caption("SIH26165 · Enterprise Safety Operations")
if ML_MODULES_LOADED:
    st.sidebar.success("✅ Trained Python ML Models (XGBoost/Joblib) Active")

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
    components.html(html_content, height=1000, scrolling=True)

elif view_mode == "🦺 Employee Field Terminal":
    html_content = load_html("employee.html")
    components.html(html_content, height=1000, scrolling=True)

elif view_mode == "📊 Safety Officer Command Center":
    html_content = load_html("officer.html")
    components.html(html_content, height=1000, scrolling=True)
