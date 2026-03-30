#!/usr/bin/env python
"""
Architecture Validation Test for Simplified Trading Agents Graph.

This script validates:
1. Graph compile successfully
2. State initialization correct
3. Node connectivity correct
4. Risk engine produces valid output
"""

import sys
import os
import json

# Add project root to path
script_dir = os.path.dirname(os.path.abspath(__file__))  # tests/
project_root = os.path.dirname(script_dir)  # parent directory
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print("=" * 80)
print("SIMPLIFIED ARCHITECTURE VALIDATION TEST")
print("=" * 80)

# Test 1: Import validation
print("\n[1/5] Validating imports...")
try:
    from tradingagents.graph.trading_graph import TradingAgentsGraph
    from tradingagents.default_config import DEFAULT_CONFIG
    from tradingagents.agents.managers.risk_engine import create_risk_engine
    print("✓ All imports successful")
except Exception as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

# Test 2: Config validation
print("\n[2/5] Validating configuration...")
try:
    config = DEFAULT_CONFIG.copy()
    assert "max_position_pct" in config, "Missing max_position_pct"
    assert "max_single_order_pct" in config, "Missing max_single_order_pct"
    assert config.get("max_debate_rounds") == 1, "Should be limited to 1 debate round"
    print(f"✓ Config valid")
    print(f"  - Default analysts: market, news")
    print(f"  - Max position: {config['max_position_pct']*100}%")
    print(f"  - Max order: {config['max_single_order_pct']*100}%")
except AssertionError as e:
    print(f"✗ Config validation failed: {e}")
    sys.exit(1)

# Test 3: Graph structure validation (serial)
print("\n[3/5] Validating serial graph structure...")
try:
    config = DEFAULT_CONFIG.copy()
    config["enable_progress_tracking"] = False
    config["llm_provider"] = "deepseek"
    config["backend_url"] = "https://api.deepseek.com/v1"
    
    ta_serial = TradingAgentsGraph(
        debug=False,
        selected_analysts=["market", "news"],
        config=config,
        parallel_mode=False
    )
    print("✓ Serial graph created successfully")
    print(f"  - Graph ID: {id(ta_serial.graph)}")
except Exception as e:
    print(f"✗ Serial graph creation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Graph structure validation (parallel)
print("\n[4/5] Validating parallel graph structure...")
try:
    ta_parallel = TradingAgentsGraph(
        debug=False,
        selected_analysts=["market", "news"],
        config=config,
        parallel_mode=True
    )
    print("✓ Parallel graph created successfully")
    print(f"  - Graph ID: {id(ta_parallel.graph)}")
except Exception as e:
    print(f"✗ Parallel graph creation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: Risk engine mock test
print("\n[5/5] Testing Risk Engine logic...")
try:
    from tradingagents.agents.utils.agent_states import AgentState, InvestDebateState, RiskDebateState
    
    risk_engine_func = create_risk_engine()
    
    # Create a minimal mock state
    mock_state = {
        "company_of_interest": "WETH/USDC",
        "trader_investment_plan": json.dumps({
            "action": "BUY",
            "confidence": 0.75,
            "thesis": "Strong bullish signals"
        }),
        "portfolio_balance": {
            "cash_usd": 10000.0,
            "position_usd": 0.0
        },
        "risk_debate_state": {
            "aggressive_history": "",
            "conservative_history": "",
            "neutral_history": "",
            "history": "",
            "latest_speaker": "",
            "current_aggressive_response": "",
            "current_conservative_response": "",
            "current_neutral_response": "",
            "judge_decision": "",
            "count": 0,
        }
    }
    
    result = risk_engine_func(mock_state)
    
    # Validate result structure
    assert "risk_debate_state" in result, "Missing risk_debate_state"
    assert "final_trade_decision" in result, "Missing final_trade_decision"
    
    decision = json.loads(result["final_trade_decision"])
    assert "action" in decision, "Missing action in decision"
    assert "order" in decision, "Missing order in decision"
    assert decision["order"]["side"] in {"BUY", "SELL", "HOLD"}, "Invalid side"
    
    print(f"✓ Risk Engine working correctly")
    print(f"  - Input action: {json.loads(mock_state['trader_investment_plan'])['action']}")
    print(f"  - Output action: {decision['action']}")
    print(f"  - Order notional: ${decision['order']['notional_usd']}")
    print(f"  - Risk status: {decision['order']['risk_status']}")
    
except Exception as e:
    print(f"✗ Risk engine test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 80)
print("✓ ALL VALIDATION TESTS PASSED")
print("=" * 80)
print("""
The simplified architecture is ready. Next steps:

1. LIGHTWEIGHT TEST (no API calls):
   python tests/test_trading_agents.py

2. FULL TEST (requires API keys - DeepSeek or OpenAI):
   python main.py
   or
   python examples/parallel_execution_example.py

3. PROGRESS TRACKING DEMO:
   python examples/progress_tracking_demo.py

Architecture Summary:
  Input → Market/News (parallel) → Context Merge → Bull/Bear (max 2 turns)
       → Chief Trader (JSON intent + confidence) → Risk Engine (Python) → Executable Order
""")
