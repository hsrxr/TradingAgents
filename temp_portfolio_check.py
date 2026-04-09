#!/usr/bin/env python3
from tradingagents.portfolio_manager import PortfolioManager

pm = PortfolioManager('./trade_memory/portfolio.db')
portfolio = pm.load_latest_portfolio()

print('=== Current Portfolio_Balance Dict ===')
print(f"Cash USD: {portfolio.get('cash_usd', 0)}")
print(f"Position USD (total): {portfolio.get('position_usd', 0)}")
print(f"Unrealized PnL: {portfolio.get('unrealized_pnl', 0)}")
print(f"Realized PnL: {portfolio.get('realized_pnl', 0)}")
print(f"Positions Detail: {portfolio.get('positions', {})}")
print(f"Timestamp: {portfolio.get('timestamp', '')}")
print()

cash_usd = portfolio.get('cash_usd', 10000.0)
position_usd = portfolio.get('position_usd', 0.0)
unrealized_pnl = portfolio.get('unrealized_pnl', 0.0)
realized_pnl = portfolio.get('realized_pnl', 0.0)
initial_capital = pm.get_initial_capital()
total_assets = cash_usd + position_usd + unrealized_pnl

drawdown_pct = ((total_assets - initial_capital) / initial_capital * 100) if initial_capital > 0 else 0
# Use total_assets for risk basis when cash is depleted but positions exist
risk_basis = total_assets if (cash_usd < 0.01 and position_usd > 0.01) else cash_usd
position_utilization = (position_usd / (risk_basis * 0.40) * 100) if risk_basis > 0 else 0
position_limit = risk_basis * 0.40
order_limit = risk_basis * 0.10
remaining_pos_cap = max(0, position_limit - position_usd)

print('=== Global Portfolio Context (text to LLM) ===')
print(f'Total Assets: ${total_assets:.2f}')
print(f'Cash Balance: ${cash_usd:.2f}')
print(f'Open Position Value: ${position_usd:.2f}')
print(f'Unrealized PnL: ${unrealized_pnl:+.2f} ({drawdown_pct:+.2f}% from baseline)')
print(f'Realized PnL (cumulative): ${realized_pnl:+.2f}')
print()
print('=== RISK CONSTRAINTS ===')
print(f'Maximum single order: ${order_limit:.2f} (10% of cash)')
print(f'Maximum total position: ${position_limit:.2f} (40% of cash)')
print(f'Current position utilization: {position_utilization:.1f}%')
print(f'Remaining position capacity: ${remaining_pos_cap:.2f}')
