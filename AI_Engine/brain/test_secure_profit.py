import sys
import os
import json
from unittest.mock import MagicMock

# Mock dependencies
sys.modules['local_brain'] = MagicMock()
sys.modules['local_sd'] = MagicMock()

# Append path
sys.path.append("c:/Users/Shandeesh R P/spidy/AI_Engine/brain")
from spidy_brain import SpidyBrain

def test_secure_profit_command():
    print("Testing 'Secure Profit' Command Interpretation...")
    
    brain = SpidyBrain()
    
    # Mock _execute_trading to avoid actual HTTP call, but we want to see if it triggers
    # Actually, we can check the decision intent first
    
    # Mocking the _generate_with_retry to return a trading intent
    brain._generate_with_retry = MagicMock(return_value='{"intent": "TRADING_UPDATE", "details": "secure my profits", "action_needed": "true"}')
    
    decision = brain.decide_intent("Spidy, secure my profits")
    
    print(f"Decision: {decision}")
    
    if decision['intent'] == "TRADING_UPDATE":
        print("SUCCESS: Intent detected correctly.")
        # Now check if details string triggers the right logic in _execute_trading (we can run it manually)
        
        # We need to mock requests.post in _execute_trading to verify payload
        import requests
        requests.post = MagicMock()
        requests.post.return_value.status_code = 200
        requests.post.return_value.json.return_value = {"closed": 5}
        
        msg = brain._execute_trading("secure my profits")
        print(f"Execution Result: {msg}")
        
        args, kwargs = requests.post.call_args
        url = args[0]
        json_payload = kwargs['json']
        
        print(f"Called URL: {url}")
        print(f"Payload: {json_payload}")
        
        if "close_all_trades" in url and json_payload.get("profitable_only") == True:
            print("SUCCESS: Correct endpoint and payload triggered.")
        else:
             print("FAILURE: Wrong endpoint or payload.")

    else:
        print("FAILURE: Intent classification failed.")

if __name__ == "__main__":
    test_secure_profit_command()
