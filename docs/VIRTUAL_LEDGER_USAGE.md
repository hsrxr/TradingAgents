Virtual Ledger Integration Guide
==================================

## Overview

The Virtual Ledger is a local, persistent trading account system that tracks:
- Trading account balance (initialized to $100,000 USD)
- Trade submissions to RiskRouter
- RiskRouter approval/rejection feedback
- Balance reservations and updates
- Complete audit trail of all trades

This guide explains how to use the Virtual Ledger in your trading system.

## Architecture

### Components

1. **VirtualLedger class** (`tradingagents/virtual_ledger.py`)
   - Manages account balance and trade history
   - Persists data to JSON for session recovery
   - Provides audit trail and reporting

2. **OnChainIntegrator integration** (`tradingagents/web3_layer/on_chain_integration.py`)
   - Automatically records trade submissions
   - Updates ledger based on RiskRouter feedback
   - Tracks trade metadata and execution

### Trade Lifecycle

```
1. SUBMIT TRADE (submit_decision)
   ↓
   - Balance reserved immediately
   - metadata["virtual_trade_id"] set
   - metadata["trade_intent"] saved
   
2. PENDING (RiskRouter processes)
   ↓
   
3a. APPROVED (wait_for_feedback)
    ↓
    - Trade marked as approved
    - Balance remains reserved for execution
    - metadata["approval_event"] set
    
3b. REJECTED (wait_for_feedback)
    ↓
    - Balance returned to account
    - metadata["rejection_event"] set
    - metadata["rejection_reason"] set

4. CLOSE TRADE (when execution complete)
   ↓
   - Return reserved balance
   - Record P&L if known
   - Update balance
```

## Usage

### Basic Initialization

```python
from tradingagents.virtual_ledger import create_virtual_ledger
from tradingagents.web3_layer.on_chain_integration import OnChainIntegrator

# Create ledger (or load existing)
ledger = create_virtual_ledger(ledger_path="./trade_memory/virtual_ledger.json")

# Initialize OnChainIntegrator with ledger
integrator = OnChainIntegrator(
    web3_client=client,
    agent_id=1,
    agent_wallet="0x...",
    ledger_path="./trade_memory/virtual_ledger.json"
)
```

### Submitting Trades

When you submit a trading decision:

```python
decision = {
    "pair": "WETH/USDC",
    "action": "BUY",
    "order": {"notional_usd": 5000},
    "confidence": 0.85,
    "reason": "Strong uptrend signal"
}

result = integrator.submit_decision(decision)

# Check submission result
if result.trade_submitted:
    print(f"Trade submitted: {result.trade_intent_hash}")
    print(f"Virtual ledger trade ID: {result.metadata['virtual_trade_id']}")
    print(f"Available balance: ${integrator.ledger.get_balance():.2f}")
```

### Processing Feedback

When RiskRouter responds:

```python
result = integrator.wait_for_feedback(
    intent_hash=trade_intent_hash,
    max_wait_seconds=60
)

# Check result
if result.trade_approved:
    print(f"Trade APPROVED")
    print(f"Balance reserved: ${integrator.ledger.get_balance():.2f}")
    
elif result.trade_rejected:
    print(f"Trade REJECTED: {result.rejection_reason}")
    print(f"Balance returned: ${integrator.ledger.get_balance():.2f}")
```

### Checking Account Status

```python
# Get current balance
balance = integrator.ledger.get_balance()
print(f"Available balance: ${balance:.2f}")

# Get full account summary
summary = integrator.ledger.get_account_summary()
print(f"Initial capital: ${summary['initial_capital_usd']:.2f}")
print(f"Trades submitted: {summary['total_trades_submitted']}")
print(f"Trades approved: {summary['total_trades_approved']}")
print(f"Trades rejected: {summary['total_trades_rejected']}")
print(f"Realized P&L: ${summary['realized_pnl_usd']:.2f}")

# Get full ledger data
ledger_data = integrator.ledger.get_ledger()
trades = ledger_data['trades']
account = ledger_data['account']

# Print human-readable summary
integrator.ledger.print_summary()
```

