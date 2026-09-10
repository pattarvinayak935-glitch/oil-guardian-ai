"""Runtime inference adapter for the V3 Unsafe Act SIF classifier."""
import joblib
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parent
MODEL_PATH = MODULE_DIR / "models" / "unsafe_act_sif_v3_model.joblib"
_model = None

def _load_resources():
    global _model
    if _model is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(f"Unsafe Act V3 model not found: {MODEL_PATH}")
        _model = joblib.load(MODEL_PATH)

def analyze(text: str) -> dict:
    text = (text or "").strip()
    if not text:
        return {"module": "Unsafe Act", "confidence": 0.0, "is_sif": False,
                "iogp_rule": "Safe Work Practice"}

    _load_resources()
    prediction = int(_model.predict([text])[0])
    probabilities = _model.predict_proba([text])[0] if hasattr(_model, "predict_proba") else None
    sif_prob = float(probabilities[1]) if probabilities is not None and len(probabilities) > 1 else float(prediction)
    conf_pct = round(sif_prob * 100, 1)

    t = text.lower()
    if any(k in t for k in ["lockout", "loto", "isolation", "energized", "live wire"]):
        rule = "Energy Isolation"
    elif any(k in t for k in ["confined space", "gas test", "atmosphere"]):
        rule = "Confined Space"
    elif any(k in t for k in ["fall", "height", "scaffold", "harness"]):
        rule = "Working at Height"
    else:
        rule = "Operational Safety"

    return {"module": "Unsafe Act", "confidence": conf_pct,
            "is_sif": prediction == 1, "iogp_rule": rule}
