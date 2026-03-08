import requests
import time

BASE_URL = "http://localhost:8000"

def test_profit_guardian():
    print("--- Testing Profit Guardian ---")
    
    # 1. Check Initial Status
    try:
        resp = requests.get(f"{BASE_URL}/status")
        data = resp.json()
        print(f"Initial Status: {data.get('risk_settings')}")
    except Exception as e:
        print(f"Failed to connect: {e}")
        return

    # 2. Trigger Tighten Stops
    print("\n[Triggering Tighten Stops...]")
    resp = requests.post(f"{BASE_URL}/tighten_stops")
    print(f"Response: {resp.json()}")

    # 3. Verify Change
    resp = requests.get(f"{BASE_URL}/status")
    data = resp.json()
    risk = data.get('risk_settings', {})
    if risk.get("mode") == "TIGHT" and risk.get("atr_multiplier") == 1.2:
        print("SUCCESS: Risk Mode updated to TIGHT.")
    else:
        print(f"FAILURE: Risk Mode not updated: {risk}")

    # 4. Reset
    print("\n[Resetting Stops...]")
    requests.post(f"{BASE_URL}/reset_stops")
    resp = requests.get(f"{BASE_URL}/status")
    risk = resp.json().get('risk_settings', {})
    if risk.get("mode") == "STANDARD":
        print("SUCCESS: Risk Mode reset to STANDARD.")
        
    print("\n--- Test Complete ---")

if __name__ == "__main__":
    test_profit_guardian()
