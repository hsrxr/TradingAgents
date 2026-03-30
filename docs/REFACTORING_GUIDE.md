"""# Trading Agent Memory & State Management Refactoring

## Overview

This document describes the comprehensive refactoring of the TradingAgents memory and portfolio state system. The changes address three critical architectural gaps:

1. **Portfolio State Persistence**: Eliminates hardcoded initial state; enables multi-session learning
2. **Semantic Memory**: Replaces keyword BM25 matching with ChromaDB vector embeddings
3. **Global Context Routing**: Ensures all agents respect risk constraints through broadcast state

---

## Part 1: Portfolio State Persistence (SQLite)

### Objective
Replace the hardcoded `cash_usd=10000.0` initialization with a persistent database that:
- Survives process restarts
- Tracks historical account evolution
- Enables realistic multi-session backtesting
- Provides audit trail for all trades

### Architecture

#### Database Schema
Located in: `tradingagents/portfolio_manager.py`

**Table: `portfolio_state`**
```sql
CREATE TABLE portfolio_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    cash_usd REAL NOT NULL,
    positions TEXT NOT NULL,  -- JSON format for flexible multi-asset
    unrealized_pnl REAL NOT NULL DEFAULT 0.0,
    realized_pnl REAL NOT NULL DEFAULT 0.0,
    total_assets REAL NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**Table: `trade_history`**
```sql
CREATE TABLE trade_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    ticker TEXT NOT NULL,
    side TEXT NOT NULL,  -- 'BUY' or 'SELL'
    quantity REAL NOT NULL,
    entry_price REAL NOT NULL,
    notional_usd REAL NOT NULL,
    status TEXT DEFAULT 'open',  -- 'open' or 'closed'
    exit_price REAL,
    realized_pnl REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### PortfolioManager API

```python
from tradingagents.portfolio_manager import PortfolioManager

pm = PortfolioManager(db_path="./trade_memory/portfolio.db")

# Load current portfolio (or initialize if first run)
portfolio = pm.load_latest_portfolio()
# Returns: {cash_usd, positions, position_usd, unrealized_pnl, realized_pnl, timestamp}

# Save updated portfolio state
pm.save_portfolio_state({
    "cash_usd": 9850.0,
    "positions": {"BTC": {"notional_usd": 500}},
    "unrealized_pnl": -250.0,
    "realized_pnl": 100.0,
    "timestamp": "2026-03-30T10:00:00"
})

# Record trade execution
trade_id = pm.record_trade(
    ticker="BTC/USDC",
    side="BUY",
    quantity=0.01,
    entry_price=67500,
    notional_usd=675.0
)

# Close trade and record PnL
pm.close_trade(trade_id=1, exit_price=68000, realized_pnl=5.0)

# Retrieve historical snapshots
history = pm.get_portfolio_history(limit=100)

# Get all trades for a ticker
trades = pm.get_trade_history(ticker="BTC/USDC", status="closed")
```

### Integration Points

#### 1. **propagation.py** (START node)
Changed from hardcoded initialization to database lookup:

```python
from tradingagents.portfolio_manager import PortfolioManager

class Propagator:
    def __init__(self):
        self.portfolio_manager = PortfolioManager()
    
    def create_initial_state(self, ...):
        # Load actual portfolio instead of hardcoding
        portfolio = self.portfolio_manager.load_latest_portfolio()
        
        return {
            "portfolio_balance": {
                "cash_usd": portfolio["cash_usd"],
                "position_usd": portfolio["position_usd"],
                "positions": portfolio["positions"],
                "unrealized_pnl": portfolio["unrealized_pnl"],
                "realized_pnl": portfolio["realized_pnl"],
            },
            ...
        }
```

#### 2. **risk_engine.py** (Decision node)
Now reads from database and persists decisions:

```python
def create_risk_engine():
    portfolio_manager = PortfolioManager()
    
    def risk_engine_node(state):
        # Read from database (single source of truth)
        portfolio = portfolio_manager.load_latest_portfolio()
        cash_usd = portfolio["cash_usd"]
        
        # Apply hard rules (Kelly formula, drawdown limits, etc.)
        order = calculate_order(...)
        
        # Persist updated portfolio state
        portfolio_manager.save_portfolio_state(updated_portfolio)
        
        # Record trade for audit trail
        if order["notional_usd"] > 0:
            portfolio_manager.record_trade(...)
        
        return {"final_trade_decision": ...}
    
    return risk_engine_node
```

#### 3. **trading_graph.py** (Reflection node)
Updated to use persistent trade records:

```python
def reflect_and_remember(self, state, returns_losses):
    # Write memory (persisted via ChromaDB)
    self.trader_memory.add_situations(
        [(situation, recommendation)],
        metadata_list=[{"ticker": "BTC", "pnl_result": returns_losses}]
    )
    
    # Update portfolio with actual PnL
    self.portfolio_manager.close_trade(
        trade_id=state["last_trade_id"],
        exit_price=actual_price,
        realized_pnl=returns_losses
    )
```

---

## Part 2: Memory System Upgrade (ChromaDB + Vectors)

### Objective
Replace in-memory BM25 keyword matching with persistent semantic embeddings:
- Matches "Powell signals hawkish stance" with "Fed hints at higher rates"
- Persists across process restarts
- Supports metadata-based filtering (ticker, regime, outcome)
- No token limits or API costs

### Architecture

#### ChromaDB Setup
Located in: `tradingagents/agents/utils/memory.py`

Database structure:
```
./trade_memory/chromadb/
├── index/
├── chroma.sqlite3
└── [collection files]
```

#### VectorizedMemory API

```python
from tradingagents.agents.utils.memory import VectorizedMemory

# Initialize (persists to disk automatically)
bull_memory = VectorizedMemory(
    name="bull_researcher",
    db_path="./trade_memory/chromadb"
)

# Add situations with metadata
bull_memory.add_situations(
    situations_and_advice=[
        (
            "Bitcoin breaking above 70k with strong momentum, Fed signals rate cuts",
            "Bull case: BTC poised for breakout. Recommend LONG position."
        ),
        (
            "Negative regulatory news, whale accumulation pattern",
            "Mixed signals suggest HOLD. Wait for clearer directional bias."
        ),
    ],
    metadata_list=[
        {"ticker": "BTC", "market_regime": "bullish", "pnl_result": "win"},
        {"ticker": "BTC", "market_regime": "mixed", "pnl_result": "loss"},
    ]
)

# Semantic similarity search
matches = bull_memory.get_memories(
    current_situation="Bitcoin near all-time high with institutional buying",
    n_matches=3,
    filter_metadata={"ticker": "BTC", "pnl_result": "win"}
)

# Output:
# [
#     {
#         "situation": "Bitcoin breaking above 70k...",
#         "recommendation": "Bull case: BTC poised...",
#         "similarity_score": 0.92,
#         "metadata": {"ticker": "BTC", ...}
#     },
#     ...
# ]

# Inspect stored situations
all_situations = bull_memory.list_all_situations(limit=100)

# Get collection statistics
stats = bull_memory.get_collection_stats()
# Returns: {name, count, embedding_model, created_at}
```

### How It Works

#### 1. **Embeddings**
Uses `sentence-transformers/all-MiniLM-L6-v2` by default:
- Lightweight model (33M parameters)
- Runs locally, no API calls
- Produces 384-dimensional vectors
- Good balance between quality and speed

#### 2. **Semantic Matching**
ChromaDB computes cosine similarity between query and stored documents:
- "Fed signals higher rates" ← Similarity → "Powell speaks hawkish" (high score)
- "Fed signals higher rates" ← Similarity → "Bitcoin pumps 5%" (low score)

#### 3. **Metadata Filtering**
Hybrid search combining semantic + structured filters:
```python
# Get memories for winning trades only
matches = memory.get_memories(
    current_situation="Market conditions similar to past",
    filter_metadata={"pnl_result": "win"}
)
```

### Integration Points

#### 1. **Backward Compatibility**
`FinancialSituationMemory` is now an alias for `VectorizedMemory`:
```python
# Old code continues to work
from tradingagents.agents.utils.memory import FinancialSituationMemory
memory = FinancialSituationMemory("bull_researcher")  # ChromaDB backend
```

#### 2. **Researcher Agents** (bull_researcher.py, bear_researcher.py, trader.py)
```python
# Get past lessons at decision time
memories = self.memory.get_memories(
    current_situation=f"Market summary: {market_report}. Sentiment: {sentiment}",
    n_matches=3
)

# Inject into prompt
prompt = f"...Similar past situations and outcomes:\n"
for m in memories:
    prompt += f"- {m['recommendation']}\n"
```

#### 3. **Reflection Node** (reflection.py)
```python
def reflect_on_bull_researcher(self, ...):
    situation = f"Market context: {market_report}. Decision: {decision}. Result: {returns_losses}"
    
    recommendation = llm.generate_reflection(situation)
    
    # Persist with metadata for future retrieval
    self.bull_memory.add_situations(
        [(situation, recommendation)],
        metadata_list=[{
            "ticker": company_of_interest,
            "market_regime": estimate_regime(market_report),
            "pnl_result": "win" if float(returns_losses) > 0 else "loss"
        }]
    )
```

---

## Part 3: Global Context Routing

### Objective
Broadcast portfolio constraints to all analyst agents, preventing:
- Overexposure recommendations
- Blind risk-taking when account is low
- Excessive position concentration

### Architecture

#### State Extension
Added to `AgentState`:
```python
class AgentState(MessagesState):
    portfolio_balance: Dict[str, Any]  # Detailed: cash, positions, PnL
    
    global_portfolio_context: str  # Natural language for all agents
    # Example format:
    # """
    # Current assets: $9,500. Position: $500 (5.3% of limit).
    # Unrealized PnL: -2.1%. Drawdown from baseline: -2%.
    # Maximum order size: $1,000 (10% of cash). Remaining capacity: $1,500.
    # CONSTRAINT: If drawdown > -5%, block new BUY orders.
    # """
