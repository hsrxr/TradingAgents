# Integration Checklist - Memory & State Management Refactoring

## Pre-Integration Setup

- [X]  **Install Dependencies**

  ```bash
  pip install -r REQUIREMENTS_UPDATE.txt
  # Or: pip install chromadb sentence-transformers
  ```
- [X]  **Validate Setup**

  ```bash
  python validate_refactoring.py
  # Expected: All checks pass ✓
  ```
- [X]  **Initialize Databases** (First Run Only)

  ```bash
  python validate_refactoring.py --init
  # Creates portfolio.db and initializes ChromaDB
  ```
- [X]  **Download Embedding Model**

  ```bash
  python validate_refactoring.py --check-chromadb
  # Downloads sentence-transformers/all-MiniLM-L6-v2 (~100MB)
  ```

---

## Graph Integration

### Step 1: Add Context Merge Node

**File**: `tradingagents/graph/trading_graph.py`

- [X]  Add import at top:

  ```python
  from tradingagents.graph.context_merger import create_context_merge_node
  ```
- [X]  Create node in `TradingAgentsGraph.__init__()` or `ParallelGraphSetup`:

  ```python
  context_merge_node = create_context_merge_node()
  graph.add_node("context_merge", context_merge_node)
  ```
- [X]  Connect in graph flow (after gathering market/news data):

  ```python
  # Current flow example:
  graph.add_edge("sentiment_analyst", "context_merge")

  # After context_merge, route to analysts
  graph.add_edge("context_merge", "bull_researcher")
  graph.add_edge("context_merge", "bear_researcher")
  graph.add_edge("context_merge", "investment_judge")
  ```

**Expected Result**: global_portfolio_context field populated before researcher agents run

### Step 2: Update Analyst Prompts

**Files**:

- `tradingagents/agents/researchers/bull_researcher.py`
- `tradingagents/agents/researchers/bear_researcher.py`

- [X]  Modify system prompt in `create_bull_researcher()`:

  ```python
  system_prompt = f"""
  You are a bullish analyst. Generate bullish arguments for the trading pair.

  === CURRENT PORTFOLIO STATE ===
  {state.get('global_portfolio_context', 'Portfolio context unavailable')}

  === DECISION CONSTRAINTS ===
  Do NOT recommend positions that exceed the risk constraints above.
  Do NOT recommend BUY if account drawdown is near -5%.
  Adjust recommendation size based on available position capacity.

  === ORIGINAL INSTRUCTIONS ===
  [Rest of original bull analyst prompt...]
  """
  ```
- [X]  Same modification for bear_researcher.py with appropriate bearish language:

  ```python
  system_prompt = f"""
  ...
  {state.get('global_portfolio_context', '...')}

  Do NOT recommend SELL/SHORT positions that exceed limits.
  Consider risk management constraints when advising bearish positions.
  ...
  """
  ```

**Expected Result**: Analysts receive real-time portfolio constraints; prompts reference portfolio state

### Step 3: Update Trader Prompt

**File**: `tradingagents/agents/trader/trader.py`

- [X]  Modify system prompt to include position sizing guidance:

  ```python
  system_prompt = f"""
  You synthesize research into a final BUY/SELL/HOLD decision.

  === PORTFOLIO STATE ===
  {state.get('global_portfolio_context', 'Context unavailable')}

  === POSITION SIZING RULES ===
  Your confidence value (0.0-1.0) will be used for Kelly formula sizing:
  - confidence 0.50 → order size = 0% (minimum threshold)
  - confidence 0.60 → order size = 20%
  - confidence 0.70 → order size = 40%
  - confidence 0.80 → order size = 60%
  - confidence 0.90 → order size = 80%
  - confidence 1.00 → order size = 100%

  Output JSON must include BOTH action and confidence:
  {{
    "action": "BUY|SELL|HOLD",
    "confidence": 0.0-1.0,
    "thesis": "Explanation of decision",
    "time_horizon": "Short|Medium|Long"
  }}

  === ORIGINAL INSTRUCTIONS ===
  [Rest of trader prompt...]
  """
  ```
- [X]  Ensure portfolio_balance is injected:

  ```python
  # Should already exist at line ~30, verify it's there:
  prompt = f"Portfolio Balance:\n{json.dumps(state['portfolio_balance'], indent=2)}\n\n{prompt}"
  ```

**Expected Result**: Trader receives portfolio context; outputs confidence value for Kelly sizing

### Step 4: Verify Risk Engine Integration

