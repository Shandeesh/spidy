import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path="../../Shared_Data/configs/.env")
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("No API Key found")
else:
    genai.configure(api_key=api_key)
    with open("models.txt", "w") as f:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                f.write(f"{m.name}\n")
    print("Models written to models.txt")
