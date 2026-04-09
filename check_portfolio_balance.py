#!/usr/bin/env python3
import json
from tradingagents.portfolio_manager import PortfolioManager

pm = PortfolioManager('./trade_memory/portfolio.db')
portfolio = pm.load_latest_portfolio()

# This is what context_merger constructs
cash_usd = portfolio.get("cash_usd", 10000.0)
position_usd = portfolio.get("position_usd", 0.0)
unrealized_pnl = portfolio.get("unrealized_pnl", 0.0)
realized_pnl = portfolio.get("realized_pnl", 0.0)
positions = portfolio.get("positions", {})

portfolio_balance = {
    "cash_usd": cash_usd,
    "position_usd": position_usd,
    "positions": positions,
    "unrealized_pnl": unrealized_pnl,
    "realized_pnl": realized_pnl,
}

print("=== portfolio_balance Dict (passed to Trader) ===")
print(json.dumps(portfolio_balance, indent=2, ensure_ascii=False))
print()
print("=== breakdown ===")
print(f"cash_usd: {portfolio_balance.get('cash_usd')}")
print(f"position_usd: {portfolio_balance.get('position_usd')}")
print(f"unrealized_pnl: {portfolio_balance.get('unrealized_pnl')}")
print(f"realized_pnl: {portfolio_balance.get('realized_pnl')}")
print(f"positions (ETH holdings): {portfolio_balance.get('positions')}")