```

#### Context Merge Node
Located in: `tradingagents/graph/context_merger.py`

Runs after market data gathering:
```python
from tradingagents.graph.context_merger import create_context_merge_node

# Add to graph
graph.add_node("context_merge", create_context_merge_node())
graph.add_edge("market_analysis", "context_merge")
graph.add_edge("context_merge", "bull_researcher")
graph.add_edge("context_merge", "bear_researcher")
```

Function refreshes portfolio context:
```python
def create_context_merge_node():
    portfolio_manager = PortfolioManager()
    
    def context_merge_node(state):
        portfolio = portfolio_manager.load_latest_portfolio()
        
        context = f"""
        === PORTFOLIO STATE (as of {portfolio['timestamp']}) ===
        Total Assets: ${total_assets:.2f}
        Cash Balance: ${cash_usd:.2f}
        Open Position: ${position_usd:.2f} ({position_utilization:.1f}% of limit)
        
        === RISK CONSTRAINTS ===
        Maximum single order: ${order_limit:.2f}
        Maximum total position: ${position_limit:.2f}
        Current drawdown: {drawdown_pct:+.2f}%
        
        === DECISION RULES ===
        DO NOT exceed order limit
        PRIORITIZE RISK if drawdown < -5%
        BE CONSERVATIVE if position utilization > 80%
        """
        
        state["global_portfolio_context"] = context
        return state
    
    return context_merge_node
