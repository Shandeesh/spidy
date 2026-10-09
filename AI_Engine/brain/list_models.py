from google import genai
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path="../../Shared_Data/configs/.env")
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("No API Key found")
else:
    client = genai.Client(api_key=api_key)
    with open("models.txt", "w") as f:
        for model in client.models.list():
            supported_actions = getattr(model, "supported_actions", [])
            if "generateContent" in supported_actions or not supported_actions:
                f.write(f"{model.name}\n")
    print("Models written to models.txt")
