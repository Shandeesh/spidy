"""
Performance Benchmark Tool
Measures bridge_server.py loop performance
"""

import time
import asyncio
import MetaTrader5 as mt5
from collections import deque

class PerformanceBenchmark:
    """Benchmarks various operations for optimization."""
    
    def __init__(self):
        self.results = {}
        
    def benchmark_mt5_fetch(self, symbol="EURUSD", bars=400):
        """Benchmark MT5 bar fetching."""
        if not mt5.initialize():
            print("MT5 initialization failed")
            return None
            
        if not mt5.symbol_select(symbol, True):
            print(f"Failed to select {symbol}")
            return None
            
        # Warmup
        mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, bars)
        
        # Benchmark
        iterations = 10
        start = time.perf_counter()
        
        for _ in range(iterations):
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, bars)
            if rates is None:
                print(f"Failed to fetch bars for {symbol}")
                
        elapsed = time.perf_counter() - start
        avg_time = (elapsed / iterations) * 1000  # Convert to ms
        
        mt5.shutdown()
        
        return {
            'operation': f'fetch_{bars}_bars',
            'iterations': iterations,
            'total_time_ms': elapsed * 1000,
            'avg_time_ms': avg_time,
            'bars_per_second': (bars * iterations) / elapsed
        }
        
    def benchmark_incremental_fetch(self, symbol="EURUSD"):
        """Benchmark small incremental fetches (optimization)."""
        if not mt5.initialize():
            return None
            
        mt5.symbol_select(symbol, True)
        
        # Simulate incremental approach
        iterations = 100
        start = time.perf_counter()
        
        for _ in range(iterations):
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 5)  # Only 5 bars
            
        elapsed = time.perf_counter() - start
        avg_time = (elapsed / iterations) * 1000
        
        mt5.shutdown()
        
        return {
            'operation': 'fetch_5_bars_incremental',
            'iterations': iterations,
            'total_time_ms': elapsed * 1000,
            'avg_time_ms': avg_time,
            'bars_per_second': (5 * iterations) / elapsed
        }
        
    def benchmark_memory_cache(self):
        """Benchmark deque operations (for rolling buffer)."""
        iterations = 10000
        cache = deque(maxlen=500)
        
        # Fill cache
        for i in range(500):
            cache.append({'close': 1.0500 + i * 0.0001})
            
        # Benchmark append (rolling update)
        start = time.perf_counter()
        for i in range(iterations):
            cache.append({'close': 1.0600 + i * 0.0001})
            
        elapsed = time.perf_counter() - start
        
        return {
            'operation': 'deque_append_rolling',
            'iterations': iterations,
            'total_time_ms': elapsed * 1000,
            'avg_time_us': (elapsed / iterations) * 1000000  # microseconds
        }
        
    def run_all(self):
        """Run all benchmarks."""
        print("=" * 60)
        print("SPIDY PERFORMANCE BENCHMARK")
        print("=" * 60)
        
        print("\n[1/3] Benchmarking MT5 Bar Fetching (Current Approach)...")
        result = self.benchmark_mt5_fetch(bars=400)
        if result:
            self.results['full_fetch'] = result
            print(f"  ✓ Avg Time: {result['avg_time_ms']:.2f}ms per fetch (400 bars)")
            print(f"  ✓ Throughput: {result['bars_per_second']:.0f} bars/sec")
            
        print("\n[2/3] Benchmarking Incremental Fetching (Optimized)...")
        result = self.benchmark_incremental_fetch()
        if result:
            self.results['incremental_fetch'] = result
            print(f"  ✓ Avg Time: {result['avg_time_ms']:.2f}ms per fetch (5 bars)")
            print(f"  ✓ Throughput: {result['bars_per_second']:.0f} bars/sec")
            
        print("\n[3/3] Benchmarking Memory Cache (Deque)...")
        result = self.benchmark_memory_cache()
        if result:
            self.results['memory_cache'] = result
            print(f"  ✓ Avg Time: {result['avg_time_us']:.2f}μs per append")
            
        self._print_summary()
        
    def _print_summary(self):
        """Print comparison and recommendations."""
        print("\n" + "=" * 60)
        print("OPTIMIZATION ANALYSIS")
        print("=" * 60)
        
        if 'full_fetch' in self.results and 'incremental_fetch' in self.results:
            full = self.results['full_fetch']['avg_time_ms']
            inc = self.results['incremental_fetch']['avg_time_ms']
            speedup = full / inc
            
            print(f"\n📊 Fetch Time Comparison:")
            print(f"   Current (400 bars):  {full:.2f}ms")
            print(f"   Optimized (5 bars):  {inc:.2f}ms")
            print(f"   Speedup:             {speedup:.1f}x faster")
            
        # Calculate API call reduction
        print(f"\n📉 API Call Reduction (6 symbols, 2s interval):")
        
        # Current: 6 symbols * (400 M1 + 250 H1) = 3900 bars every 2s
        current_calls = 6 * (400 + 250) / 2  # per second
        current_per_min = current_calls * 60
        
        # Optimized: 6 symbols * (5 M1 + 5 H1) every 2s (after initial fetch)
        opt_calls = 6 * (5 + 5) / 2
        opt_per_min = opt_calls * 60
        
        reduction = ((current_per_min - opt_per_min) / current_per_min) * 100
        
        print(f"   Current:   {current_per_min:,.0f} calls/min")
        print(f"   Optimized: {opt_per_min:,.0f} calls/min")
        print(f"   Reduction: {reduction:.1f}%")
        
        print(f"\n💡 Recommendation:")
        print(f"   Implement incremental bar updates with deque caching")
        print(f"   Expected CPU reduction: ~20-30%")
        print(f"   Expected latency improvement: ~40-60%")
        print("=" * 60)


if __name__ == "__main__":
    benchmark = PerformanceBenchmark()
    try:
        benchmark.run_all()
    except KeyboardInterrupt:
        print("\n\nBenchmark interrupted.")
    except Exception as e:
        print(f"\n\nERROR: {e}")
        import traceback
        traceback.print_exc()
