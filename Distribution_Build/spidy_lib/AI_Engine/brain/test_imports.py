
try:
    import google.generativeai as genai
    print("SUCCESS: google.generativeai imported")
except ImportError as e:
    print(f"FAILURE: google.generativeai - {e}")

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
