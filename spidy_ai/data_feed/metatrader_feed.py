import MetaTrader5 as mt5
import pandas as pd
import logging
from datetime import datetime
import pytz

# Setup logger
logger = logging.getLogger(__name__)

class MetaTraderFeed:
    def __init__(self, login=None, password=None, server=None, path=None):
        self.login = login
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

    def get_historical_data(self, symbol, timeframe, num_candles):
        """
        Fetch historical OHLCV data for a given symbol.
        
        :param symbol: e.g., "EURUSD"
        :param timeframe: MT5 timeframe constant, e.g., mt5.TIMEFRAME_M1
        :param num_candles: Number of candles to fetch
        :return: DataFrame with OHLCV data or None if failed
        """
        if not self.connected:
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
        
        # Rename columns to match standard format if necessary, MT5 returns: time, open, high, low, close, tick_volume, spread, real_volume
        # We generally keep them or rename as needed.
        
        return df

    def get_market_info(self, symbol):
        """
        Get current market info (bid, ask, point, etc.)
        """
        if not self.connected:
            if not self.connect():
                return None
                
        info = mt5.symbol_info(symbol)
        if info is None:
            logger.error(f"Failed to get symbol info for {symbol}")
            return None
            
        return info._asdict()
