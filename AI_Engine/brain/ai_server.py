"""
ai_server.py — Legacy AI Server (Port 5000)

DEPRECATED: This file is kept for backward compatibility only.
The canonical production AI server is brain_server.py (Port 5001),
which has full API key auth, proper CORS, and Pydantic models.

Use brain_server.py for all new integrations.
"""
from fastapi import FastAPI, UploadFile, File, Form, Body
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import sys
import os
import json

# Ensure we can import spidy_brain
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from spidy_brain import SpidyBrain

app = FastAPI(title="Spidy AI Legacy Server (Deprecated — use brain_server.py)")

# SECURITY FIX: Restrict CORS to known local origins (was wildcard "*")
# brain_server.py is the canonical server with the same fix applied.
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5000",
    "http://127.0.0.1:5000",
    "http://localhost:5001",
    "http://127.0.0.1:5001",
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
print("Initializing Spidy Brain...")
brain = SpidyBrain()
print("Spidy Brain Ready!")

@app.get("/")
def home():
    return {"status": "Spidy AI Server Running"}

@app.post("/ask")
async def ask(query: str = Body(..., embed=True)):
    """
    Endpoint to process user queries.
    Expects JSON: {"query": "Hello"}
    """
    try:
        response = brain.decide_intent(query)
        return {"success": True, "ai_response": response}
    except Exception as e:
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5000)
