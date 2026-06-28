import MetaTrader5 as mt5
import pandas as pd
import logging
from datetime import datetime
import pytz

# Setup logger
logger = logging.getLogger(__name__)

def _map_timeframe(tf):
    if tf is None:
        return mt5.TIMEFRAME_M5
    # If it's already an MT5 constant (e.g., TIMEFRAME_H1 is 16385)
    if isinstance(tf, int) and tf > 1440:
        return tf
    
    mapping = {
        1: mt5.TIMEFRAME_M1,
        5: mt5.TIMEFRAME_M5,
        15: mt5.TIMEFRAME_M15,
        30: mt5.TIMEFRAME_M30,
        60: mt5.TIMEFRAME_H1,
        240: mt5.TIMEFRAME_H4,
        1440: mt5.TIMEFRAME_D1,
        "M1": mt5.TIMEFRAME_M1,
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1,
        "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1,
    }
    return mapping.get(tf, mt5.TIMEFRAME_M5)

class MetaTraderFeed:
    def __init__(self, symbol=None, timeframe=None, login=None, password=None, server=None, path=None):
        # Support positional arguments if passed as MetaTraderFeed(symbol, 5)
        # in this case, symbol matches login parameter if we don't name them.
        # So we check if symbol is a number (login) vs string (symbol)
        if isinstance(symbol, int):
            self.login = symbol
            self.symbol = None
        else:
            self.symbol = symbol
            self.login = login

        # Check if timeframe is password (if instantiated as MetaTraderFeed(symbol, 5))
        if isinstance(timeframe, str) and len(timeframe) > 10:
            self.password = timeframe
            self.timeframe = None
        else:
            self.timeframe = _map_timeframe(timeframe)
            self.password = password

        self.server = server
        self.path = path
        self.connected = False

    def connect(self):
        """
        Connects to the MetaTrader 5 terminal.
        """
        init_params = {}
        if self.path:
            init_params['path'] = self.path
        
        if not mt5.initialize(**init_params):
            logger.error(f"MT5 initialization failed, error code = {mt5.last_error()}")
            return False

        if self.login and self.password and self.server:
            authorized = mt5.login(login=self.login, password=self.password, server=self.server)
            if not authorized:
                logger.error(f"MT5 login failed, error code = {mt5.last_error()}")
                mt5.shutdown()
                return False

        self.connected = True
        logger.info("Connected to MetaTrader 5")
        return True

    def disconnect(self):
        """
        Shuts down the connection to MetaTrader 5.
        """
        if self.connected:
            mt5.shutdown()
            self.connected = False
            logger.info("Disconnected from MetaTrader 5")

    def shutdown(self):
        """Alias for disconnect"""
        self.disconnect()

    def get_historical_data(self, symbol, timeframe, num_candles):
        """
        Fetch historical OHLCV data for a given symbol.
        """
        term_info = mt5.terminal_info()
        if not self.connected or term_info is None or not term_info.connected:
            self.connected = False
            if not self.connect():
                return None

        # Ensure symbol is selected in Market Watch
        selected = mt5.symbol_select(symbol, True)
        if not selected:
            logger.warning(f"Failed to select symbol {symbol}")
            return None

        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, num_candles)
        
        if rates is None or len(rates) == 0:
            logger.error(f"Failed to get rates for {symbol}")
            return None

        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df

    def get_candles(self, n=500):
        """
        Gets candles for the preset symbol and timeframe.
        Used by main.py and data_engineer.py.
        """
        symbol = self.symbol or "EURUSD"
        timeframe = self.timeframe or mt5.TIMEFRAME_M5
        return self.get_historical_data(symbol, timeframe, n)

    def get_market_info(self, symbol):
        """
        Get current market info (bid, ask, point, etc.)
        """
        term_info = mt5.terminal_info()
        if not self.connected or term_info is None or not term_info.connected:
            self.connected = False
            if not self.connect():
                return None
                
        info = mt5.symbol_info(symbol)
        if info is None:
            logger.error(f"Failed to get symbol info for {symbol}")
            return None
            
        return info._asdict()
