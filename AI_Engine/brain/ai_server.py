from fastapi import FastAPI, UploadFile, File, Form, Body
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import sys
import os
import json

# Ensure we can import spidy_brain
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from spidy_brain import SpidyBrain

app = FastAPI()

# Enable CORS for Frontend Access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
