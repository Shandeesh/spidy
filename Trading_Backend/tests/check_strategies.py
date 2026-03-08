
import sys
import os
import contextlib

# Suppress stderr to avoid TF noise
@contextlib.contextmanager
def suppress_stderr():
    with open(os.devnull, "w") as devnull:
        old_stderr = sys.stderr
        sys.stderr = devnull
        try:
            yield
        finally:
            sys.stderr = old_stderr

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "mt5_bridge"))

print("DEBUG: Starting Import...", flush=True)
try:
    with suppress_stderr():
        from strategy_manager import StrategyManager
    print("DEBUG: Import Successful", flush=True)
except Exception as e:
    print(f"DEBUG: Import Failed: {e}", flush=True)
    sys.exit(1)

print("DEBUG: Initializing Manager...", flush=True)
try:
    manager = StrategyManager()
    print(f"DEBUG: Manager Initialized. Strategies: {len(manager.strategies)}", flush=True)
    for s in manager.strategies:
        print(f" - {s.get_name()}", flush=True)
except Exception as e:
    print(f"DEBUG: Manager Init Failed: {e}", flush=True)
