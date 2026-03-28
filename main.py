import os
import time
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Create a custom config
config = DEFAULT_CONFIG.copy()
config["deep_think_llm"] = "gpt-5-mini"  # Use a different model
config["quick_think_llm"] = "gpt-5-mini"  # Use a different model
config["max_debate_rounds"] = 1  # Increase debate rounds

config["llm_provider"] = "deepseek"  # Switch to DeepSeek provider
config["backend_url"] = "https://api.deepseek.com/v1" 
config["deep_think_llm"] = "deepseek-reasoner"  
config["quick_think_llm"] = "deepseek-chat"  


# Configure data vendors (default uses yfinance, no extra API keys needed)
config["data_vendors"] = {
    "core_stock_apis": "alpha_vantage",           # Options: alpha_vantage, yfinance
    "technical_indicators": "alpha_vantage",      # Options: alpha_vantage, yfinance
    "fundamental_data": "alpha_vantage",          # Options: alpha_vantage, yfinance
    "news_data": "alpha_vantage",                 # Options: alpha_vantage, yfinance
}
start_time = time.time()
# Initialize with custom config
ta = TradingAgentsGraph(debug=True, selected_analysts=["market", "news"], config=config)

# forward propagate NVDA
final_state, decision = ta.propagate("WETH/USDC", "2026-3-28")
end_time = time.time()

print(decision)
print('\n',"=" * 50,'\n')
print(f"Execution time: {end_time - start_time:.2f} seconds")
# Memorize mistakes and reflect
# ta.reflect_and_remember(1000) # parameter is the position returns
