
try:
    from google import genai
    print("SUCCESS: google-genai imported")
except ImportError as e:
    print(f"FAILURE: google-genai - {e}")

try:
    import torch
    print("SUCCESS: torch imported")
except ImportError as e:
    print(f"FAILURE: torch - {e}")

try:
    import diffusers
    print("SUCCESS: diffusers imported")
except ImportError as e:
    print(f"FAILURE: diffusers - {e}")
