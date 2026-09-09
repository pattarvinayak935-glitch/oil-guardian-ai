import joblib
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parent
MODEL_PATH = MODULE_DIR / "models" / "xgboost_unsafe_model.pkl"

_embedder = None
_model = None

def _load_resources():
    global _embedder, _model
    if _embedder is None:
        from sentence_transformers import SentenceTransformer
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
    if _model is None and MODEL_PATH.exists():
        _model = joblib.load(MODEL_PATH)

def analyze(text: str) -> dict:
    if not text or not text.strip():
        return {"module": "Unsafe Condition", "confidence": 0.0, "is_sif": False, "iogp_rule": "Worksite Inspection"}

    _load_resources()
    if _model is None:
        return {"module": "Unsafe Condition", "confidence": 0.0, "is_sif": False, "iogp_rule": "Worksite Inspection"}

    vec = _embedder.encode([text])

    if hasattr(_model, "predict_proba"):
        probs = _model.predict_proba(vec)[0]
        prob = float(probs[1]) if len(probs) > 1 else float(probs[0])
    else:
        prob = float(_model.predict(vec)[0])

    conf_pct = round(prob * 100, 1)

    t = text.lower()
    if any(k in t for k in ["leak", "gas", "flange", "corrosion", "pressure"]):
        iogp = "Energy Isolation"
    elif any(k in t for k in ["electrical", "cable", "wire", "junction"]):
        iogp = "Electrical Safety"
    else:
        iogp = "Worksite Condition"

    return {
        "module": "Unsafe Condition",
        "confidence": conf_pct,
        "is_sif": conf_pct >= 65.0,
        "iogp_rule": iogp
    }