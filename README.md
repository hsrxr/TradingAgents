# TradingAgents ERC-8004

A multi-agent LLM trading framework focused on crypto market workflows.

This repository is an actively usable refactored build. It keeps the original multi-role decision pipeline and adds production-oriented foundations such as persistent portfolio state, semantic memory, and shared risk context broadcasting.

## Project Status

- Completed: End-to-end multi-agent trading flow (analysis -> research debate -> trading -> risk adjudication -> portfolio decision)
- Completed: Both serial and parallel execution modes via LangGraph
- Completed: Unified multi-provider LLM integration (OpenAI-compatible, Anthropic, Google)
- Completed: SQLite-based portfolio persistence across sessions
- Completed: ChromaDB vector memory replacing keyword-only memory
- Completed: Global portfolio context injection for cross-agent risk alignment
- Completed: Hardened risk engine (Kelly-based scaling + drawdown guardrails)
- Completed: Repository cleanup and docs restructuring (docs, data, examples)

## Core Capabilities

### 1) Multi-Role Collaborative Decision Making

- Analyst Team: market, news, quant, social, and fundamentals analysis
- Research Team: bull/bear debate and investment synthesis
- Trader: generates a trade proposal with action + confidence
- Risk Management: applies deterministic risk constraints
- Portfolio Manager: emits the final trade decision

### 2) Memory and State System

- PortfolioManager (SQLite)
  - Portfolio snapshots: cash, positions, PnL, total assets
  - Trade audit ledger: trade_history
- FinancialSituationMemory (ChromaDB)
  - Persistent semantic retrieval
  - Metadata filtering support (ticker, pnl_result, trade_date, etc.)
- Context Merger
  - Builds global_portfolio_context from the latest portfolio state
  - Broadcasts constraints to downstream research/trading agents

### 3) Risk Control

- Max position and max single-order percentage limits
- Kelly-fraction adjustment from model confidence
- Drawdown protection to reduce new risk exposure
- Standardized JSON decision payload from the risk engine

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/TauricResearch/TradingAgents.git
cd TradingAgents
```

### 2. Create a virtual environment and install dependencies

```bash
python -m venv .venv
# Windows
.\.venv\Scripts\Activate.ps1
# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt
```

Notes:

- pyproject.toml contains the fuller dependency definition (including refactor additions)
- requirements.txt is the lightweight install list

### 3. Configure environment variables

Set at least one provider key:

```bash
# OpenAI / OpenAI-compatible endpoints (deepseek, openrouter, etc.)
export OPENAI_API_KEY=your_key

# Google
export GOOGLE_API_KEY=your_key

# Anthropic
export ANTHROPIC_API_KEY=your_key

# xAI (optional)
export XAI_API_KEY=your_key

# OpenRouter (optional)
export OPENROUTER_API_KEY=your_key
```

Windows PowerShell example:

```powershell
$env:OPENAI_API_KEY = "your_key"
```

### 4. Optional: run refactor validation script

```bash
python docs/scripts/validate_refactoring.py
```

First-time persistence initialization:

```bash
python docs/scripts/validate_refactoring.py --init
```

## How to Run

### Option A: Run main flow directly

```bash
python main.py
```

The default sample run executes one full graph pass on WETH/USDC.

### Option B: Use the interactive CLI

```bash
python -m cli.main
```

Or use the installed entrypoint:

```bash
tradingagents
```

### Option C: Start trigger-based runtime

```bash
python trigger_main.py
```

This mode polls event sources (news/social) and triggers runs by an aggregation window.

## Python Usage Example

```python
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

config = DEFAULT_CONFIG.copy()
config["llm_provider"] = "deepseek"      # openai / deepseek / openrouter / xai / anthropic / google / ollama
config["backend_url"] = "https://api.deepseek.com/v1"
config["deep_think_llm"] = "deepseek-reasoner"
config["quick_think_llm"] = "deepseek-chat"
config["max_debate_rounds"] = 1

graph = TradingAgentsGraph(
    debug=True,
    selected_analysts=["market", "news", "quant"],
    config=config,
    parallel_mode=True,
)

final_state, decision = graph.propagate("WETH/USDC", "2026-03-30 21:00:00")
print(decision)
```

## Project Structure (Condensed)

```text
TradingAgents-0.2.1/
├── tradingagents/
│   ├── agents/                 # analysts, researchers, trader, risk modules
│   ├── graph/                  # LangGraph workflow and orchestration
│   ├── dataflows/              # prices, indicators, news processing
│   ├── llm_clients/            # multi-provider LLM client layer
│   ├── portfolio_manager.py    # SQLite portfolio persistence
│   └── default_config.py       # default runtime config
├── cli/                        # terminal UI/CLI
├── docs/                       # guides, checklists, architecture docs
├── trade_memory/               # runtime persistence (DB/vector store)
├── main.py                     # main entry
└── trigger_main.py             # trigger runtime entry
```

## Key Documents

- docs/PROJECT_STRUCTURE.md: repository structure guide
- docs/IMPLEMENTATION_SUMMARY.md: refactor implementation summary
- docs/INTEGRATION_CHECKLIST.md: integration and verification checklist
- docs/REFACTORING_GUIDE.md: architecture-level details
- docs/QUICK_REFERENCE.md: quick operational reference

## Notes

- This project is for research and engineering validation and is not financial advice.
- LLM behavior is non-deterministic. Always run backtesting and risk validation before live usage.
- trade_memory and eval_results are runtime artifacts. Manage retention and backups accordingly.

## License

See LICENSE in the repository root.
