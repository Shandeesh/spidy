import requests
import json
import time

url = "http://localhost:8000/status"

print("Waiting for server...")
time.sleep(2)

try:
    # Trigger connection first (needed for mock data init)
    requests.post("http://localhost:8000/connect")
    time.sleep(1)

    response = requests.get(url)
    data = response.json()
    print("Response received:")
    print(json.dumps(data, indent=2))
    
    if "positions" in data:
        print("VERIFICATION PASSED: 'positions' field found.")
    else:
        print("VERIFICATION FAILED: 'positions' field missing.")
except Exception as e:
    print(f"Error: {e}")
