import requests
import json
import os
import sys

class LocalBrain:
    def __init__(self, model_name="gemma2:2b", host="http://localhost:11434"):
        """
        Initializes the Local Brain using Ollama.
        :param model_name: The model to use (default: gemma2:2b).
        :param host: The Ollama API host (default: localhost:11434).
        """
        self.model_name = model_name
        self.host = host
        self.is_available = self._check_availability()

    def _check_availability(self):
        """Checks if the local Ollama instance is running."""
        try:
            response = requests.get(f"{self.host}/api/tags", timeout=2)
            if response.status_code == 200:
                sys.stderr.write(f"[OK] Local Brain (Ollama) is ONLINE. Model: {self.model_name}\n")
                return True
        except requests.exceptions.ConnectionError:
            sys.stderr.write("[WARN] Local Brain (Ollama) is OFFLINE.\n")
        except Exception as e:
            sys.stderr.write(f"[WARN] Local Brain check failed: {e}\n")
        return False

    def generate_content(self, prompt):
        """
        Generates content using the local model.
        Returns an object causing to mimic the Gemini response object structure for compatibility.
        """
        if not self.is_available:
             # Try one last re-check in case it just started
            self.is_available = self._check_availability()
            if not self.is_available:
                raise ConnectionError("Local Ollama instance is not running.")

        url = f"{self.host}/api/generate"
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False
        }

        try:
            response = requests.post(url, json=payload, timeout=120)
            response.raise_for_status()
            data = response.json()
            return MockGeminiResponse(data.get("response", ""))
        except Exception as e:
            raise RuntimeError(f"Local generation failed: {e}")

class MockGeminiResponse:
    """Helper class to mimic Gemini's response object."""
    def __init__(self, text):
        self.text = text

if __name__ == "__main__":
    # Test
    brain = LocalBrain()
    if brain.is_available:
        try:
            res = brain.generate_content("Say hello from local AI!")
            print(res.text)
        except Exception as e:
            print(e)
