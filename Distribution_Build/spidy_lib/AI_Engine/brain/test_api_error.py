import requests
import json

url = "http://localhost:5001/api/ask"
payload = {
    "query": "Hello Spidy",
    "persona": "cyberpunk"
}

try:
    print(f"Sending request to {url}...")
    response = requests.post(url, json=payload)
    print(f"Status Code: {response.status_code}")
    print("Response Body:")
    print(response.text)
except Exception as e:
    print(f"Request failed: {e}")
