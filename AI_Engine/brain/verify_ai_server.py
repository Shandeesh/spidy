import requests
import time
import json

url = "http://localhost:5000/ask"
payload = {"query": "Hello from verification script"}

print("Waiting for AI Server...")
time.sleep(5) # Give server time to start

try:
    start_time = time.time()
    print(f"Sending POST to {url}...")
    response = requests.post(url, json=payload, timeout=5)
    end_time = time.time()
    
    latency = end_time - start_time
    print(f"Latency: {latency:.2f}s")
    
    if response.status_code == 200:
        print("Response received:")
        print(json.dumps(response.json(), indent=2))
        if latency < 2.0:
            print("VERIFICATION PASSED: Response was fast.")
        else:
            print("VERIFICATION WARNING: Response was slow (>2s).")
    else:
        print(f"VERIFICATION FAILED: Status {response.status_code}")
        print(response.text)
except Exception as e:
    print(f"Connection Error: {e}")
