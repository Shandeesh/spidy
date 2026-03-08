import sys
import os

# Ensure we can import SpidyBrain
sys.path.append(os.path.join(os.getcwd(), 'spidy', 'AI_Engine', 'brain'))

try:
    from spidy_brain import SpidyBrain
except ImportError:
    # Adjust path if running from root or elsewhere
    sys.path.append(r"c:\Users\Shandeesh R P\spidy\AI_Engine\brain")
    from spidy_brain import SpidyBrain

def debug_brain():
    print("Initializing SpidyBrain...")
    try:
        brain = SpidyBrain()
        print("SpidyBrain Initialized Successfully.")
    except Exception as e:
        print(f"CRITICAL: Failed to initialize SpidyBrain: {e}")
        return

    test_queries = [
        "Hello",
        "What is the price of EURUSD?",
        "Generate an image of a red car"
    ]

    for q in test_queries:
        print(f"\n--- Testing Query: '{q}' ---")
        try:
            decision = brain.decide_intent(q, persona="cyberpunk")
            print(f"Result: {decision}")
        except Exception as e:
            print(f"ERROR processing '{q}': {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    debug_brain()
