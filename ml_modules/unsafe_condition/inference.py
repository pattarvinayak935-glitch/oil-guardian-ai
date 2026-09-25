import re
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


def _is_negated(text: str, match_start: int) -> bool:
    """
    Checks whether a detected control word/phrase is negated.

    Examples treated as NEGATED:
        not isolated
        has not been isolated
        was not repaired
        without isolation
        without being isolated
        failed to isolate
        did not repair
        no isolation
        not yet repaired
    """

    preceding = text[max(0, match_start - 100):match_start]

    negation_pattern = re.compile(
        r"""
        (?:
            \bnot\b
            |
            \bno\b
            |
            \bwithout\b
            |
            \bnever\b
            |
            \bfailed\s+to\b
            |
            \bdid\s+not\b
            |
            \bdoes\s+not\b
            |
            \bdo\s+not\b
            |
            \bhas\s+not\b
            |
            \bhave\s+not\b
            |
            \bhad\s+not\b
            |
            \bwas\s+not\b
            |
            \bwere\s+not\b
            |
            \bis\s+not\b
            |
            \bare\s+not\b
            |
            \bnot\s+yet\b
        )
        (?:\s+\b[\w'-]+\b){0,5}
        \s*$
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    return bool(negation_pattern.search(preceding))


def _extract_control_evidence(text: str) -> list[str]:
    """
    Detect explicit positive control/remediation evidence.

    IMPORTANT:
    This function does NOT change the trained model's score.
    It only identifies control evidence for HSE review.

    Negated statements are explicitly excluded.
    """

    t = text.lower()
    controls = []

    control_patterns = {
        "Isolation applied": [
            r"\bisolated\b",
            r"\bisolation was applied\b",
            r"\bequipment was isolated\b",
            r"\bcircuit was isolated\b",
            r"\benergy was isolated\b",
            r"\benergy isolated\b",
        ],

        "LOTO applied": [
            r"\blocked out\b",
            r"\blocked out and tagged\b",
            r"\blockout\b",
            r"\btagout\b",
            r"\btagged out\b",
            r"\bloto\b",
        ],

        "Hazard removed from service": [
            r"\bremoved from service\b",
            r"\btaken out of service\b",
            r"\bequipment was removed\b",
        ],

        "Repair completed": [
            r"\brepaired\b",
            r"\brepair completed\b",
            r"\bwas repaired\b",
            r"\breplaced\b",
            r"\breplacement completed\b",
            r"\brepair was completed\b",
        ],

        "Area made safe": [
            r"\bmade safe\b",
            r"\barea was made safe\b",
            r"\barea made safe\b",
            r"\bmade safe before work\b",
        ],

        "Authorized personnel involved": [
            r"\bauthorized electrician\b",
            r"\bauthorized person\b",
            r"\bauthorized personnel\b",
            r"\bcompetent person\b",
        ],

        "Zero energy verified": [
            r"\bzero energy was verified\b",
            r"\bzero energy verified\b",
            r"\bverified zero energy\b",
            r"\benergy was verified\b",
            r"\babsence of energy was verified\b",
        ],

        "Work resumed after controls": [
            r"\bbefore work resumed\b",
            r"\bwork resumed after\b",
            r"\bwork resumed once\b",
            r"\bbefore resuming work\b",
            r"\bafter controls were applied\b",
        ],
    }

    for label, patterns in control_patterns.items():
        found = False

        for pattern in patterns:
            for match in re.finditer(pattern, t, re.IGNORECASE):

                # Ignore the match when the control is negated.
                if _is_negated(t, match.start()):
                    continue

                found = True
                break

            if found:
                break

        if found:
            controls.append(label)

    return controls


def _map_iogp_rule(text: str) -> str:
    """
    Maps the report to the existing application rule labels.
    """

    t = text.lower()

    if any(
        keyword in t
        for keyword in [
            "leak",
            "leaking",
            "gas",
            "flange",
            "corrosion",
            "pressure",
            "pitting",
        ]
    ):
        return "Energy Isolation"

    if any(
        keyword in t
        for keyword in [
            "electrical",
            "cable",
            "wire",
            "junction",
            "electric",
            "voltage",
            "energized",
        ]
    ):
        return "Electrical Safety"

    return "Worksite Condition"


def analyze(text: str) -> dict:
    """
    Run the existing trained Unsafe Condition model.

    The model confidence is preserved exactly as produced by XGBoost.
    Control evidence is returned separately and does NOT modify the score.
    """

    if not text or not text.strip():
        return {
            "module": "Unsafe Condition",
            "confidence": 0.0,
            "is_sif": False,
            "iogp_rule": "Worksite Inspection",
            "control_evidence": [],
            "controls_present": False,
            "review_required": False,
        }

    _load_resources()

    if _model is None:
        return {
            "module": "Unsafe Condition",
            "confidence": 0.0,
            "is_sif": False,
            "iogp_rule": "Worksite Inspection",
            "control_evidence": [],
            "controls_present": False,
            "review_required": False,
        }

    # Generate the embedding using the EXISTING model pipeline.
    vec = _embedder.encode([text])

    # Get the EXISTING trained-model score.
    if hasattr(_model, "predict_proba"):
        probs = _model.predict_proba(vec)[0]

        if len(probs) > 1:
            prob = float(probs[1])
        else:
            prob = float(probs[0])
    else:
        prob = float(_model.predict(vec)[0])

    # Preserve the original model score.
    conf_pct = round(prob * 100, 1)

    # Existing Unsafe Condition threshold.
    is_sif = conf_pct >= 65.0

    # Existing rule mapping.
    iogp = _map_iogp_rule(text)

    # Separate control-evidence layer.
    control_evidence = _extract_control_evidence(text)

    controls_present = len(control_evidence) > 0

    # High model signal + completed controls = human review.
    # We intentionally DO NOT modify the model score.
    review_required = bool(is_sif and controls_present)

    return {
        "module": "Unsafe Condition",
        "confidence": conf_pct,
        "is_sif": is_sif,
        "iogp_rule": iogp,
        "control_evidence": control_evidence,
        "controls_present": controls_present,
        "review_required": review_required,
    }