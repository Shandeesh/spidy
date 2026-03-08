import requests
import json
from datetime import datetime

try:
    print(f"Checking Status at {datetime.now()}...")
    response = requests.get("http://localhost:8000/status", timeout=5)
    data = response.json()
    print("--- RAW JSON RESPONSE ---")
    print(json.dumps(data, indent=2))
    print("-------------------------")
    
    if data.get("market_status") == "CLOSED_WEEKEND":
        print("✅ Backend reports CLOSED_WEEKEND (Correct)")
    else:
        print(f"❌ Backend reports {data.get('market_status')} (INCORRECT for Saturday)")
        
except Exception as e:
    print(f"Connection Failed: {e}")
