import sys
import os
import traceback

# Simulate the path setup in bridge_server.py
current_dir = r"c:\Users\Shandeesh R P\spidy\Trading_Backend\mt5_bridge"
target_dir = os.path.abspath(os.path.join(current_dir, "../../AI_Engine/internet_gathering"))
print(f"Adding to path: {target_dir}")
sys.path.append(target_dir)

try:
    from news_fetcher import NewsFetcher
    print("SUCCESS: NewsFetcher imported!")
except ImportError as e:
    print("ERROR: ImportError caught!")
    print(e)
    traceback.print_exc()
except Exception as e:
    print("ERROR: Other Exception caught!")
    print(e)
    traceback.print_exc()
