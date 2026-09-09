"""Runtime inference adapter for the Near Miss SIF model."""
import joblib
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parent
MODEL_PATH = MODULE_DIR / "models" / "xgboost_near_miss_model.pkl"

_model = None
_embedder = None

def _load_resources():
    global _model, _embedder
    if _model is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(f"Near Miss model not found: {MODEL_PATH}")
        _model = joblib.load(MODEL_PATH)
    if _embedder is None:
        from sentence_transformers import SentenceTransformer
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")

def analyze(text: str) -> dict:
    text = (text or "").strip()
    if not text:
        return {"module": "Near Miss", "confidence": 0.0, "is_sif": False,
                "iogp_rule": "Incident Prevention"}

    _load_resources()
    try:
        vec = _embedder.encode([text])
        if hasattr(_model, "predict_proba"):
            probs = _model.predict_proba(vec)[0]
            score = float(probs[1]) if len(probs) > 1 else float(probs[0])
        else:
            score = float(_model.predict(vec)[0])
    except Exception as exc:
        raise RuntimeError(f"Near Miss model inference failed: {exc}") from exc

    conf_pct = round(score * 100 if 0 <= score <= 1 else score, 1)
    return {"module": "Near Miss", "confidence": conf_pct,
            "is_sif": conf_pct >= 70.0, "iogp_rule": "Incident Prevention"}
