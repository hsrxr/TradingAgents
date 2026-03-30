"""
Quick demonstration of real-time progress tracking.
Shows agent prompts, outputs, and execution progress in real-time.
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
from tradingagents.graph.progress_tracker import ProgressTracker

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

print("\n" + "=" * 80)
print("TRADING AGENTS - REAL-TIME PROGRESS TRACKING DEMO")
print("=" * 80)
print("""
This demo shows real-time visibility into agent execution including:

  📝 PROMPTS: The input prompts sent to each analyst
  📤 RESPONSES: The outputs returned by each analyst  
  ⏱️  TIMINGS: How long each analysis takes
  📊 SUMMARY: Performance metrics and bottleneck identification

Configuration: 2 analysts (market, news) running in serial mode for clarity
""")
print("=" * 80 + "\n")

# Create config with progress tracking enabled
config = DEFAULT_CONFIG.copy()
config["llm_provider"] = "deepseek"
config["backend_url"] = "https://api.deepseek.com/v1"
config["deep_think_llm"] = "deepseek-reasoner"
config["quick_think_llm"] = "deepseek-chat"
config["max_debate_rounds"] = 1
config["llm_timeout_seconds"] = 180.0
config["llm_max_retries"] = 3
config["graph_invoke_retries"] = 2

# CRITICAL: Enable progress tracking
config["enable_progress_tracking"] = True
config["enable_colored_output"] = True

config["data_vendors"] = {
    "core_stock_apis": "alpha_vantage",
    "technical_indicators": "alpha_vantage",
    "fundamental_data": "alpha_vantage",
    "news_data": "alpha_vantage",
}

print("=" * 80)
print("SERIAL MODE - Real-time Progress Display")
print("=" * 80)
print("\nInitializing TradingAgentsGraph with progress tracking...\n")

try:
    ta = TradingAgentsGraph(
        debug=False,
        selected_analysts=['market', 'news'],
        config=config,
        parallel_mode=False
    )
    
    print("\n" + "-" * 80)
    print("Starting analysis for WETH/USDC on 2026-03-28")
    print("-" * 80 + "\n")
    
    start_time = time.time()
    
    # Run the analysis - progress will be shown in real-time during execution
    final_state, decision = ta.propagate("WETH/USDC", "2026-03-28")
    
    total_time = time.time() - start_time
    
    print("\n" + "=" * 80)
    print("FINAL DECISION")
    print("=" * 80)
    print(f"\nTrade Decision: {decision}\n")
    
    print("=" * 80)
    print(f"Total Execution Time: {total_time:.2f} seconds")
    print("=" * 80)
    
    # Display LLM call history
    llm_calls = ta.progress_tracker.get_llm_calls_json()
    if llm_calls:
        print(f"\n📋 LLM Call History ({len(llm_calls)} total calls):")
        print("-" * 80)
        for i, call in enumerate(llm_calls, 1):
            print(f"\n{i}. Analyst: {call['analyst']}")
            print(f"   Timestamp: {call['timestamp']}")
            print(f"   Duration: {call['duration']:.2f}s")
            if call['prompt']:
                prompt_preview = call['prompt'][:100].replace('\n', ' ') + "..."
                print(f"   Prompt: {prompt_preview}")
            if call['response']:
                response_preview = call['response'][:100].replace('\n', ' ') + "..."
                print(f"   Response: {response_preview}")

except KeyboardInterrupt:
    print("\n\n⚠️  Analysis interrupted by user")
except Exception as e:
    print(f"\n\n❌ Error during analysis: {str(e)}")
    print("\nTroubleshooting tips:")
    print("  1. Check your API keys in .env file")
    print("  2. Verify network connectivity")
    print("  3. Check that the trading date (2026-03-28) has valid market data")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("Demo complete! Progress tracking shows all agent activity in real-time.")
print("=" * 80 + "\n")
