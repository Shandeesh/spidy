
import sys
import os
import traceback

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from spidy_brain import SpidyBrain
    print("SpidyBrain imported successfully.")
except ImportError as e:
    print(f"Failed to import SpidyBrain: {e}")
    sys.exit(1)

def test_generation():
    print("Initializing SpidyBrain...")
    brain = SpidyBrain(mode="hybrid")
    
    query = "generate a image of real girl with saree standing in river side red silk saree"
    
    print(f"Testing query: {query}")
    try:
        # We need to simulate the response from LLM that triggers GENERATE_IMAGE intent
        # But wait, decide_intent calls the LLM. If the LLM returns GENERATE_IMAGE, 
        # then it proceeds to execute it.
        
        # To strictly test the image generation part (assuming intent classification works),
        # we can manually trigger the logic or just let decide_intent run if I have API keys.
        # Since I don't know if keys are present (likely yes as user got text response), 
        # I will try running decide_intent first.
        
        decision = brain.decide_intent(query)
        print("Decision result:")
        print(decision)
        
    except Exception:
        traceback.print_exc()

if __name__ == "__main__":
    test_generation()
