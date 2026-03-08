import datetime

class EconomicCalendar:
    def __init__(self):
        # In a real app, this would fetch from an API (e.g., ForexFactory, Investing.com, or a paid data provider)
        # For now, we simulate a schedule or allow manual injection.
        self.events = [
            # Example Format:
            # {"time": "14:30", "currency": "USD", "impact": "HIGH", "name": "Non-Farm Employment Change"},
            # {"time": "15:00", "currency": "USD", "impact": "MEDIUM", "name": "ISM Services PMI"}
        ]
        
    def add_manual_event(self, time_str, currency, impact="HIGH"):
        """Add a test event. Format HH:MM (24h)"""
        self.events.append({
            "time": time_str,
            "currency": currency,
            "impact": impact,
            "name": "Manual Event"
        })

    def is_event_nearby(self, symbol, minutes_before=2, minutes_after=2):
        """
        Checks if a High Impact event matches the symbol's currencies 
        within the time window.
        """
        now = datetime.datetime.now()
        current_time_str = now.strftime("%H:%M")
        
        # Parse Symbol (e.g., EURUSD -> EUR, USD)
        # Crypto: BTCUSD -> BTC, USD
        base = symbol[:3]
        quote = symbol[3:]
        
        for event in self.events:
            if event["impact"] != "HIGH":
                continue
            
            # Check Currency Match
            if event["currency"] not in [base, quote, "USD"]: # USD usually affects everything
                continue
                
            # Time Delta Check
            event_dt = datetime.datetime.strptime(event["time"], "%H:%M").replace(
                year=now.year, month=now.month, day=now.day
            )
            
            # Handle crossing midnight (kept simple for intra-day)
            
            diff = (event_dt - now).total_seconds() / 60
            
            # Event is in future (diff > 0) and within minutes_before
            if 0 < diff <= minutes_before:
                return True, f"Upcoming: {event['name']} ({event['currency']}) in {int(diff)}m"
                
            # Event passed recently (diff < 0) and within minutes_after (Volatility Wake)
            if -minutes_after <= diff <= 0:
                pass # Usually we trade the breakout here, but for safety we might just signal "VOLATILE"
                # For now, let's just warn
                return True, f"During/After: {event['name']} ({event['currency']})"
                
        return False, None

# Global Instance
calendar = EconomicCalendar()
