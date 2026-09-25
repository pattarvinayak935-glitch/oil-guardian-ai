"""Runtime inference adapter for the V4 Unsafe Act SIF classifier."""

import joblib
from pathlib import Path


# V4 model is stored in the separate model-development project
MODEL_PATH = (
    Path(r"C:\Users\Vinayak Pattar\OneDrive\Desktop\oil-safety-classifier-backup")
    / "models"
    / "unsafe_act_sif_v4_model.joblib"
)

_model = None

# V4 threshold selected using the validation set
SIF_THRESHOLD = 0.34


def _load_resources():
    global _model

    if _model is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Unsafe Act V4 model not found: {MODEL_PATH}"
            )

        _model = joblib.load(MODEL_PATH)


def analyze(text: str) -> dict:
    text = (text or "").strip()

    if not text:
        return {
            "module": "Unsafe Act",
            "confidence": 0.0,
            "is_sif": False,
            "iogp_rule": "Safe Work Practice",
        }

    _load_resources()

    probabilities = (
        _model.predict_proba([text])[0]
        if hasattr(_model, "predict_proba")
        else None
    )

    if probabilities is not None and len(probabilities) > 1:
        sif_prob = float(probabilities[1])
    else:
        prediction = int(_model.predict([text])[0])
        sif_prob = float(prediction)

    # V4 uses 0.34 as the SIF decision threshold
    is_sif = sif_prob >= SIF_THRESHOLD

    conf_pct = round(sif_prob * 100, 1)

    t = text.lower()

    if any(
        k in t
        for k in [
            "lockout",
            "loto",
            "isolation",
            "energized",
            "live wire",
        ]
    ):
        rule = "Energy Isolation"

    elif any(
        k in t
        for k in [
            "confined space",
            "gas test",
            "atmosphere",
        ]
    ):
        rule = "Confined Space"

    elif any(
        k in t
        for k in [
            "fall",
            "height",
            "scaffold",
            "harness",
        ]
    ):
        rule = "Working at Height"

    elif any(
        k in t
        for k in [
            "lifting",
            "crane",
            "suspended load",
            "rigging",
        ]
    ):
        rule = "Safe Mechanical Lifting"

    elif any(
        k in t
        for k in [
            "hot work",
            "welding",
            "cutting",
            "grinding",
        ]
    ):
        rule = "Hot Work"

    else:
        rule = "Operational Safety"

    return {
        "module": "Unsafe Act",
        "confidence": conf_pct,
        "is_sif": is_sif,
        "iogp_rule": rule,
        "threshold": SIF_THRESHOLD,
    }