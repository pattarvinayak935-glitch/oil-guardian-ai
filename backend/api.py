from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ml_modules.near_miss.inference import analyze as analyze_nm
from ml_modules.unsafe_act.inference import analyze as analyze_ua
from ml_modules.unsafe_condition.inference import analyze as analyze_uc


app = FastAPI(
    title="OIL Guardian AI Inference API",
    version="1.0.0",
)

# Explicitly allow the local Streamlit UI and sandboxed iframe origin.
# The UI and inference API use different ports, so this is cross-origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",
        "http://127.0.0.1:8501",
        "null",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_private_network=True,
)


class AnalyzeRequest(BaseModel):
    text: str
    category: str


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "OIL Guardian AI Inference API",
    }


@app.post("/api/analyze")
def analyze_report(request: AnalyzeRequest):
    text = request.text.strip()
    category = request.category.strip().lower()

    if not text:
        return {"error": "Report text is empty"}

    if category == "unsafe act":
        result = analyze_ua(text)

    elif category == "unsafe condition":
        result = analyze_uc(text)

    elif category in ("near miss", "near-miss"):
        result = analyze_nm(text)

    else:
        return {
            "error": "Unsupported category",
            "category_received": request.category,
        }

    confidence = float(result.get("confidence", 0.0))

    if confidence >= 75:
        risk_tier = "High Risk"
    elif confidence >= 45:
        risk_tier = "Medium Risk"
    else:
        risk_tier = "Low Risk"

    return {
        "category": result.get("module", request.category),
        "risk_tier": risk_tier,
        "sif_prob": f"{confidence:.1f}%",
        "is_sif": bool(result.get("is_sif", False)),
        "iogp_rule": result.get("iogp_rule", "Operational Safety"),
        "threshold": result.get("threshold"),
        "control_evidence": result.get("control_evidence", []),
        "controls_present": bool(result.get("controls_present", False)),
        "review_required": bool(result.get("review_required", False)),
        "extracted_text": text,
        "model_result": result,
    }