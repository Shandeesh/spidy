import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys
import os

# Force console output to use UTF-8 to prevent cp1252 UnicodeEncodeErrors on Windows
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Ensure we can import SpidyBrain
sys.path.append(os.path.dirname(__file__))
from spidy_brain import SpidyBrain
from antigravity_pipeline import AntigravityPipeline

app = FastAPI(title="Spidy AI Brain Server")

# FIX #3: Restrict CORS to known local origins (was wildcard "*")
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5000",
    "http://127.0.0.1:5000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Brain ONCE at startup
brain = SpidyBrain()

class QueryRequest(BaseModel):
    query: str
    image: str = None
    persona: str = "cyberpunk"
    model_mode: str = "turbo"  # UPGRADE 5: 'turbo' = Gemini Flash, 'deep' = Gemini Pro

@app.post("/api/ask")
async def ask_brain(request: QueryRequest):
    try:
        # UPGRADE 5: Pass model_mode to SpidyBrain so it picks Flash vs Pro
        decision = brain.decide_intent(
            request.query,
            image_data=request.image,
            persona=request.persona,
            model_mode=request.model_mode
        )
        return decision
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/listen")
async def listen_brain():
    try:
        # Trigger voice listening
        text = brain.listen_to_user()
        return {"transcript": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status")
async def status():
    return {"status": "online", "model": "Gemini/GPT"}

class ConfigUpdateRequest(BaseModel):
    floor: str
    auto_update: bool
    plan_mode: bool
    strict_testing: bool
    max_retries: int

class FeedbackRequest(BaseModel):
    floor: str
    message: str
    level: str = "info"
    source: str = "user"

class UpdateActionRequest(BaseModel):
    floor: str

@app.get("/api/update-center/status")
async def get_update_center_status():
    try:
        pipeline = AntigravityPipeline()
        return pipeline.db
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/update-center/config")
async def update_update_center_config(req: ConfigUpdateRequest):
    try:
        pipeline = AntigravityPipeline()
        if "config" not in pipeline.db:
            pipeline.db["config"] = {}
        pipeline.db["config"][req.floor] = {
            "auto_update": req.auto_update,
            "plan_mode": req.plan_mode,
            "strict_testing": req.strict_testing,
            "max_retries": req.max_retries
        }
        pipeline._save_db()
        return {"success": True, "config": pipeline.db["config"][req.floor]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/update-center/feedback")
async def add_update_center_feedback(req: FeedbackRequest):
    try:
        pipeline = AntigravityPipeline()
        entry = pipeline.add_feedback(
            floor=req.floor,
            message=req.message,
            source=req.source,
            level=req.level
        )
        return {"success": True, "entry": entry}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/update-center/trigger")
async def trigger_update(req: UpdateActionRequest):
    try:
        pipeline = AntigravityPipeline()
        res = pipeline.run_audit(req.floor)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/update-center/approve")
async def approve_update(req: UpdateActionRequest):
    try:
        pipeline = AntigravityPipeline()
        res = pipeline.approve_plan(req.floor)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/update-center/reject")
async def reject_update(req: UpdateActionRequest):
    try:
        pipeline = AntigravityPipeline()
        res = pipeline.reject_plan(req.floor)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Run on port 5001 to avoid conflict with Node (5000) and MT5 Bridge (8000)
    uvicorn.run(app, host="127.0.0.1", port=5001)
