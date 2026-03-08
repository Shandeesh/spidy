import requests
import time

BASE_URL = "http://localhost:8000"

def test_auto_secure():
    print("--- Testing Auto-Secure Profit ---")
    
    # 1. Update Settings
    print("\n[Enabling Auto-Secure check...]")
    payload = {"enabled": True, "threshold": 15.5}
    try:
        resp = requests.post(f"{BASE_URL}/settings/auto_secure", json=payload)
        print(f"Update Response: {resp.json()}")
    except Exception as e:
        print(f"Failed: {e}")
        return

    # 2. Verify Status
    try:
        resp = requests.get(f"{BASE_URL}/status")
        data = resp.json()
        risk = data.get('risk_settings', {})
        auto_sec = risk.get('auto_secure', {})
        
        if auto_sec.get('enabled') == True and auto_sec.get('threshold') == 15.5:
             print("SUCCESS: Settings updated correctly.")
        else:
             print(f"FAILURE: Settings mismatch: {auto_sec}")
    except Exception as e:
        print(f"Status Check Failed: {e}")

    # 3. Reset
    requests.post(f"{BASE_URL}/settings/auto_secure", json={"enabled": False})
    print("\n--- Test Complete ---")

if __name__ == "__main__":
    test_auto_secure()
