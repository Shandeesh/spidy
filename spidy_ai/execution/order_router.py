import MetaTrader5 as mt5

class OrderRouter:
    """
    Routes orders to the appropriate execution venue (MetaTrader5 or Shoonya).
    Controlled by 'live_mode' flag.
    Handles Buy, Sell, and Close logic.
    """
    def __init__(self, broker="MT5", live_mode=False):
        self.broker = broker
        self.live_mode = live_mode
        if self.live_mode:
            print(f"⚠️ OrderRouter: LIVE MODE ENABLED for {broker}. Real money at risk.")

    def send_order(self, symbol, order_type, volume, price=None, sl=None, tp=None):
        """
        Send an Entry order (Buy/Sell).
        """
        if self.broker == "MT5":
            return self._send_mt5_entry(symbol, order_type, volume, price, sl, tp)
        return False

    def get_open_positions(self, symbol=None):
        """
        Retrieve open positions.
        """
        if self.broker == "MT5":
            return self._get_mt5_positions(symbol)
        return []

    def close_position(self, symbol, ticket=None):
        """
        Close an existing position.
        If ticket is provided, close that specific trade.
        If not, close ALL positions for the symbol.
        """
        if self.broker == "MT5":
            return self._close_mt5(symbol, ticket)
        return False

    def _send_mt5_entry(self, symbol, order_type, volume, price, sl, tp):
        """
        Internal MT5 Entry Logic.
        """
        # Mapping string order types to MT5 constants
        type_op = mt5.ORDER_TYPE_BUY if order_type == "BUY" else mt5.ORDER_TYPE_SELL
        
        # Get current price if None
        if not price:
            tick = mt5.symbol_info_tick(symbol)
            if not tick:
                print(f"❌ OrderRouter: Failed to get tick for {symbol}")
                return False
            price = tick.ask if order_type == "BUY" else tick.bid
            
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": type_op,
            "price": price,
            "sl": float(sl) if sl else 0.0,
            "tp": float(tp) if tp else 0.0,
            "deviation": 20,
            "magic": 123456,
            "comment": "Spidy AI Entry",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        if self.live_mode:
            result = mt5.order_send(request)
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                print(f"❌ MT5 Entry Failed: {result.comment} (Code: {result.retcode})")
                return False
            print(f"✅ MT5 Entry Executed: {order_type} {volume} {symbol} @ {price}")
            return True
        else:
            print(f"[MT5 SIM] Entry: {order_type} {volume} {symbol} @ {price}")
            return True

    def _close_mt5(self, symbol, ticket=None):
        """
        Internal MT5 Close Logic.
        """
        if not self.live_mode:
            print(f"[MT5 SIM] Closing Position for {symbol}")
            return True

        # Ge positions
        positions = mt5.positions_get(symbol=symbol)
        if not positions:
            print(f"OrderRouter: No positions found for {symbol} to close.")
            return False

        for pos in positions:
            # If ticket specified, only close that one
            if ticket and pos.ticket != ticket:
                continue
                
            # Close is an opposing order
            type_op = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
            price = mt5.symbol_info_tick(symbol).bid if type_op == mt5.ORDER_TYPE_SELL else mt5.symbol_info_tick(symbol).ask
            
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": pos.volume,
                "type": type_op,
                "position": pos.ticket,
                "price": price,
                "deviation": 20,
                "magic": 123456,
                "comment": "Spidy AI Close",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            result = mt5.order_send(request)
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                print(f"❌ MT5 Close Failed: {result.comment}")
            else:
                print(f"✅ MT5 Closed Ticket {pos.ticket}")
                
        return True

    def _get_mt5_positions(self, symbol=None):
        """
        Internal MT5 Position Fetcher.
        Returns list of dicts: {ticket, symbol, type, profit, price_open, price_current}
        """
        if not self.live_mode:
            # Mock position for simulation
            return [] # In sim, main.py tracks simple state, but for this feature we might want mock PnL
        
        if symbol:
            positions = mt5.positions_get(symbol=symbol)
        else:
            positions = mt5.positions_get()

        if positions:
            data = []
            for p in positions:
                data.append({
                    "ticket": p.ticket,
                    "symbol": p.symbol,
                    "type": "BUY" if p.type == mt5.ORDER_TYPE_BUY else "SELL",
                    "volume": p.volume,
                    "profit": p.profit,
                    "commission": p.commission, # Add Commission
                    "swap": p.swap,             # Add Swap
                    "price_open": p.price_open,
                    "price_current": p.price_current,
                    "comment": p.comment
                })
            return data
        return []
