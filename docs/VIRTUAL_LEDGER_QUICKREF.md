# Virtual Ledger Quick Reference

## Setup (One-time)
```python
from tradingagents.web3_layer.on_chain_integration import OnChainIntegrator

integrator = OnChainIntegrator(
    web3_client=client,
    agent_id=1,
    agent_wallet="0x...",
    ledger_path="./trade_memory/virtual_ledger.json"  # Auto-persists
)
```

## Check Balance
```python
balance = integrator.ledger.get_balance()
print(f"${balance:.2f}")
```

## Submit Trade (auto-tracked)
```python
result = integrator.submit_decision({
    "pair": "WETH/USDC",
    "action": "BUY",
    "order": {"notional_usd": 5000},
    "confidence": 0.85,
    "reason": "..."
})

print(result.metadata["virtual_trade_id"])  # Ledger ID
```

## Process Feedback (auto-updated)
```python
result = integrator.wait_for_feedback(intent_hash)
# Balance automatically updated:
# - Approved: reserved
# - Rejected: returned
```

## Get Account Summary
```python
summary = integrator.ledger.get_account_summary()
print(f"Balance: ${summary['balance_usd']:.2f}")
print(f"Approved: {summary['total_trades_approved']}")
print(f"Rejected: {summary['total_trades_rejected']}")
print(f"P&L: ${summary['realized_pnl_usd']:.2f}")
```

## Find Trade by Hash
```python
trade = integrator.ledger.get_trade_by_hash(intent_hash)
print(trade['status'])  # submitted, approved, rejected, closed
print(f"${trade['amount_usd']:.2f}")
```

## Close Trade (update P&L)
```python
integrator.ledger.close_trade(
    intent_hash=intent_hash,
    exit_price=1950.50,
    realized_pnl=50.00  # Optional
)
```

## Print Full Report
```python
integrator.ledger.print_summary()
```

## File Location
```
./trade_memory/virtual_ledger.json  # Auto-created, persists across sessions
```

## Tests
```bash
python test_virtual_ledger_integration.py  # All 5 tests should pass
```

## Key Features
✓ Auto-persists to JSON  
✓ Integrated with OnChainIntegrator  
✓ Auto-updated on RiskRouter feedback  
✓ Full audit trail  
✓ Account summary & analytics  

## Common Patterns
```python
# Check if you can trade
if integrator.ledger.get_balance() >= 5000:
    # Submit trade

# Monitor rejections
summary = integrator.ledger.get_account_summary()
if summary['total_trades_rejected'] > 5:
    logger.warning("High rejection rate")

# List all pending trades
pending = integrator.ledger.get_trades_by_status("submitted")
for trade in pending:
    print(f"{trade['pair']}: ${trade['amount_usd']:.2f}")
```

## Data Structure
```json
{
  "account": {
    "balance_usd": 85000,
    "initial_capital_usd": 100000,
    "created_at": "2026-04-09T..."
  },
  "trades": [
    {
      "id": "0x..._0",
      "pair": "WETH/USDC",
      "action": "BUY",
      "amount_usd": 5000,
      "status": "approved",
      "submitted_at": "...",
      "approved_at": "...",
      "intent_hash": "0x..."
    }
  ]
}
```