**File**: `tradingagents/agents/managers/risk_engine.py`

- [X]  Already modified (✅ DONE), but verify:

  ```python
  def create_risk_engine():
      portfolio_manager = PortfolioManager(db_path="./trade_memory/portfolio.db")

      def risk_engine_node(state):
          # Should read from database
          current_portfolio = portfolio_manager.load_latest_portfolio()

          # Should apply Kelly sizing
          kelly_fraction = max(0.0, 2 * capped_confidence - 1)

          # Should enforce drawdown
          if drawdown < -max_drawdown_pct:
              order_notional = 0.0

          # Should persist
          portfolio_manager.save_portfolio_state(updated_portfolio)
  ```
- [X]  Verify order output includes kelly_fraction:

  ```python
  order = {
      ...
      "kelly_fraction": round(kelly_fraction, 3),
      ...
  }
  ```

**Expected Result**: Risk engine reads from database; applies Kelly formula; persists trades

### Step 5: Verify Reflection Integration

**File**: `tradingagents/graph/reflection.py`

- [X]  Check that reflect_on_trader() writes to ChromaDB with metadata:

  ```python
  # Look for this pattern around line ~67-80:
  situation = f"Market context: {report}. Decision: {decision}. Outcome: {returns_losses}"
  recommendation = llm_response

  self.trader_memory.add_situations(
      [(situation, recommendation)],
      metadata_list=[{
          "ticker": state.get("company_of_interest", ""),
          "pnl_result": "win" if float(returns_losses) > 0 else "loss",
          "return_amount": float(returns_losses),
      }]
  )
  ```
- [X]  Verify all 5 memories are written with metadata:

  ```python
  # Should have 5 calls:
  self.bull_memory.add_situations(...)     # ✓
  self.bear_memory.add_situations(...)     # ✓
  self.trader_memory.add_situations(...)   # ✓
  self.invest_judge_memory.add_situations(...)     # ✓
  self.risk_manager_memory.add_situations(...)     # ✓
  ```

**Expected Result**: Reflection writes to persistent ChromaDB; stores outcome metadata

---

## Testing & Validation

### Unit Tests

- [X]  **Test 1: Portfolio Persistence**

  ```python
  from tradingagents.portfolio_manager import PortfolioManager

  pm = PortfolioManager()
  portfolio = pm.load_latest_portfolio()
  assert portfolio["cash_usd"] > 0

  pm.save_portfolio_state({
      "cash_usd": 9500.0,
      "positions": {},
      "unrealized_pnl": 0.0,
      "realized_pnl": 0.0,
  })

  updated = pm.load_latest_portfolio()
  assert updated["cash_usd"] == 9500.0
  ```

  ✅ Expected: PASS
- [X]  **Test 2: Semantic Memory**

  ```python
  from tradingagents.agents.utils.memory import VectorizedMemory

  memory = VectorizedMemory("test_memory")
  memory.add_situations([
      ("Bitcoin at ATH with strong momentum", "Recommend LONG"),
      ("Ethereum showing weakness", "Recommend HOLD"),
  ])

  matches = memory.get_memories("Bitcoin breaking resistance")
  assert len(matches) > 0
  assert matches[0]["similarity_score"] > 0.5
  ```

  ✅ Expected: PASS (retrieves Bitcoin situation)
- [X]  **Test 3: Risk Engine Kelly Sizing**

  ```python
  from tradingagents.agents.managers.risk_engine import create_risk_engine

  risk_engine = create_risk_engine()
  state = {
      "trader_investment_plan": '{"action": "BUY", "confidence": 0.8}',
      "portfolio_balance": {"cash_usd": 10000.0, "position_usd": 0.0},
      "company_of_interest": "BTC/USDC",
      "risk_debate_state": {},
  }

  result = risk_engine(state)
  final_decision = json.loads(result["final_trade_decision"])

  assert final_decision["action"] == "BUY"
  assert final_decision["order"]["kelly_fraction"] == 0.6  # 2*0.8-1=0.6
  assert final_decision["order"]["notional_usd"] > 0
  ```

  ✅ Expected: PASS (Kelly fraction = 0.6 for confidence 0.8)
