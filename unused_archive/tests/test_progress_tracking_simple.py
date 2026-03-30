"""
Quick test to verify progress tracking imports and basic functionality.
"""

import sys
import os

# Add project root to path for proper module importing
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print("Testing progress tracking imports...")

try:
    from tradingagents.graph.progress_tracker import ProgressTracker, NodeType
    print("✓ ProgressTracker imported successfully")
    
    # Create instance
    tracker = ProgressTracker(verbose=False, enable_colors=False)
    print("✓ ProgressTracker instance created")
    
    # Test basic methods
    tracker.track_node_start("test_node", {})
    print("✓ track_node_start works")
    
    tracker.track_node_end("test_node", {})
    print("✓ track_node_end works")
    
    tracker.track_llm_call("test_analyst", "test prompt", "test response", 1.5)
    print("✓ track_llm_call works")
    
    calls = tracker.get_llm_calls_json()
    print(f"✓ get_llm_calls_json works (returned {len(calls)} calls)")
    
    print("\nAll basic tests passed!")
    print("\nNode history:")
    for node in tracker.node_history:
        if "duration" in node:
            print(f"  - {node['name']}: {node['duration']:.2f}s")
    
    sys.exit(0)
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
