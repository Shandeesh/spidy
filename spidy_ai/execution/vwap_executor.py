class VWAPExecutor:
    """
    Execution algorithm that attempts to execute close to or better than VWAP.
    For Phase 1/2, this is a simplified logic gate.
    """
    
    def __init__(self, order_router):
        self.router = order_router

    def execute_carefully(self, symbol, decision, volume, current_price, current_vwap):
        """
        Execute trade if price is favorable relative to VWAP.
        
        BUY Rule: Price <= VWAP (Buying "Cheap")
        SELL Rule: Price >= VWAP (Selling "Expensive")
        """
        if decision == "BUY":
            if current_price <= current_vwap * 1.002: # Allow 0.2% tolerance
                print(f"VWAP EXEC: Buying {symbol} (Price {current_price} <= VWAP {current_vwap})")
                return self.router.send_order(symbol, "BUY", volume)
            else:
                print(f"VWAP BLOCK: Price {current_price} too high above VWAP {current_vwap}. Waiting.")
                return False

        elif decision == "SELL":
            if current_price >= current_vwap * 0.998:
                print(f"VWAP EXEC: Selling {symbol} (Price {current_price} >= VWAP {current_vwap})")
                return self.router.send_order(symbol, "SELL", volume)
            else:
                 print(f"VWAP BLOCK: Price {current_price} too low below VWAP {current_vwap}. Waiting.")
                 return False
                 
        return False