### Trade Tracking

```python
# Get specific trade
trade = integrator.ledger.get_trade_by_hash(intent_hash)
if trade:
    print(f"Trade status: {trade['status']}")
    print(f"Amount: ${trade['amount_usd']:.2f}")
    print(f"Submitted: {trade['submitted_at']}")
    if trade['status'] == 'approved':
        print(f"Approved: {trade['approved_at']}")

# Get trades by status
submitted = integrator.ledger.get_trades_by_status("submitted")
approved = integrator.ledger.get_trades_by_status("approved")
rejected = integrator.ledger.get_trades_by_status("rejected")
```

### Closing Trades

When a trade execution completes:

```python
exit_price = 1950.50
realized_pnl = None  # Or calculate if known

integrator.ledger.close_trade(
    intent_hash=intent_hash,
    exit_price=exit_price,
    realized_pnl=realized_pnl
)

# Check balance after close
print(f"Balance after close: ${integrator.ledger.get_balance():.2f}")
print(f"Total P&L: ${integrator.ledger.get_account_summary()['realized_pnl_usd']:.2f}")
```

## Data Persistence

The Virtual Ledger automatically persists to JSON:

```json
{
  "account": {
    "balance_usd": 85000.00,
    "initial_capital_usd": 100000.00,
    "realized_pnl_usd": 0.00,
    "total_trades_submitted": 3,
    "total_trades_approved": 2,
    "total_trades_rejected": 1,
    "created_at": "2026-04-09T..."
  },
  "trades": [
    {
      "id": "0xabc123_0",
      "agent_id": 1,
      "pair": "WETH/USDC",
      "action": "BUY",
      "amount_usd": 5000.00,
      "intent_hash": "0xabc123...",
      "confidence": 0.85,
      "notes": "Strong uptrend",
      "status": "approved",
      "submitted_at": "2026-04-09T...",
      "approved_at": "2026-04-09T...",
      "reserved_balance": 5000.00,
      ...
    }
  ],
  "last_saved": "2026-04-09T..."
}
```

Data loads automatically when you create a new ledger with the same path.

## Integration with Trader Module

If using the Trader class for decision-making:

```python
from tradingagents.agents.trader import Trader
from tradingagents.web3_layer.on_chain_integration import OnChainIntegrator

# Initialize both
trader = Trader(...)
integrator = OnChainIntegrator(..., ledger_path="./trade_memory/virtual_ledger.json")

# Trading loop
for market_data in data_stream:
    # Make decision
    decision = trader.decide(market_data)
    
    if decision:
        # Submit to RiskRouter with virtual ledger tracking
        result = integrator.submit_decision(decision)
        
        # Wait for feedback
        if result.trade_submitted:
            feedback = integrator.wait_for_feedback(result.trade_intent_hash)
            
            # Check balance
            balance = integrator.ledger.get_balance()
            print(f"Updated balance: ${balance:.2f}")
```

## Testing

The integration is fully tested with:

```bash
python test_virtual_ledger_integration.py
```

This runs 5 comprehensive tests:
1. **Virtual Ledger**: Basic operations and balance tracking
2. **OnChainIntegrator Integration**: Integration with web3 layer
3. **Trade Lifecycle**: Full trade submission → approval → execution flow
4. **Persistence**: Data survives session restarts
5. **Multiple Trades**: Accurate balance tracking with many concurrent trades

All tests should show `[OK] ... PASSED`.

## Configuration

### Custom Ledger Location

```python
ledger = create_virtual_ledger(
    ledger_path="/path/to/custom/ledger.json"
)
```

### Environment Variables (future)

The system can be extended to support:
```
VIRTUAL_LEDGER_PATH=/path/to/ledger.json
INITIAL_CAPITAL_USD=100000
```

## Monitoring & Alerts

To monitor account health:

