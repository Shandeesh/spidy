import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys
import os

# Ensure we can import SpidyBrain
sys.path.append(os.path.dirname(__file__))
from spidy_brain import SpidyBrain

app = FastAPI(title="Spidy AI Brain Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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

if __name__ == "__main__":
    # Run on port 5001 to avoid conflict with Node (5000) and MT5 Bridge (8000)
    uvicorn.run(app, host="127.0.0.1", port=5001)
