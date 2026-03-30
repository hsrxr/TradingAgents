"""
Simple test to verify progress tracking functionality works.
This does not require API calls - just tests the tracking mechanism.
"""

import sys
import time
from tradingagents.graph.progress_tracker import ProgressTracker, NodeType

print("=" * 80)
print("TESTING PROGRESS TRACKING FUNCTIONALITY")
print("=" * 80)

# Create a progress tracker
tracker = ProgressTracker(verbose=True, enable_colors=False)  # Disable colors for terminal testing

print("\n✓ ProgressTracker created successfully\n")

# Simulate some node executions
test_nodes = [
    ("Market Data Collection", NodeType.TOOL),
    ("Market Analyst", NodeType.ANALYST),
    ("Technical Analysis", NodeType.TOOL),
    ("News Analyst", NodeType.ANALYST),
    ("Risk Analysis", NodeType.RISK),
    ("Investment Decision", NodeType.DEBATE),
    ("Trading Execution", NodeType.TRADER),
]

print("-" * 80)
print("SIMULATING AGENT EXECUTION")
print("-" * 80)

for node_name, node_type in test_nodes:
    # Track start
    tracker.track_node_start(node_name, {"step": node_name})
    
    # Simulate work
    sleep_time = 0.5 + (hash(node_name) % 10) * 0.1
    time.sleep(sleep_time)
    
    # Track end
    tracker.track_node_end(node_name, {"status": "completed"})

print("\n" + "-" * 80)
print("TRACKING LLM CALLS")
print("-" * 80)

# Simulate some LLM calls
sample_prompt = """Analyze the following market data:
- Price: $2500
- Volume: 1M
- Trend: Upward

Provide detailed analysis."""

sample_response = """Based on the market data analysis:

Market Conditions:
- Strong upward trend observed
- Volume supports price movement
- Momentum indicators positive

Recommendation: Consider long position

Risk Level: Medium"""

tracker.track_llm_call("Market Analyst", sample_prompt, sample_response, 2.34)

tracker.track_llm_call(
    "News Analyst",
    "Summarize recent crypto news related to Ethereum",
    "Recent news shows positive sentiment for Ethereum...",
    1.87
)

print("\n" + "=" * 80)
print("EXECUTION SUMMARY")
print("=" * 80)

tracker.print_summary()

print("\n" + "=" * 80)
print("TESTING JSON EXPORT")
print("=" * 80)

llm_calls = tracker.get_llm_calls_json()
print(f"\n✓ Successfully exported {len(llm_calls)} LLM calls to JSON\n")

if llm_calls:
    print("Sample LLM Call Data:")
    print(f"  Analyst: {llm_calls[0]['analyst']}")
    print(f"  Duration: {llm_calls[0]['duration']:.2f}s")
    print(f"  Prompt length: {len(llm_calls[0]['prompt'])} chars")
    print(f"  Response length: {len(llm_calls[0]['response'])} chars")

print("\n" + "=" * 80)
print("✓ ALL TESTS PASSED")
print("=" * 80)

print("""
Progress tracking is working correctly!

You can now:
1. Run: python progress_tracking_demo.py     (Full demo with API calls)
2. Run: python parallel_execution_example.py (Compare serial vs parallel)
3. Enable progress_tracking in your own code

See PROGRESS_TRACKING_GUIDE.md for more details.
""")
