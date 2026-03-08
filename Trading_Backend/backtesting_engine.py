"""
Phase 2B: Advanced Backtesting Engine
Paper Trading OrderBook for Strategy Validation
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import os

class PaperOrderBook:
    """
    Simulates a trading environment for backtesting strategies.
    Tracks balance, positions, and executes orders against historical data.
    """
    
    def __init__(self, initial_balance=10000.0, commission_per_lot=2.0):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.equity = initial_balance
        self.commission_per_lot = commission_per_lot
        
        # Positions: {symbol: {'type': 'BUY'/'SELL', 'volume': 0.01, 'entry_price': 1.0500, 'ticket': 1}}
        self.positions: Dict[str, dict] = {}
        self.next_ticket = 1000
        
        # Trade History
        self.closed_trades = []
        self.trade_log = []
        
        # Performance Metrics
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_profit = 0.0
        self.max_drawdown = 0.0
        self.peak_equity = initial_balance
        
    def execute_order(self, symbol: str, action: str, volume: float, price: float, 
                     sl: float = 0, tp: float = 0, timestamp: datetime = None):
        """
        Simulates order execution.
        action: 'BUY' or 'SELL'
        """
        if timestamp is None:
            timestamp = datetime.now()
            
        # Calculate commission
        commission = volume * self.commission_per_lot
        self.balance -= commission
        
        # Create position
        ticket = self.next_ticket
        self.next_ticket += 1
        
        position = {
            'ticket': ticket,
            'symbol': symbol,
            'type': action,
            'volume': volume,
            'entry_price': price,
            'sl': sl,
            'tp': tp,
            'open_time': timestamp,
            'commission': commission,
            'swap': 0.0,
            'profit': 0.0
        }
        
        self.positions[ticket] = position
        
        self.trade_log.append({
            'time': timestamp,
            'action': 'OPEN',
            'ticket': ticket,
            'symbol': symbol,
            'type': action,
            'volume': volume,
            'price': price
        })
        
        return ticket
        
    def close_position(self, ticket: int, close_price: float, timestamp: datetime = None):
        """Close a position and calculate P&L."""
        if ticket not in self.positions:
            return False, "Position not found"
            
        if timestamp is None:
            timestamp = datetime.now()
            
        pos = self.positions[ticket]
        
        # Calculate profit
        # For simplicity, assume base currency is USD and we're trading forex
        # Real implementation would need contract size and currency conversion
        
        point_value = 100000 * pos['volume']  # Standard lot = 100,000 units
        
        if pos['type'] == 'BUY':
            pips = close_price - pos['entry_price']
        else:  # SELL
            pips = pos['entry_price'] - close_price
            
        gross_profit = pips * point_value
        net_profit = gross_profit - pos['commission'] - pos['swap']
        
        # Update balance
        self.balance += net_profit
        self.equity = self.balance
        
        # Update metrics
        self.total_trades += 1
        self.total_profit += net_profit
        
        if net_profit > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1
            
        # Update drawdown
        if self.equity > self.peak_equity:
            self.peak_equity = self.equity
        else:
            drawdown = self.peak_equity - self.equity
            if drawdown > self.max_drawdown:
                self.max_drawdown = drawdown
                
        # Record closed trade
        closed_trade = {
            'ticket': ticket,
            'symbol': pos['symbol'],
            'type': pos['type'],
            'volume': pos['volume'],
            'entry_price': pos['entry_price'],
            'close_price': close_price,
            'open_time': pos['open_time'],
            'close_time': timestamp,
            'profit': net_profit,
            'pips': pips,
            'commission': pos['commission']
        }
        
        self.closed_trades.append(closed_trade)
        
        self.trade_log.append({
            'time': timestamp,
            'action': 'CLOSE',
            'ticket': ticket,
            'symbol': pos['symbol'],
            'price': close_price,
            'profit': net_profit
        })
        
        # Remove position
        del self.positions[ticket]
        
        return True, net_profit
        
    def update_floating_pnl(self, current_prices: Dict[str, float]):
        """Update unrealized P&L based on current market prices."""
        floating_pnl = 0.0
        
        for ticket, pos in self.positions.items():
            symbol = pos['symbol']
            if symbol not in current_prices:
                continue
                
            current_price = current_prices[symbol]
            point_value = 100000 * pos['volume']
            
            if pos['type'] == 'BUY':
                pips = current_price - pos['entry_price']
            else:
                pips = pos['entry_price'] - current_price
                
            profit = pips * point_value - pos['commission']
            pos['profit'] = profit
            floating_pnl += profit
            
        self.equity = self.balance + floating_pnl
        return floating_pnl
        
    def check_stop_loss_take_profit(self, current_prices: Dict[str, float], timestamp: datetime):
        """Check if any positions hit SL/TP and auto-close them."""
        closed_tickets = []
        
        for ticket, pos in list(self.positions.items()):
            symbol = pos['symbol']
            if symbol not in current_prices:
                continue
                
            price = current_prices[symbol]
            
            should_close = False
            close_reason = ""
            
            if pos['type'] == 'BUY':
                if pos['sl'] > 0 and price <= pos['sl']:
                    should_close = True
                    close_reason = "SL"
                elif pos['tp'] > 0 and price >= pos['tp']:
                    should_close = True
                    close_reason = "TP"
            else:  # SELL
                if pos['sl'] > 0 and price >= pos['sl']:
                    should_close = True
                    close_reason = "SL"
                elif pos['tp'] > 0 and price <= pos['tp']:
                    should_close = True
                    close_reason = "TP"
                    
            if should_close:
                self.close_position(ticket, price, timestamp)
                closed_tickets.append((ticket, close_reason))
                
        return closed_tickets
        
    def get_performance_report(self):
        """Generate comprehensive performance statistics."""
        if self.total_trades == 0:
            win_rate = 0.0
        else:
            win_rate = (self.winning_trades / self.total_trades) * 100
            
        total_return = self.equity - self.initial_balance
        return_pct = (total_return / self.initial_balance) * 100
        
        if self.max_drawdown > 0:
            recovery_factor = abs(total_return / self.max_drawdown)
        else:
            recovery_factor = 0.0
            
        report = {
            'initial_balance': self.initial_balance,
            'final_equity': self.equity,
            'total_return': total_return,
            'return_pct': return_pct,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': win_rate,
            'max_drawdown': self.max_drawdown,
            'recovery_factor': recovery_factor,
            'profit_factor': self._calculate_profit_factor()
        }
        
        return report
        
    def _calculate_profit_factor(self):
        """Profit Factor = Gross Profit / Gross Loss"""
        gross_profit = sum(t['profit'] for t in self.closed_trades if t['profit'] > 0)
        gross_loss = abs(sum(t['profit'] for t in self.closed_trades if t['profit'] < 0))
        
        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0.0
            
        return gross_profit / gross_loss
        
    def export_results(self, filename="backtest_results.json"):
        """Export results to JSON file."""
        results = {
            'performance': self.get_performance_report(),
            'trades': self.closed_trades,
            'trade_log': [
                {**entry, 'time': entry['time'].isoformat()} 
                for entry in self.trade_log
            ]
        }
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
            
        print(f"Results exported to {filename}")


class BacktestEngine:
    """
    Runs backtests using historical data and a trading strategy.
    """
    
    def __init__(self, historical_data: pd.DataFrame, strategy_func, initial_balance=10000.0):
        """
        historical_data: DataFrame with columns ['time', 'open', 'high', 'low', 'close', 'volume']
        strategy_func: Function that takes (orderbook, current_bar) and executes trades
        """
        self.data = historical_data
        self.strategy = strategy_func
        self.orderbook = PaperOrderBook(initial_balance=initial_balance)
        
    def run(self, symbol="EURUSD"):
        """Execute the backtest."""
        print(f"Starting Backtest on {len(self.data)} bars...")
        
        for idx, row in self.data.iterrows():
            timestamp = row['time'] if 'time' in row else datetime.now()
            current_prices = {symbol: row['close']}
            
            # Check SL/TP
            self.orderbook.check_stop_loss_take_profit(current_prices, timestamp)
            
            # Update floating P&L
            self.orderbook.update_floating_pnl(current_prices)
            
            # Execute strategy
            self.strategy(self.orderbook, row, symbol, timestamp)
            
        # Close all remaining positions at final price
        final_price = self.data.iloc[-1]['close']
        final_time = self.data.iloc[-1]['time'] if 'time' in self.data.columns else datetime.now()
        
        for ticket in list(self.orderbook.positions.keys()):
            self.orderbook.close_position(ticket, final_price, final_time)
            
        print("Backtest Complete!")
        return self.orderbook.get_performance_report()


# Example Strategy: Simple Moving Average Crossover
def sma_crossover_strategy(orderbook: PaperOrderBook, bar: pd.Series, symbol: str, timestamp: datetime):
    """
    Example strategy: Buy when fast SMA crosses above slow SMA, sell when crosses below.
    This is a placeholder - real implementation would need pandas rolling calculations.
    """
    # This is just a template - you'd need to calculate SMAs from historical bars
    # For demonstration purposes, we'll use a random signal
    pass


if __name__ == "__main__":
    # Example: Load historical data and run backtest
    print("Backtesting Engine Ready.")
    print("To use: Load historical CSV/MT5 data into DataFrame and pass to BacktestEngine")
    
    # Example skeleton:
    # df = pd.read_csv("EURUSD_M5.csv")
    # df['time'] = pd.to_datetime(df['time'])
    # engine = BacktestEngine(df, sma_crossover_strategy)
    # results = engine.run()
    # print(json.dumps(results, indent=2))
