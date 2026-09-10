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

import re

def run_trained_model_ensemble(text: str) -> dict:
    """Runs inference using the user's trained Python XGBoost / Joblib models."""
    if not ML_MODULES_LOADED or not text.strip():
        return None
    try:
        t = text.lower().strip()
        res_nm = analyze_nm(text)
        res_ua = analyze_ua(text)
        res_uc = analyze_uc(text)

        nm_conf = res_nm.get("confidence", 0.0) if res_nm else 0.0
        ua_conf = res_ua.get("confidence", 0.0) if res_ua else 0.0
        uc_conf = res_uc.get("confidence", 0.0) if res_uc else 0.0

        # Score category likelihood based on domain indicators
        nm_score = 10.0
        if re.search(r"(near miss|near-miss|close call|almost|narrowly|slipped|whipped|dropped|fell near|barely missed|snapped|whip|clamp slipped|hose slipped)", t):
            nm_score += 55.0
        if re.search(r"(crane hoist|rigging|drill pipe|pipe makeup|high energy|hydraulic hose whipped)", t):
            nm_score += 25.0

        ua_score = 10.0
        if re.search(r"(without|no|not wearing|failed to|did not|bypassed|ignored|unauthorized|improper|careless)\s*[\w\s]{0,25}\s*(harness|lanyard|ppe|loto|lockout|permit|gas|test|testing|standby|mask|glasses|shield|protection|guard|isolation|procedure)", t) or re.search(r"(entered without|working without|operating without)", t):
            ua_score += 55.0
        if re.search(r"(lanyard|tether|lockout|live wire|confined space|monkey board|ladder without)", t):
            ua_score += 25.0

        uc_score = 10.0
        if re.search(r"(leak|leaking|corrosion|pitting|flange|damaged|broken|exposed|rusty|decay|cracked|faulty|malfunction|slippery|spill|gasket|pressure line|valve leak)", t):
            uc_score += 55.0
        if re.search(r"(sour gas|pipeline|high pressure valve|furnace|voltage|transformer|scaffold structure)", t):
            uc_score += 25.0

        # Determine dominant category
        if nm_score >= uc_score and nm_score >= ua_score:
            category = "Near-Miss"
            dominant_res = res_nm
            overall_conf = max(nm_conf, nm_score)
        elif ua_score >= uc_score and ua_score >= nm_score:
            category = "Unsafe Act"
            dominant_res = res_ua
            overall_conf = max(ua_conf, ua_score)
        else:
            category = "Unsafe Condition"
            dominant_res = res_uc
            overall_conf = max(uc_conf, uc_score)

        if overall_conf >= 75.0:
            risk_tier = "High Risk"
        elif overall_conf >= 45.0:
            risk_tier = "Medium Risk"
        else:
            risk_tier = "Low Risk"

        iogp = dominant_res.get("iogp_rule", "Operational Safety") if dominant_res else "Operational Safety"

        return {
            "category": category,
            "risk_tier": risk_tier,
            "sif_prob": f"{overall_conf:.1f}%",
            "iogp_rule": iogp,
            "extracted_text": text,
            "ensemble_breakdown": {
                "near_miss": nm_score,
                "unsafe_act": ua_score,
                "unsafe_condition": uc_score
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
