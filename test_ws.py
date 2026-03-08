import asyncio
import websockets
import requests
import time

def check_http():
    try:
        r = requests.get("http://localhost:8000/")
        print(f"HTTP GET /: {r.status_code} {r.json()}")
    except Exception as e:
        print(f"HTTP GET / Failed: {e}")

async def test_logs(uri):
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            print(f"Connected to {uri}!")
            # Wait for greeting or logs
            try:
                msg = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                print(f"Received: {msg}")
            except asyncio.TimeoutError:
                print("No message received in 2s")
    except Exception as e:
        print(f"Connection Failed to {uri}: {e}")

async def main():
    check_http()
    await test_logs("ws://localhost:8000/ws/logs")
    await test_logs("ws://localhost:8000/ws/logs/")

if __name__ == "__main__":
    asyncio.run(main())
