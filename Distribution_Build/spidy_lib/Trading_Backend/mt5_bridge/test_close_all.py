import requests
import sys

def test_close_all():
    url = "http://localhost:8000/close_all_trades"
    try:
        print(f"Sending POST to {url}...")
        resp = requests.post(url, json={"profitable_only": True}, timeout=10)
        print(f"Status Code: {resp.status_code}")
        print(f"Response: {resp.text}")
        
    except Exception as e:
        print(f"EXCEPTION: {e}")

if __name__ == "__main__":
    test_close_all()
