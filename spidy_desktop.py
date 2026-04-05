import os
import sys
import threading
import time
import uvicorn
import webview
import multiprocessing

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.append(os.path.join(BASE_DIR, "Trading_Backend", "mt5_bridge"))
sys.path.append(os.path.join(BASE_DIR, "AI_Engine", "brain"))
sys.path.append(os.path.join(BASE_DIR, "AI_Engine"))
sys.path.append(os.path.join(BASE_DIR, "Trading_Backend"))
sys.path.append(BASE_DIR)

from Trading_Backend.mt5_bridge.bridge_server import app as bridge_app
from AI_Engine.brain.brain_server import app as brain_app

def run_bridge_server():
    print("[Desktop] Starting MT5 Bridge & Dashboard Server on port 8000...")
    uvicorn.run(bridge_app, host="0.0.0.0", port=8000, log_level="warning")

def run_brain_server():
    print("[Desktop] Starting AI Brain Server on port 5001...")
    uvicorn.run(brain_app, host="0.0.0.0", port=5001, log_level="warning")

def main():
    multiprocessing.freeze_support()
    print("=======================================")
    print("   Spidy Trading Intelligence V2       ")
    print("   Initializing Desktop Environment    ")
    print("=======================================")
    
    # 1. Start backend servers in background threads
    bridge_thread = threading.Thread(target=run_bridge_server, daemon=True)
    brain_thread = threading.Thread(target=run_brain_server, daemon=True)
    
    bridge_thread.start()
    brain_thread.start()
    
    # Wait for the Uvicorn servers to initialize
    print("[Desktop] Waiting for servers to initialize...")
    time.sleep(4)
    
    # 2. Launch the Desktop GUI
    # The bridge server (port 8000) now serves the Next.js static files at the root "/"
    print("[Desktop] Launching Webview UI...")
    webview.create_window(
        title='Spidy - AI Trading Intelligence', 
        url='http://localhost:8000/', 
        width=1400, 
        height=900,
        background_color='#0f172a' # Tailwind slate-900
    )
    
    # Start the event loop for the GUI (this blocks until window is closed)
    webview.start()
    
    print("[Desktop] Application closed.")
    # Exit aggressively to guarantee background threads die
    os._exit(0)

if __name__ == '__main__':
    main()
