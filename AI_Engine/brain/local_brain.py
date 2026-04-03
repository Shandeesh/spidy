"""
local_brain.py — Ollama Local AI Client (DISABLED)
Ollama has been removed from this system. This stub ensures any remaining
try/except import blocks in other modules continue to work without crashing.
"""
import sys

class MockGeminiResponse:
    """Compatibility shim for code that uses response.text"""
    def __init__(self, text=""):
        self.text = text

class LocalBrain:
    """Stub — Ollama is not installed. is_available is always False."""
    def __init__(self, model_name="disabled", host="http://localhost:11434"):
        self.model_name = model_name
        self.host = host
        self.is_available = False  # Always offline — Ollama removed
        sys.stderr.write("[INFO] LocalBrain: Ollama removed. Using Gemini AI only.\n")

    def generate_content(self, prompt):
        raise ConnectionError("Ollama is not installed on this system. Use Gemini via brain_server.py.")

if __name__ == "__main__":
    print("LocalBrain stub — Ollama removed. System uses Gemini AI for all inference.")
