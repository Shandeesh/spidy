import asyncio
import websockets
import json
import requests
import sys
import os

def verify_ai():
    print("\n--- Verifying AI Persona ---")
    try:
        sys.path.append(os.path.abspath("Member1_AI_Core/brain"))
        from spidy_brain import SpidyBrain
        
        brain = SpidyBrain()
        response = brain.decide_intent("Who are you?")
        details = response.get("details", "")
        
        # Sanitize for Windows Console
        safe_details = details.encode('ascii', 'replace').decode('ascii')
        print(f"AI Response: {safe_details}")
        
        if "witty" in details.lower() or "cyberpunk" in details.lower() or "spidy" in details.lower() or "🕷️" in details:
            print("[PASS] AI Persona Check Passed")
        else:
            print("[WARN] AI Persona Check Uncertain (Check output manually)")
            
    except Exception as e:
        print(f"[FAIL] AI Verification Failed: {e}")

async def verify_bridge():
    print("\n--- Verifying MT5 Bridge Logging ---")
    uri = "ws://localhost:8000/ws/logs"
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to WebSocket.")
            try:
                requests.post("http://localhost:8000/trade", json={"action": "BUY", "symbol": "TEST", "details": "Verification"})
            except:
                print("[FAIL] Failed to trigger trade")
                return

            try:
                msg = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"Log Received: {msg}")
                if "[" in msg and "]" in msg:
                    print("[PASS] Timestamp verification passed")
                else:
                    print("[FAIL] Timestamp missing in logs")
            except asyncio.TimeoutError:
                print("[FAIL] Timeout waiting for logs")
                
    except Exception as e:
        print(f"[FAIL] Bridge Connection Failed: {e}")

def check_network_status():
    print("\n--- Verifying Bridge Status API ---")
    try:
        res = requests.get("http://localhost:8000/status")
        if res.status_code == 200:
            data = res.json()
            print(f"Status API Reachable: {data}")
            if "connected" in data:
                 print("[PASS] Status Check Passed")
            else:
                 print("[FAIL] Status API missing 'connected' key")
        else:
            print(f"[FAIL] Status API returned {res.status_code}")
    except Exception as e:
         print(f"[FAIL] Status API Failed: {e}")

def check_backend_api():
    print("\n--- Verifying Backend API ---")
    try:
        # Test the ask endpoint with a simple query
        payload = {"query": "Hello"}
        res = requests.post("http://localhost:5000/api/ask", json=payload)
        
        if res.status_code == 200:
            print(f"Backend Reachable. Response: {res.json()}")
            print("[PASS] Backend API Check Passed")
        else:
             print(f"[FAIL] Backend API returned {res.status_code} - {res.text}")
    except Exception as e:
         print(f"[FAIL] Backend API Connection Failed: {e}")

if __name__ == "__main__":
    verify_ai()
    check_backend_api()
    check_network_status()
    asyncio.run(verify_bridge())
