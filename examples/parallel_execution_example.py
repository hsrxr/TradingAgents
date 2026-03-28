"""
Example: Using TradingAgentsGraph with Parallel Execution
Demonstrates how to enable and use the parallel execution mode with real-time progress tracking.
"""

import os
import sys
import time
import logging

# Add project root to path for proper module importing
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.progress_tracker import setup_progress_tracking

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging for better visibility
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create a custom config with progress tracking enabled
config = DEFAULT_CONFIG.copy()
config["llm_provider"] = "deepseek"  # Switch to DeepSeek provider
config["backend_url"] = "https://api.deepseek.com/v1" 
config["deep_think_llm"] = "deepseek-reasoner"  
config["quick_think_llm"] = "deepseek-chat"  
config["max_debate_rounds"] = 1  # Limit debate rounds for faster execution
config["llm_timeout_seconds"] = 180.0
config["llm_max_retries"] = 5
config["graph_invoke_retries"] = 4
config["graph_invoke_backoff_seconds"] = 2.0

# Enable progress tracking
config["enable_progress_tracking"] = True
config["enable_colored_output"] = True

# Configure data vendors
config["data_vendors"] = {
    "core_stock_apis": "alpha_vantage",
    "technical_indicators": "alpha_vantage",
    "fundamental_data": "alpha_vantage",
    "news_data": "alpha_vantage",
}

print("\n" + "=" * 80)
print("REAL-TIME PROGRESS TRACKING - TRADING AGENTS")
print("=" * 80)
print("\nThis demo shows real-time progress of agent execution with:")
print("  ✓ Agent prompts and responses")
print("  ✓ Execution progress for each analyst")
print("  ✓ Performance metrics and timings")
print("\n" + "=" * 80 + "\n")

# ============ SERIAL EXECUTION (Original) ============
print("=" * 80)
print("SERIAL EXECUTION MODE (Original Architecture)")
print("=" * 80)
print("\nRunning with analysts: market, news")
print("-" * 80)

start_time = time.time()
ta_serial = TradingAgentsGraph(
    debug=False,
    selected_analysts=['market', "news"],
    config=config,
    parallel_mode=False  # Serial execution
)

print("\n📊 Starting serial analysis...\n")
final_state_serial, decision_serial = ta_serial.propagate("WETH/USDC", "2026-03-28")
serial_time = time.time() - start_time

print(f"\n{'=' * 80}")
print(f"✓ Serial Execution completed in {serial_time:.2f} seconds")
print(f"{'=' * 80}")
print(f"Decision: {decision_serial}\n")

# ============ PARALLEL EXECUTION (Optimized) ============
print("\n" + "=" * 80)
print("PARALLEL EXECUTION MODE (Optimized Architecture)")
print("=" * 80)
print("\nRunning with analysts: market, social, news, fundamentals")
print("-" * 80)

start_time = time.time()
ta_parallel = TradingAgentsGraph(
    debug=False,
    selected_analysts=["market", "social", "news", "fundamentals"],  # Multiple analysts
    config=config,
    parallel_mode=True  # Enable parallel execution
)

print("\n📊 Starting parallel analysis...\n")
final_state_parallel, decision_parallel = ta_parallel.propagate("WETH/USDC", "2026-03-28")
parallel_time = time.time() - start_time

print(f"\n{'=' * 80}")
print(f"✓ Parallel Execution completed in {parallel_time:.2f} seconds")
print(f"{'=' * 80}")
print(f"Decision: {decision_parallel}\n")

# ============ PERFORMANCE COMPARISON ============
print("\n" + "=" * 80)
print("PERFORMANCE COMPARISON")
print("=" * 80)
print(f"\nSerial Mode (2 analysts):     {serial_time:8.2f}s")
print(f"Parallel Mode (4 analysts):   {parallel_time:8.2f}s")

if serial_time > 0:
    speedup = serial_time / parallel_time
    print(f"\nSpeedup: {speedup:.2f}x")
    improvement = ((serial_time - parallel_time) / serial_time) * 100
    print(f"Improvement: {improvement:.1f}%")

# Visualize the difference
print("\nExecution Timeline Comparison:")
serial_bars = int(serial_time * 10)
parallel_bars = int(parallel_time * 10)
print(f"Serial:   [{'-' * min(serial_bars, 60)}]")
print(f"Parallel: [{'-' * min(parallel_bars, 60)}]")

print("\n" + "=" * 80)
print("Analysis complete! Check above for detailed progress tracking.")
print("=" * 80 + "\n")