```

#### Prompt Integration
Updated analyst prompts to include context:

**bull_researcher.py:**
```python
system_prompt = f"""
You are a bullish market analyst. Generate bullish arguments for the asset.

[PORTFOLIO CONSTRAINT - RESPECT THIS]
{state['global_portfolio_context']}

DO NOT recommend positions that violate the constraints above.
If account is near drawdown limit, recommend defensive positions or HOLD.
"""
```

**trader.py:**
```python
system_prompt = f"""
You synthesize all research into a BUY/SELL/HOLD decision.

CURRENT PORTFOLIO STATE:
{state['global_portfolio_context']}

Apply these position sizing rules:
- BUY size = confidence × (available capacity)
- Never exceed {state['portfolio_balance']['cash_usd'] * 0.10:.2f}
- Reduce size if unrealized PnL is negative
"""
```

---

## Part 4: Risk Engine Hardening

### Enhanced Risk Engine Features

#### 1. **Direct Database Access**
Reads from `portfolio_state` table (single source of truth):
```python
portfolio = portfolio_manager.load_latest_portfolio()
cash = portfolio["cash_usd"]  # Not from state (prevents staleness)
```

#### 2. **Kelly Formula Position Sizing**
Replaces simple confidence scaling:
```
kelly_fraction = 2 × confidence - 1
order_size = base_size × kelly_fraction

Examples:
- Confidence 0.6 → kelly_fraction = 0.2 (20% of max)
- Confidence 0.7 → kelly_fraction = 0.4 (40% of max)
- Confidence 0.5 → kelly_fraction = 0.0 (no position)
```

#### 3. **Drawdown Protection**
Limits losses to 5% from baseline:
```python
max_drawdown = -0.05  # 5% loss limit
current_drawdown = (total_assets - initial_capital) / initial_capital

if current_drawdown < max_drawdown:
    # Block new BUY orders
    # But allow SELL orders for risk management