- [X]  **Test 4: Drawdown Protection**

  ```python
  # User simulates $500 loss (5.1% drawdown)
  pm.save_portfolio_state({
      "cash_usd": 9500.0,
      "positions": {},
      "unrealized_pnl": -500.0,
      "realized_pnl": 0.0,
  })

  # Try to BUY
  state = {"trader_investment_plan": '{"action": "BUY", "confidence": 0.9}', ...}
  result = risk_engine(state)
  final_decision = json.loads(result["final_trade_decision"])

  assert "drawdown_exceeded" in final_decision["order"]["risk_status"]
  assert final_decision["order"]["notional_usd"] == 0.0
  ```

  ✅ Expected: PASS (blocks BUY at drawdown > -5%)

### Integration Tests

- [X]  **Test 5: Full Graph with Context Merge**

  ```bash
  # Run trading_graph.py with test input
  python -c "
  from tradingagents.graph.trading_graph import TradingAgentsGraph

  graph = TradingAgentsGraph()
  state = graph.propagator.create_initial_state('BTC/USDC', '2026-03-30')

  assert 'global_portfolio_context' in state
  assert 'Current portfolio state' in state['global_portfolio_context']
  assert 'Risk Constraints' in state['global_portfolio_context']
  print('✓ Context merge integration test passed')
  "
  ```

  ✅ Expected: PASS (state includes portfolio context)
- [X]  **Test 6: Memory Persistence Across Restart**

  ```bash
  # Session 1
  python -c "
  from tradingagents.agents.utils.memory import VectorizedMemory

  mem = VectorizedMemory('test_persistence')
  mem.add_situations([('Test situation', 'Test recommendation')])
  print('Added 1 situation')
  "

  # Session 2 (new process)
  python -c "
  from tradingagents.agents.utils.memory import VectorizedMemory

  mem = VectorizedMemory('test_persistence')
  situations = mem.list_all_situations()
  assert len(situations) > 0
  print(f'✓ Found {len(situations)} persistent situation(s)')
  "
  ```

  ✅ Expected: PASS (ChromaDB persists across restarts)

---

## Validation Checklist

### Before Merging to Main

- [X]  All unit tests pass
- [X]  All integration tests pass
- [X]  validate_refactoring.py shows all checks ✓
- [X]  Portfolio loads on first run
- [X]  Context merge broadcasts to analysts
- [X]  Memory retrieval uses semantic search (not BM25)
- [X]  Risk engine persists portfolio after orders
- [X]  Drawdown protection works (-5% limit)
- [X]  Kelly formula applies (confidence adjustment)
- [X]  Trade history records all orders
- [X]  Reflection writes to ChromaDB with metadata
- [X]  No breaking changes to existing prompts (graceful fallback)
- [X]  Backward compatible: FinancialSituationMemory still works

### Performance Checks

- [ ]  Portfolio load: <1ms ✓
- [ ]  Memory search: <20ms ✓
- [ ]  Context merge: <10ms ✓
- [ ]  Full E2E flow: < 5 min ✓

### Documentation Review

- [ ]  REFACTORING_GUIDE.md reviewed ✓
- [ ]  IMPLEMENTATION_SUMMARY.md reviewed ✓
- [X]  REQUIREMENTS_UPDATE.txt installed ✓
- [ ]  Code comments added where needed ✓

---

## Rollback Plan

If integration causes issues:

1. **Database backup**:

   ```bash
   cp ./trade_memory/portfolio.db ./trade_memory/portfolio.db.backup
   cp -r ./trade_memory/chromadb ./trade_memory/chromadb.backup
   ```
2. **Revert graph changes**:

   - Remove context_merge node from graph connections
   - Remove global_portfolio_context references from prompts
   - Keep portfolio_manager import (won't break anything)
3. **Fallback behavior**:

   - Risk engine still works if portfolio load fails (uses state fallback)
   - Analysts still work if global_portfolio_context missing (no constraints)
   - Memory still searchable (defaults to ChromaDB, no BM25)

---

## After Integration

- [ ]  Monitor log files for errors
- [X]  Check trade_history table is growing
- [X]  Verify ChromaDB collections have situations
- [ ]  Test portfolio evolution over 10+ runs
- [ ]  Validate memory retrieval improves decisions
- [ ]  Measure E2E execution time (should be similar)

---

## Support

Questions? Review:

1. `REFACTORING_GUIDE.md` - Architecture details
2. `IMPLEMENTATION_SUMMARY.md` - What changed
3. Validation script: `python validate_refactoring.py --help`

Key Files:

- Portfolio: `tradingagents/portfolio_manager.py`
- Memory: `tradingagents/agents/utils/memory.py`
- Context: `tradingagents/graph/context_merger.py`
- Risk: `tradingagents/agents/managers/risk_engine.py`
