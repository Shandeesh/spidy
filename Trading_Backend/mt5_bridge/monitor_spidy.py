import asyncio
import websockets
import sys
from datetime import datetime

async def listen():
    uri = "ws://localhost:8000/ws/logs"
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected! Listening for logs (Press Ctrl+C to stop)...")
            print("-------------------------------------------------------")
            while True:
                msg = await websocket.recv()
                print(f"LIVE: {msg}")
    except Exception as e:
        print(f"Connection Error: {e}")

if __name__ == "__main__":
    try:
        # Run for 30 seconds then exit
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        task = loop.create_task(listen())
        loop.run_until_complete(asyncio.wait_for(task, timeout=30))
    except asyncio.TimeoutError:
        print("\n--- Monitoring Timeout (30s complete) ---")
    except KeyboardInterrupt:
        print("\n--- Stopped by User ---")
