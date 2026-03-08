import requests
import json

url = "http://localhost:3000/api/ask"
payload = {"query": "Hello"}

try:
    print(f"Sending POST to {url}...")
    response = requests.post(url, json=payload, timeout=30)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        print("Response:", json.dumps(response.json(), indent=2))
        print("VERIFICATION PASSED")
    else:
        print("VERIFICATION FAILED")
        print("Error:", response.text)
except Exception as e:
    print(f"Connection Error: {e}")
