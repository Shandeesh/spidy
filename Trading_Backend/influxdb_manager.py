"""
InfluxDB Time-Series Database Integration
Stores trading metrics, indicators, and performance data
"""

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
import os
from datetime import datetime
import threading
from queue import Queue
import time

class InfluxDBManager:
    """Manages InfluxDB connection and writes for trading metrics."""
    
    def __init__(self, url="http://localhost:8086", token=None, org="spidy", bucket="trading_metrics"):
        """
        Initialize InfluxDB connection.
        
        Args:
            url: InfluxDB server URL
            token: Authentication token (auto-generated if None)
            org: Organization name
            bucket: Bucket (database) name
        """
        self.url = url
        self.org = org
        self.bucket = bucket
        
        # Use token from environment or default
        self.token = token or os.getenv("INFLUXDB_TOKEN", "my-super-secret-admin-token")
        
        self.client = None
        self.write_api = None
        self.query_api = None
        self.connected = False
        
        # Write queue for async batching
        self.write_queue = Queue(maxsize=1000)
        self.writer_thread = None
        self.running = False
        
    def connect(self):
        """Establish connection to InfluxDB."""
        try:
            self.client = InfluxDBClient(url=self.url, token=self.token, org=self.org)
            
            # Test connection
            health = self.client.health()
            if health.status == "pass":
                print(f"✅ InfluxDB Connected: {self.url}")
                self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
                self.query_api = self.client.query_api()
                self.connected = True
                
                # Start background writer
                self.running = True
                self.writer_thread = threading.Thread(target=self._batch_writer, daemon=True)
                self.writer_thread.start()
                
                return True
            else:
                print(f"❌ InfluxDB Health Check Failed: {health.message}")
                return False
                
        except Exception as e:
            print(f"❌ InfluxDB Connection Failed: {e}")
            print("   Make sure InfluxDB is running: docker run -p 8086:8086 influxdb:2.7")
            return False
            
    def disconnect(self):
        """Close InfluxDB connection."""
        self.running = False
        if self.writer_thread:
            self.writer_thread.join(timeout=2)
        if self.client:
            self.client.close()
        print("InfluxDB Disconnected")
        
    def _batch_writer(self):
        """Background thread that batches writes."""
        batch = []
        last_flush = time.time()
        
        while self.running:
            try:
                # Collect points for up to 1 second or 100 points
                while len(batch) < 100 and (time.time() - last_flush) < 1.0:
                    try:
                        point = self.write_queue.get(timeout=0.1)
                        batch.append(point)
                    except:
                        break
                        
                # Write batch if we have data
                if batch and self.connected:
                    try:
                        self.write_api.write(bucket=self.bucket, org=self.org, record=batch)
                        batch = []
                        last_flush = time.time()
                    except Exception as e:
                        print(f"InfluxDB Write Error: {e}")
                        batch = []  # Discard failed batch
                        
            except Exception as e:
                print(f"Batch Writer Error: {e}")
                
    def write_trade(self, ticket, symbol, trade_type, volume, entry_price, 
                   exit_price=None, profit=None, strategy="Manual", sentiment="NEUTRAL"):
        """
        Write trade data to InfluxDB.
        
        Measurement: trades
        Tags: symbol, strategy, type (BUY/SELL), sentiment
        Fields: entry_price, exit_price, profit, volume
        """
        if not self.connected:
            return
            
        point = Point("trades") \
            .tag("symbol", symbol) \
            .tag("strategy", strategy) \
            .tag("type", trade_type) \
            .tag("sentiment", sentiment) \
            .field("ticket", ticket) \
            .field("entry_price", float(entry_price)) \
            .field("volume", float(volume))
            
        if exit_price is not None:
            point = point.field("exit_price", float(exit_price))
        if profit is not None:
            point = point.field("profit", float(profit))
            
        point = point.time(datetime.utcnow(), WritePrecision.NS)
        
        try:
            self.write_queue.put_nowait(point)
        except:
            pass  # Queue full, skip
            
    def write_indicator(self, symbol, timeframe, rsi=None, ema=None, atr=None, 
                       adx=None, vwap=None, bb_upper=None, bb_lower=None):
        """
        Write technical indicator data.
        
        Measurement: indicators
        Tags: symbol, timeframe
        Fields: rsi, ema, atr, adx, vwap, bb_upper, bb_lower
        """
        if not self.connected:
            return
            
        point = Point("indicators") \
            .tag("symbol", symbol) \
            .tag("timeframe", timeframe)
            
        if rsi is not None:
            point = point.field("rsi", float(rsi))
        if ema is not None:
            point = point.field("ema", float(ema))
        if atr is not None:
            point = point.field("atr", float(atr))
        if adx is not None:
            point = point.field("adx", float(adx))
        if vwap is not None:
            point = point.field("vwap", float(vwap))
        if bb_upper is not None:
            point = point.field("bb_upper", float(bb_upper))
        if bb_lower is not None:
            point = point.field("bb_lower", float(bb_lower))
            
        point = point.time(datetime.utcnow(), WritePrecision.NS)
        
        try:
            self.write_queue.put_nowait(point)
        except:
            pass
            
    def write_performance(self, equity, balance, profit, daily_pnl=None, 
                         positions_count=0, win_rate=None):
        """
        Write account performance metrics.
        
        Measurement: performance
        Fields: equity, balance, profit, daily_pnl, positions_count, win_rate
        """
        if not self.connected:
            return
            
        point = Point("performance") \
            .field("equity", float(equity)) \
            .field("balance", float(balance)) \
            .field("profit", float(profit)) \
            .field("positions_count", int(positions_count))
            
        if daily_pnl is not None:
            point = point.field("daily_pnl", float(daily_pnl))
        if win_rate is not None:
            point = point.field("win_rate", float(win_rate))
            
        point = point.time(datetime.utcnow(), WritePrecision.NS)
        
        try:
            self.write_queue.put_nowait(point)
        except:
            pass
            
    def query_recent_trades(self, limit=50):
        """Query recent trades from last 24 hours."""
        if not self.connected:
            return []
            
        query = f'''
        from(bucket: "{self.bucket}")
            |> range(start: -24h)
            |> filter(fn: (r) => r._measurement == "trades")
            |> limit(n: {limit})
        '''
        
        try:
            tables = self.query_api.query(query, org=self.org)
            results = []
            for table in tables:
                for record in table.records:
                    results.append({
                        'time': record.get_time(),
                        'symbol': record.values.get('symbol'),
                        'type': record.values.get('type'),
                        'strategy': record.values.get('strategy'),
                        'profit': record.values.get('profit'),
                        'entry_price': record.values.get('entry_price'),
                        'exit_price': record.values.get('exit_price')
                    })
            return results
        except Exception as e:
            print(f"Query Error: {e}")
            return []
            
    def query_equity_history(self, hours=24):
        """Get equity history for charting."""
        if not self.connected:
            return []
            
        query = f'''
        from(bucket: "{self.bucket}")
            |> range(start: -{hours}h)
            |> filter(fn: (r) => r._measurement == "performance" and r._field == "equity")
            |> aggregateWindow(every: 1m, fn: last)
        '''
        
        try:
            tables = self.query_api.query(query, org=self.org)
            results = []
            for table in tables:
                for record in table.records:
                    results.append({
                        'time': record.get_time().isoformat(),
                        'equity': record.get_value()
                    })
            return results
        except Exception as e:
            print(f"Query Error: {e}")
            return []


# Global instance
influx_db = None

def init_influxdb(url="http://localhost:8086"):
    """Initialize global InfluxDB instance."""
    global influx_db
    influx_db = InfluxDBManager(url=url)
    return influx_db.connect()


if __name__ == "__main__":
    # Test connection
    print("Testing InfluxDB Connection...")
    if init_influxdb():
        print("✅ InfluxDB Ready")
        
        # Test write
        influx_db.write_trade(
            ticket=12345,
            symbol="EURUSD",
            trade_type="BUY",
            volume=0.1,
            entry_price=1.0500,
            exit_price=1.0520,
            profit=20.0,
            strategy="TestStrategy"
        )
        
        influx_db.write_performance(
            equity=10500.0,
            balance=10400.0,
            profit=100.0,
            daily_pnl=50.0,
            positions_count=2
        )
        
        print("✅ Test data written")
        
        time.sleep(2)  # Wait for batch write
        
        # Test query
        trades = influx_db.query_recent_trades(limit=10)
        print(f"✅ Queried {len(trades)} trades")
        
        influx_db.disconnect()
    else:
        print("❌ InfluxDB Connection Failed")
        print("\nTo start InfluxDB:")
        print("docker run -d -p 8086:8086 influxdb:2.7")
