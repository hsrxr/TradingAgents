#!/usr/bin/env python3
"""
Example: Enable on-chain integration for TradingAgents

This script demonstrates how to configure and run the trading agent with
automatic on-chain submission of TradeIntents and Checkpoints.

Usage:
    python example_on_chain_integration.py
"""

import os
import time
import logging
from dotenv import load_dotenv

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

# Configure logging to see on-chain submission details
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)

# Load environment variables (including on-chain config)
load_dotenv()

def main():
    """Run trading agent with on-chain integration enabled."""
    
    # Check required environment variables
    required_vars = [
        "SEPOLIA_RPC_URL",
        "OPERATOR_PRIVATE_KEY",
        "AGENT_WALLET_PRIVATE_KEY",
        "AGENT_ID",
        "AGENT_WALLET",
    ]
    
    missing = [var for var in required_vars if not os.getenv(var)]
    
    if missing:
        print(f"❌ Missing environment variables: {', '.join(missing)}")
        print("\nPlease configure .env with:")
        print("  - SEPOLIA_RPC_URL")
        print("  - OPERATOR_PRIVATE_KEY")
        print("  - AGENT_WALLET_PRIVATE_KEY")
        print("  - AGENT_ID")
        print("  - AGENT_WALLET")
        print("\nExample: See .env.example_on_chain")
        return
    
    print("✅ All environment variables configured")
    
    # Create config with on-chain submission enabled
    config = DEFAULT_CONFIG.copy()
    config["enable_on_chain_submission"] = True      # Enable TradeIntent/Checkpoint submission
    config["on_chain_simulation_enabled"] = True     # Optional: simulate before submitting
    config["llm_provider"] = "openai"                # or "deepseek" if using DeepSeek
    config["deep_think_llm"] = "gpt-4-turbo"
    config["quick_think_llm"] = "gpt-4-turbo"
    
    print("\n📊 Initializing TradingAgents with on-chain integration...")
    
    # Initialize trading graph
    ta = TradingAgentsGraph(
        debug=True,
        selected_analysts=['market', 'news', 'quant'],
        config=config,
        parallel_mode=True,
    )
    
    print("✅ TradingAgents initialized")
    
    if ta.on_chain_integrator:
        print(f"✅ On-chain integration active")
        print(f"   Agent ID: {ta.on_chain_integrator.agent_id}")
        print(f"   Agent Wallet: {ta.on_chain_integrator.agent_wallet}")
    else:
        print("⚠️  On-chain integration NOT active (check .env configuration)")
        return
    
    print("\n🚀 Running trading analysis...")
    print("-" * 50)
    
    try:
        # Run a single analysis (like trigger_main.py does)
        start_time = time.time()
        final_state, decision = ta.propagate(
            pair="WETH/USDC",
            trade_date="2026-04-08 10:30:00"
        )
        elapsed = time.time() - start_time
        
        print("-" * 50)
        print(f"\n✅ Analysis completed in {elapsed:.1f}s")
        print(f"\n📋 Decision Summary:")
        print(f"   {decision}")
        
        # If on-chain submission occurred, it will be logged automatically
        # Look for messages like:
        #   "TradeIntent submitted: 0xabc123..."
        #   "Checkpoint submitted: 0xdef456..."
        
        if ta.on_chain_integrator:
            print("\n✅ Check logs above for on-chain submission results:")
            print("   - TradeIntent hash (RiskRouter)")
            print("   - Checkpoint hash (ValidationRegistry)")
        
    except Exception as e:
        print(f"\n❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
