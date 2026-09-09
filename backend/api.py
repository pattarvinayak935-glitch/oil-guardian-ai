import sys
import os
import shutil
from pathlib import Path
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# 1. Path routing to access the ML modules
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

# Import the standardized inference nodes
from ml_modules.near_miss.inference import analyze as analyze_nm
from ml_modules.unsafe_condition.inference import analyze as analyze_uc
from ml_modules.unsafe_act.inference import analyze as analyze_ua

app = FastAPI(title="OIL Guardian AI - Multimodal Ensemble")

# 2. Allow frontend to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Initialize Multimodal Models on Startup
print("Text inference modules are ready. Whisper/EasyOCR load on first use.")
audio_model = None
ocr_reader = None

class ReportRequest(BaseModel):
    text: str

# 4. Core Ensemble Logic (Reused by all endpoints)
def process_text_ensemble(text: str) -> dict:
    clean_text = text.strip()
    if not clean_text:
        return {
            "category": "None",
            "risk_tier": "Low Risk",
            "sif_prob": "0.0%",
            "iogp_rule": "N/A",
            "ensemble_breakdown": {"near_miss": 0.0, "unsafe_act": 0.0, "unsafe_condition": 0.0}
        }

    # Query all 3 SIF-risk models. Their scores measure SIF likelihood;
    # the selected module is a routing heuristic, not a learned category model.
    res_nm = analyze_nm(clean_text)
    res_uc = analyze_uc(clean_text)
    res_ua = analyze_ua(clean_text)
    
    # Routing heuristic: choose the module with the highest SIF probability.
    all_results = [res_nm, res_uc, res_ua]
    dominant_result = max(all_results, key=lambda r: r["confidence"])
    
    overall_confidence = dominant_result["confidence"]
    
    # Determine Risk Tier
    if overall_confidence >= 75.0:
        risk_tier = "High Risk"
    elif overall_confidence >= 45.0:
        risk_tier = "Medium Risk"
    else:
        risk_tier = "Low Risk"
        
    return {
        "category": dominant_result["module"],
        "risk_tier": risk_tier,
        "sif_prob": f"{overall_confidence:.1f}%",
        "iogp_rule": dominant_result.get("iogp_rule", "Operational Safety"),
        "extracted_text": clean_text, # Returns the text so the UI can show what was transcribed
        "ensemble_breakdown": {
            "near_miss": res_nm["confidence"],
            "unsafe_act": res_ua["confidence"],
            "unsafe_condition": res_uc["confidence"]
        }
    }

# 5. API Endpoints
@app.post("/api/predict")
def predict_hazard_text(req: ReportRequest):
    """Endpoint for standard text input"""
    return process_text_ensemble(req.text)

@app.post("/api/predict/voice")
def predict_hazard_voice(file: UploadFile = File(...)):
    """Endpoint for audio file input"""
    import whisper
    global audio_model
    if audio_model is None:
        audio_model = whisper.load_model("base")
    temp_path = f"temp_audio_{Path(file.filename).name}"
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        result = audio_model.transcribe(temp_path)
        extracted_text = result.get("text", "")
        return process_text_ensemble(extracted_text)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.post("/api/predict/image")
def predict_hazard_image(file: UploadFile = File(...)):
    """Endpoint for handwritten image input"""
    import easyocr
    global ocr_reader
    if ocr_reader is None:
        ocr_reader = easyocr.Reader(["en"])
    temp_path = f"temp_img_{Path(file.filename).name}"
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        ocr_results = ocr_reader.readtext(temp_path)
        extracted_text = " ".join([text for _, text, _ in ocr_results])
        return process_text_ensemble(extracted_text)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

# 6. Serve the HTML frontend directly
FRONTEND_DIR = ROOT_DIR / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")