```python
def check_account_health(integrator, min_balance=10000):
    """Alert if balance drops below threshold."""
    balance = integrator.ledger.get_balance()
    summary = integrator.ledger.get_account_summary()
    
    if balance < min_balance:
        print(f"WARNING: Low balance: ${balance:.2f}")
    
    # Track performance
    return_pct = (summary['realized_pnl_usd'] / 
                  summary['initial_capital_usd']) * 100
    print(f"Return: {return_pct:.2f}%")
```

## Troubleshooting

### Issue: "Ledger file not found"
**Solution**: The ledger will be created automatically on first use. Ensure the parent directory exists:
```python
from pathlib import Path
ledger_path = "./trade_memory/virtual_ledger.json"
Path(ledger_path).parent.mkdir(parents=True, exist_ok=True)
```

### Issue: "Trade not found or not approved"
**Solution**: Check trade status with:
```python
trade = integrator.ledger.get_trade_by_hash(intent_hash)
print(f"Trade status: {trade['status']}")  # submitted, approved, rejected, closed
```

### Issue: "Insufficient balance"
**Solution**: Check account summary:
```python
summary = integrator.ledger.get_account_summary()
print(f"Available: ${summary['balance_usd']:.2f}")
print(f"Pending trades: {[t for t in integrator.ledger.trades if t['status'] == 'submitted']}")
```

## API Reference

### VirtualLedger Methods

```python
# Balance & Account
get_balance() -> float                      # Current USD balance
get_account_summary() -> Dict               # Full account stats
get_ledger() -> Dict                        # Complete ledger data
print_summary() -> None                     # Human-readable summary

# Trade Operations
submit_trade(...) -> str                    # Submit and reserve
approve_trade(intent_hash) -> bool          # Mark approved
reject_trade(intent_hash, reason) -> bool   # Mark rejected, return balance
close_trade(intent_hash, exit_price) -> bool # Close and record P&L

# Query
get_trade_by_hash(intent_hash) -> Dict     # Find specific trade
get_trades_by_status(status) -> List[Dict]  # Filter by status
```

### OnChainIntegrator Integration

```python
# Submission
submit_decision(decision) -> TradeSubmissionResult

# Feedback (automatically updates ledger)
wait_for_feedback(intent_hash, max_wait_seconds) -> TradeSubmissionResult
```

## Best Practices

1. **Always check balance before critical operations**
   ```python
   if integrator.ledger.get_balance() < min_required:
       # Skip trade or reduce size
       return
   ```

2. **Log trade decisions with confidence**
   ```python
   logger.info(f"Trade: {pair} {action} @ ${amount}usd, confidence={confidence:.2%}")
   ```

3. **Monitor rejection rates**
   ```python
   summary = integrator.ledger.get_account_summary()
   rejection_rate = (summary['total_trades_rejected'] / 
                     summary['total_trades_submitted'])
   if rejection_rate > 0.3:
       logger.warning(f"High rejection rate: {rejection_rate:.0%}")
   ```

4. **Persist logs for audit**
   ```python
   # Configure logging to file
   logging.basicConfig(
       filename='trade_audit.log',
       level=logging.INFO,
       format='%(asctime)s - %(message)s'
   )
   ```

5. **Regular backups of ledger file**
   ```python
   import shutil
   shutil.copy(ledger_path, f"{ledger_path}.backup.{timestamp}")
   ```

## Future Enhancements

- [ ] Multi-asset support (BTC, ETH, altcoins)
- [ ] Portfolio-level analytics
- [ ] Risk metrics (Sharpe ratio, drawdown)
- [ ] Automated profit-taking rules
- [ ] Database backend (SQLite/PostgreSQL) for large datasets
- [ ] Real-time monitoring dashboard
- [ ] WebSocket integration for live updates
- [ ] Backtesting support

## Support

For issues or feature requests:
1. Check the troubleshooting section above
2. Run test suite: `python test_virtual_ledger_integration.py`
3. Check logs in the working directory
4. Review test cases for usage examples