```

#### 4. **Standardized Order Payload**
Prepares JSON for EIP-712 signature module:
```python
order = {
    "ticker": "BTC/USDC",
    "side": "BUY",
    "order_type": "market",
    "notional_usd": 750.00,
    "quantity": None,  # Filled at execution
    "confidence": 0.72,
    "kelly_fraction": 0.44,
    "risk_status": "allowed",
    "max_position_pct": 0.20,
    "max_single_order_pct": 0.10,
}
```

#### 5. **Trade Persistence**
Records all orders for audit trail:
```python
trade_id = portfolio_manager.record_trade(
    ticker="BTC/USDC",
    side="BUY",
    quantity=0,  # Would be filled by execution engine
    entry_price=0,  # Would be filled by execution engine
    notional_usd=750.00
)
```

---

## Migration Guide

### For Existing Code

#### 1. **Update imports**
```python
# Old
from tradingagents.agents.utils.memory import FinancialSituationMemory
memory = FinancialSituationMemory("bull_researcher")

# Still works! FinancialSituationMemory now uses ChromaDB backend
# No code changes needed
```

#### 2. **Add portfolio manager to agent**
```python
# Before
portfolio = state["portfolio_balance"]
cash = portfolio["cash_usd"]

# After (in risk_engine.py)
from tradingagents.portfolio_manager import PortfolioManager
pm = PortfolioManager()
portfolio = pm.load_latest_portfolio()
cash = portfolio["cash_usd"]  # Single source of truth
```

#### 3. **Update graph setup**
```python
# Add context merge node
from tradingagents.graph.context_merger import create_context_merge_node

graph.add_node("context_merge", create_context_merge_node())

# Route market/news → context_merge → analysts
graph.add_edge("sentiment_analyst", "context_merge")
graph.add_edge("context_merge", "bull_researcher")
```

### Dependencies

New packages required:
```bash
pip install chromadb sentence-transformers
```

Add to `requirements.txt`:
```
chromadb>=0.4.0
sentence-transformers>=2.2.0
```

### Database Initialization

Automatic on first run:
```python
from tradingagents.portfolio_manager import PortfolioManager

# Creates ./trade_memory/portfolio.db with schema
pm = PortfolioManager()

# Optionally inspect
history = pm.get_portfolio_history(limit=5)
print(f"Current cash: ${history[0]['cash_usd']:.2f}")
```

---

## Validation Checklist

After refactoring deployment:

- [ ] Portfolio database initializes on first run
- [ ] START node loads portfolio instead of hardcoding
- [ ] Global context broadcasts to analysts
- [ ] Bull/Bear researchers inject context into prompts
- [ ] Risk engine reads from database
- [ ] Risk engine persists portfolio state after orders
- [ ] ChromaDB collections created for all 5 memories
- [ ] Reflect_and_remember writes to ChromaDB with metadata
- [ ] Memory retrieval uses semantic similarity (not BM25)
- [ ] Trade history table records all orders
- [ ] Portfolio history tracked over multiple runs
- [ ] Drawdown limit prevents new buys at -5%
- [ ] Kelly formula sizes orders by confidence
- [ ] Order JSON includes kelly_fraction field

---

## Performance Notes

### Storage
- SQLite: ~100KB per 100 portfolio snapshots
- ChromaDB: ~1-5MB for 1000 situations across all memories

### Retrieval Speed
- Portfolio load: <1ms (single table scan)
- Memory vector search: 5-20ms (depends on collection size)
- Context merge: <10ms total

### Training Data Impact
Mid-session improvements visible within single process:
- reflect_and_remember writes to ChromaDB
- Next decision reads from ChromaDB via semantic search
- Learning loop works for bull/bear/trader in same session

Cross-session learning:
- All memories persisted to disk
- Next process startup loads from ChromaDB
- Full training accumulation across multiple runs

---

## Future Enhancements

1. **Portfolio Optimization**
   - Multi-asset allocation (beyond single BTC/USDC pair)
   - Rebalancing scheduler
   - Correlation-based diversification

2. **Advanced Risk Management**
   - Value-at-Risk (VaR) calculations
   - Stress testing against historical scenarios
   - Dynamic position limits based on volatility

3. **Memory Compression**
   - Automatic cleanup of low-similarity situations
   - Semantic clustering to find representative situations
   - Pruning strategy for memory growth management

4. **Execution Integration**
   - EIP-712 signing for order authentication
   - Real execution against live DEX liquidity
   - Slippage estimation and execution validation

5. **Backtesting Framework**
   - Replay trades through historical market data
   - Measure return attribution (skill vs luck)
   - Walk-forward validation with fresh data

---

## References

- ChromaDB Docs: https://docs.trychroma.com/
- Sentence Transformers: https://www.sbert.net/
- Kelly Criterion: https://en.wikipedia.org/wiki/Kelly_criterion
- EIP-712: https://eips.ethereum.org/EIPS/eip-712
"""