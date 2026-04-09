# TradingAgents v0.2.1 - 多代理LLM加密交易框架

[![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen)](docs/PROJECT_ANALYSIS.md)

一个完整的、生产级的多代理LLM交易框架，专为加密货币市场设计。通过协作型AI代理进行多角度市场分析、讨论和交易决策。

## 📊 项目概览

**TradingAgents** 实现了一个端到端的多代理协作系统，将复杂的交易决策分解为多个专业角色进行深度分析和讨论。系统遵循生产级的架构设计，包含持久化状态、向量化语义记忆、全局风险约束和强化风险管理引擎。

### 🎯 核心特性

#### 1️⃣ 多角色协作决策系统（Multi-Role Collaborative Framework）

**分析团队（Analyst Team）5人组**

- 🔍 **市场分析师** - 技术指标、价格趋势、支撑阻力位分析
- 📰 **新闻分析师** - 新闻驱动、市场情绪、基本信息分析
- 📊 **量化分析师** - 统计模型、量化信号、历史数据分析

**研究团队（Research Team）**

- 📢 **研究员** - 进行深度牛/熊市辩论，综合多视角

**执行和管理（Execution & Management）**

- 🚀 **交易员** - 生成交易提案（BUY/SELL/HOLD + 置信度）
- ⚠️ **风险管理器** - 应用Kelly公式、Drawdown保护、约束校验

#### 2️⃣ 生产级状态管理系统


| 组件             | 技术              | 功能                                |
| ---------------- | ----------------- | ----------------------------------- |
| **投资组合状态** | SQLite            | 现金、仓位、PnL持久化；完整审计跟踪 |
| **语义记忆**     | ChromaDB + 向量化 | 跨会话语义检索；元数据过滤          |
| **全局约束**     | 实时上下文广播    | 风险参数同步；统一决策规则          |
| **执行追踪**     | JSON审计日志      | EIP-712兼容签名；历史回溯           |

#### 3️⃣ 灵活的执行模式

- **串行模式** - 按顺序执行各角色，确定性强，便于调试
- **并行模式** - 并行执行分析师和讨论，效率提升2-3倍

#### 4️⃣ 多LLM供应商统一支持


| 提供商         | 推荐模型           | 速度     | 质量       | 特殊功能          |
| -------------- | ------------------ | -------- | ---------- | ----------------- |
| **OpenAI**     | gpt-4, gpt-4-turbo | ⭐⭐⭐   | ⭐⭐⭐⭐⭐ | o1 思考链         |
| **Anthropic**  | claude-3-opus      | ⭐⭐⭐   | ⭐⭐⭐⭐⭐ | extended thinking |
| **DeepSeek**   | deepseek-reasoner  | ⭐⭐⭐⭐ | ⭐⭐⭐⭐   | 推理链✅ 性价比优 |
| **Google**     | gemini-1.5-pro     | ⭐⭐⭐   | ⭐⭐⭐⭐   | thinking 模式     |
| **OpenRouter** | 100+组合           | ⭐⭐     | 可选       | 多模型支持        |

#### 5️⃣ 强化风险管理

- **Kelly公式位置调整** - 基于置信度的最优头寸大小
  ```
  Kelly分数 = 2 × 置信度 - 1
  订单大小 = 基础大小 × Kelly分数
  ```
- **Drawdown保护** - 5%回撤时自动停止新建仓位
- **头寸限额** - 最大头寸占比、单笔订单占比
- **动态约束** - 基于实时投资组合状态的动态调整

#### 6️⃣ 完整的数据流处理

- 🔗 **加密货币价格** - GeckoTerminal DEX实时价格和OHLCV
- 📡 **新闻聚合** - RSS订阅、完整文章抓取、社交监控
- 📈 **技术指标** - 20+内置指标 + 自定义量化信号
- 💾 **智能缓存** - 自动缓存机制避免重复请求

---

## 🚀 快速开始（5分钟）

### 前置条件

- Python 3.10 或更高版本
- 至少一个LLM提供商的API密钥（OpenAI, Anthropic, DeepSeek等）
- 2GB可用磁盘空间（用于向量数据库和缓存）

### 1️⃣ 克隆和环境设置

```bash
# 克隆项目
git clone https://github.com/TauricResearch/TradingAgents.git
cd TradingAgents-0.2.1

# 创建虚拟环境
python -m venv .venv

# Windows激活
.\.venv\Scripts\Activate.ps1

# macOS/Linux激活
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2️⃣ 配置API密钥

选择至少一个LLM提供商并配置其API密钥：

**Windows PowerShell:**

```powershell
# 方式1：环境变量（临时，仅当前会话）
$env:DEEPSEEK_API_KEY = "your_key_here"
$env:OPENAI_API_KEY = "your_key_here"
$env:ANTHROPIC_API_KEY = "your_key_here"

# 方式2：创建 .env 文件（推荐）
# 在项目根路径创建 .env 文件，内容如下：
# DEEPSEEK_API_KEY=your_key_here
# OPENAI_API_KEY=your_key_here
# ANTHROPIC_API_KEY=your_key_here
```

**Linux/macOS:**

```bash
export DEEPSEEK_API_KEY="your_key_here"
export OPENAI_API_KEY="your_key_here"
export ANTHROPIC_API_KEY="your_key_here"
```

### 3️⃣ 运行你的第一个交易流程

**方式A：直接运行示例**

```bash
python main.py
```

默认配置会在WETH/USDC上执行一次完整的多代理分析和交易提案。

**方式B：使用交互式CLI**

```bash
# 激活entrypoint
tradingagents

# 或直接运行
python -m cli.main
```

**方式C：Python代码中使用**

```python
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG
import json

# 自定义配置
config = DEFAULT_CONFIG.copy()
config["llm_provider"] = "deepseek"          # 选择LLM供应商
config["deep_think_llm"] = "deepseek-reasoner"
config["quick_think_llm"] = "deepseek-chat"
config["max_debate_rounds"] = 2              # 增加辩论轮数
config["parallel_mode"] = True               # 启用并行模式

# 初始化交易代理框架
graph = TradingAgentsGraph(
    debug=True,
    selected_analysts=["market", "news", "quant"],  # 选择分析师
    config=config,
    parallel_mode=True
)

# 执行交易流程
final_state, decision = graph.propagate("WETH/USDC", "2026-03-30 21:00:00")

# 输出最终决策
print(json.dumps(decision, indent=2))
```

**预期输出示例：**

```json
{
  "ticker": "WETH/USDC",
  "recommendation": "BUY",
  "confidence": 0.75,
  "rationale": "Multiple bullish signals from technical analysis, positive news sentiment, and quantitative indicators",
  "risk_assessment": "MODERATE",
  "position_size_usd": 495.00,
  "kelly_fraction": 0.50,
  "risk_status": "ALLOWED"
}
```

### 4️⃣ 启动后端服务 + 前端网页（Dashboard）

当前仓库包含完整的本地可视化联调链路：

- 后端服务：`runtime_api_server.py`（默认 `127.0.0.1:8765`）
- 前端网页：`web-dashboard/`（Vite + React + TypeScript）

在项目根目录启动后端：

```bash
python runtime_api_server.py
```

新开一个终端，启动前端：

```bash
cd web-dashboard
npm install
npm run dev
```

打开浏览器访问Vite输出地址（通常是 `http://127.0.0.1:5173`）。

注意：前端默认请求 `http://127.0.0.1:8765`，配置位于 `web-dashboard/src/store/dashboardStore.ts` 的 `API_BASE`。

---

## 🌐 前后端联调说明

### 架构关系

- 前端：负责展示运行状态、事件流、交易记录，并触发新的run
- 后端：包装 `TradingAgentsGraph`，以HTTP API形式暴露运行控制和事件查询
- 核心引擎：`tradingagents/` 中的多代理图和风险流程

---

## ⛓️ ERC-8004 Path B 链上交互（Sepolia 共享合约）

仓库已内置 Path B 所需的链上交互层，使用独立脚本 `web3_path_b.py` 即可运行。

### 1. 环境变量

在项目根目录 `.env` 中配置：

```env
SEPOLIA_RPC_URL=https://ethereum-sepolia-rpc.publicnode.com

# operatorWallet: 持有 agent NFT、发交易、付 gas
OPERATOR_PRIVATE_KEY=0x...

# agentWallet: 专门用于 EIP-712 TradeIntent 签名
AGENT_WALLET_PRIVATE_KEY=0x...

# Path B 文档中的共享合约地址（可不填，代码内置默认值）
AGENT_REGISTRY_ADDRESS=0x97b07dDc405B0c28B17559aFFE63BdB3632d0ca3
HACKATHON_VAULT_ADDRESS=0x0E7CD8ef9743FEcf94f9103033a044caBD45fC90
RISK_ROUTER_ADDRESS=0xd6A6952545FF6E6E6681c2d15C59f9EB8F40FdBC
REPUTATION_REGISTRY_ADDRESS=0x423a9904e39537a9997fbaF0f220d79D7d545763
VALIDATION_REGISTRY_ADDRESS=0x92bF63E5C7Ac6980f237a7164Ab413BE226187F1

# 注册完成后写入
AGENT_ID=123
```

### 2. 注册 Agent

```bash
uv run python web3_path_b.py register \
    --name "My Agent" \
    --description "A trustless AI trading agent" \
    --capabilities "trading,eip712-signing" \
    --agent-uri "https://example.com/agent-metadata.json"
```

执行后会输出并写入 `agent-id.json`（包含 `agentId` 与 `txHash`）。

### 3. 领取 0.05 ETH 沙盒资金

```bash
uv run python web3_path_b.py claim --agent-id 123
```

查询余额/是否已领取：

```bash
uv run python web3_path_b.py balance --agent-id 123
```

### 4. 提交 TradeIntent（EIP-712）

先模拟：

```bash
uv run python web3_path_b.py simulate-intent \
    --agent-id 123 \
    --pair XBTUSD \
    --action BUY \
    --amount-usd-scaled 50000 \
    --max-slippage-bps 100
```

再提交：

```bash
uv run python web3_path_b.py submit-intent \
    --agent-id 123 \
    --pair XBTUSD \
    --action BUY \
    --amount-usd-scaled 50000 \
    --max-slippage-bps 100
```

命令会自动获取链上 nonce、签名并提交到 RiskRouter。

### 5. 发布验证 Checkpoint

```bash
uv run python web3_path_b.py post-checkpoint \
    --agent-id 123 \
    --action BUY \
    --pair XBTUSD \
    --amount-usd-scaled 50000 \
    --price-usd-scaled 185000 \
    --score 85 \
    --reasoning "Momentum signal confirmed by volume" \
    --notes "Round 1 execution"
```

该命令会：
- 生成 checkpoint 的 EIP-712 digest（`checkpointHash`）
- 调用 `ValidationRegistry.postEIP712Attestation`
- 追加本地审计日志 `checkpoints.jsonl`

### 6. 查询验证分与信誉分

```bash
uv run python web3_path_b.py scores --agent-id 123
```

返回：`validationScore` 与 `reputationScore`。

### 后端API一览（runtime_api_server.py）

- `GET /healthz`
    - 健康检查
    ---
- `POST /api/run/start`
    ## 🔄 自动链上集成 — Agent 决策自动提交
    - 启动一次交易流程
    **新增功能**：Agent 生成交易决策后，可自动签名并提交 `TradeIntent` 到 RiskRouter，以及向 ValidationRegistry 提交 `Checkpoint`。
    - 请求体示例：
    无需手动调用 `web3_path_b.py`，一切自动化。

    ### 启用自动链上提交
```json
    #### 1. 配置 `.env`
{
    ```bash
    SEPOLIA_RPC_URL=https://ethereum-sepolia-rpc.publicnode.com
    OPERATOR_PRIVATE_KEY=0x...              # 操作者钱包私钥
    AGENT_WALLET_PRIVATE_KEY=0x...          # Agent 钱包私钥
    AGENT_ID=123                            # 已注册的 Agent ID
    AGENT_WALLET=0x...                      # Agent 钱包地址
    ```
    "pair": "WETH/USDC",
    参考 `.env.example_on_chain`。
    "tradeDate": "2026-04-02 10:00:00",
    #### 2. 启用配置
    "selectedAnalysts": ["market", "news", "quant"],
    ```python
    config = DEFAULT_CONFIG.copy()
    config["enable_on_chain_submission"] = True
    "parallelMode": true
    ta = TradingAgentsGraph(..., config=config)
    final_state, decision = ta.propagate("WETH/USDC", trade_date)
    # TradeIntent 和 Checkpoint 自动提交！
    ```
}
    #### 3. 查看日志
```
    ```
    INFO - Submitting on-chain: action=BUY, pair=WETH/USDC, amount=500.00 USD
    INFO - TradeIntent submitted: 0xabc123...
    INFO - Checkpoint submitted: 0xdef456...
    ```

    ### 工作流
- `GET /api/runs`
    ```
    Agent 决策 → 解析 → 模拟 [可选] → 签名 → 提交 TradeIntent → 构建 Checkpoint → 提交
    ```
    - 查看最近runs列表与状态
    **无需修改 Agent 代码** — 自动适配 `final_trade_decision` JSON。
- `GET /api/runs/{runId}/events?after={offset}`
    详情见 [ON_CHAIN_INTEGRATION.md](./ON_CHAIN_INTEGRATION.md)
    - 增量拉取事件流（前端默认约900ms轮询）
    ---

前端调用入口可参考：

- `web-dashboard/src/store/dashboardStore.ts`
    - `startRun()` -> `POST /api/run/start`
    - 轮询events -> `GET /api/runs/{runId}/events`

---

## 📖 使用指南

### 场景1：自定义LLM配置

```python
config = DEFAULT_CONFIG.copy()

# OpenAI选项
config["llm_provider"] = "openai"
config["deep_think_llm"] = "gpt-4"
config["quick_think_llm"] = "gpt-3.5-turbo"

# DeepSeek选项（推荐，性价比最优）
config["llm_provider"] = "deepseek"
config["backend_url"] = "https://api.deepseek.com/v1"
config["deep_think_llm"] = "deepseek-reasoner"    # 支持chain-of-thought
config["quick_think_llm"] = "deepseek-chat"

# Anthropic选项
config["llm_provider"] = "anthropic"
config["deep_think_llm"] = "claude-3-opus-20250219"
config["quick_think_llm"] = "claude-3-haiku-20250307"

# Google选项
config["llm_provider"] = "google"
config["deep_think_llm"] = "gemini-2.0-pro"
config["quick_think_llm"] = "gemini-1.5-flash"
```

### 场景2：选择不同的分析师组合

```python
# 只使用技术面和新闻分析
graph = TradingAgentsGraph(
    selected_analysts=["market", "news"],
    parallel_mode=False
)

# 使用全部分析师，并行执行
graph = TradingAgentsGraph(
    selected_analysts=["market", "news", "quant", "fundamentals", "social"],
    parallel_mode=True
)
```

### 场景3：从持久化投资组合恢复

```python
from tradingagents.portfolio_manager import PortfolioManager

pm = PortfolioManager()

# 加载最新的投资组合
latest = pm.load_latest_portfolio()
print(f"Current cash: ${latest['cash_usd']:.2f}")
print(f"Open position: ${latest['position_usd']:.2f}")
print(f"Total assets: ${latest['total_assets']:.2f}")

# 获取交易历史
trades = pm.get_portfolio_history()
for trade in trades:
    print(f"{trade['timestamp']}: {trade['ticker']} {trade['side']} @ {trade['notional_usd']}")
```

### 场景4：实时事件触发模式

```bash
# 启动事件驱动的交易运行时（监听新闻和社交信号）
python trigger_main.py
```

此模式会：

- 持续监听RSS新闻源
- 监控社交媒体信号（Nitter）
- 聚合事件信号
- 在事件聚合窗口关闭时自动触发交易流程

---

## 📂 项目结构梗概

```
TradingAgents-0.2.1/
├── 📄 README.md                               # 本文件
├── 📄 pyproject.toml                          # 项目配置和依赖定义
├── 📄 requirements.txt                        # Python依赖（简化版）
├── 📄 main.py                                 # 主入口点
├── 📄 runtime_api_server.py                   # 后端Runtime API服务（HTTP）
├── 📄 trigger_main.py                         # 事件触发运行时入口
│
├── 📁 tradingagents/                          # ⭐ 核心库代码
│   ├── 📄 default_config.py                   # 默认配置（模型、参数等）
│   ├── 📄 portfolio_manager.py                # SQLite投资组合持久化
│   ├── 📁 agents/                             # 所有代理角色实现
│   │   ├── analysts/                          # 5种分析师实现
│   │   ├── researchers/                       # 研究员实现
│   │   ├── trader/                            # 交易员实现
│   │   ├── managers/                          # 风险和投资组合经理
│   │   └── utils/
│   │       ├── memory.py                      # ChromaDB向量记忆
│   │       └── agent_states.py                # 代理状态定义
│   ├── 📁 graph/                              # ⭐ LangGraph工作流
│   │   ├── trading_graph.py                   # 主协调器
│   │   ├── setup.py                           # 串行拓扑配置
│   │   ├── parallel_setup.py                  # 并行拓扑配置
│   │   ├── context_merger.py                  # 投资组合上下文注入
│   │   ├── conditional_logic.py               # 路由和条件逻辑
│   │   ├── propagation.py                     # 图流传播
│   │   ├── reflection.py                      # 交易后反思和学习
│   │   └── signal_processing.py               # 信号处理
│   ├── 📁 dataflows/                          # 数据流处理管道
│   │   ├── geckoterminal_price.py             # DEX价格获取
│   │   ├── calculate_indicators.py            # 技术指标计算
│   │   ├── rss_processor.py                   # RSS新闻处理
│   │   ├── get_full_articles.py               # 文章内容爬取
│   │   └── utils.py                           # 缓存和工具函数
│   └── 📁 llm_clients/                        # ⭐ 多LLM供应商支持
│       ├── factory.py                         # 客户端工厂
│       ├── base_client.py                     # 基础客户端接口
│       ├── openai_client.py                   # OpenAI和兼容端点
│       ├── anthropic_client.py                # Anthropic支持
│       ├── google_client.py                   # Google支持
│       └── validators.py                      # 输出验证
│
├── 📁 cli/                                    # 命令行界面
│   ├── main.py                                # CLI应用入口
│   ├── models.py                              # CLI数据模型
│   └── config.py                              # CLI配置
│
├── 📁 web-dashboard/                          # ⭐ 前端可视化Dashboard（React+Vite）
│   ├── src/                                   # 页面、组件、状态管理
│   ├── package.json                           # 前端依赖和脚本
│   └── README.md                              # 前端工程说明
│
├── 📁 docs/                                   # 详细文档
│   ├── PROJECT_ANALYSIS.md                    # ⭐ 项目完成度分析（新）
│   ├── PROJECT_STRUCTURE.md                   # 项目结构说明
│   ├── IMPLEMENTATION_SUMMARY.md              # 实现细节总结
│   ├── INTEGRATION_CHECKLIST.md               # 集成测试清单
│   ├── REFACTORING_GUIDE.md                   # 重构和架构指南
│   ├── BEFORE_AFTER.md                        # v0.1→v0.2升级对比
│   ├── QUICK_REFERENCE.md                     # 快速参考
│   └── scripts/
│       └── validate_refactoring.py            # 依赖和配置验证脚本
│
├── 📁 trade_memory/                           # ⭐ 运行时持久化数据
│   ├── portfolio.db                           # SQLite投资组合和交易历史
│   └── chromadb/                              # ChromaDB向量数据库
│       └── chroma.sqlite3
│
├── 📁 eval_results/                           # 评估和回测结果
└── 📁 visualisation/                          # 可视化资源（仪表板HTML等）
```

---

## ⚙️ 配置参考

所有配置选项都定义在 `DEFAULT_CONFIG` 中（`tradingagents/default_config.py`）：

### LLM配置


| 参数                   | 类型  | 说明                                                       |
| ---------------------- | ----- | ---------------------------------------------------------- |
| `llm_provider`         | str   | LLM供应商：deepseek/openai/anthropic/google/openrouter/xai |
| `deep_think_llm`       | str   | 用于深度分析的模型                                         |
| `quick_think_llm`      | str   | 用于快速判断的模型                                         |
| `backend_url`          | str   | OpenAI兼容端点的后端URL                                    |
| `llm_timeout_seconds`  | float | LLM调用超时（默认180秒）                                   |
| `llm_max_retries`      | int   | 失败重试次数（默认5）                                      |
| `enable_llm_streaming` | bool  | 启用流式输出                                               |

### 交易流程配置


| 参数                      | 类型  | 默认值 | 说明               |
| ------------------------- | ----- | ------ | ------------------ |
| `max_debate_rounds`       | int   | 1      | 研究员辩论轮数     |
| `max_risk_discuss_rounds` | int   | 1      | 风险讨论轮数       |
| `max_position_pct`        | float | 0.20   | 最大头寸占现金比例 |
| `max_single_order_pct`    | float | 0.10   | 单笔订单占现金比例 |

### 执行配置


| 参数                       | 类型 | 默认值 | 说明           |
| -------------------------- | ---- | ------ | -------------- |
| `parallel_mode`            | bool | False  | 启用并行执行   |
| `enable_progress_tracking` | bool | True   | 显示实时进度   |
| `enable_colored_output`    | bool | True   | 彩色终端输出   |
| `graph_invoke_retries`     | int  | 3      | 图调用失败重试 |

---

## 🔍 主要文档导航


| 文档                                                            | 用途                                                |
| --------------------------------------------------------------- | --------------------------------------------------- |
| **[PROJECT_ANALYSIS.md](docs/PROJECT_ANALYSIS.md)**             | 📊**必读** - 项目完成度详细分析，功能清单和架构演进 |
| **[IMPLEMENTATION_SUMMARY.md](docs/IMPLEMENTATION_SUMMARY.md)** | 🔧 实现细节，各个组件的前后对比                     |
| **[PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md)**           | 📂 项目目录说明，文件用途导航                       |
| **[INTEGRATION_CHECKLIST.md](docs/INTEGRATION_CHECKLIST.md)**   | ✅ 集成和验证清单                                   |
| **[QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md)**               | ⚡ 常见任务的快速参考                               |
| **[REFACTORING_GUIDE.md](docs/REFACTORING_GUIDE.md)**           | 🏗️ 架构设计和扩展指南                             |

---

## 🔌 扩展和集成

### 创建自定义分析师

```python
from tradingagents.agents import BaseAnalyst
from tradingagents.agents.utils.agent_states import AgentState

class YourCustomAnalyst(BaseAnalyst):
    """Your custom analyst implementation."""
  
    def analyze(self, state: AgentState) -> str:
        """
        Perform your custom analysis.
      
        Args:
            state: Agent state with portfolio context, market data, etc.
      
        Returns:
            Analysis as a formatted string
        """
        analysis = f"Custom analysis for {state['company_name']}"
        return analysis
```

### 集成新数据源

```python
from tradingagents.dataflows import BaseDataflow

class YourCustomDataflow(BaseDataflow):
    """Fetch data from your custom source."""
  
    def fetch(self, ticker: str, **kwargs):
        # Your data fetching logic
        return processed_data
```

### 自定义风险规则

编辑 `tradingagents/agents/managers/risk_engine.py`，在风险评估中添加自定义约束。

## 🧪 验证和测试

```bash
# 验证依赖安装和配置
python docs/scripts/validate_refactoring.py

# 首次运行时初始化持久化存储
python docs/scripts/validate_refactoring.py --init

# 运行单个完整流程
python main.py

# 运行CLI交互式模式
tradingagents
```

---

## ⚠️ 重要声明

### 免责声明

- **研究和工程验证用途** - 本项目用于研究、学习和系统验证，不提供财务建议
- **非确定性行为** - LLM的决策输出具有非确定性，即使配置相同也会产生不同结果
- **备份和恢复** - 所有trade_memory和eval_results都是运行时生成的临时数据，应定期备份

### 生产部署建议

1. 充分进行回测和历史数据验证
2. 使用模拟账户验证至少2周
3. 从小额开始，逐步增加交易量
4. 监控所有交易决策和风险指标
5. 定期审查和调整风险参数
6. 有充分的人工干预机制

---

## 🤝 贡献指南

欢迎PR和问题反馈！请参考：

- [INTEGRATION_CHECKLIST.md](/docs/INTEGRATION_CHECKLIST.md) - 集成和测试标准
- [REFACTORING_GUIDE.md](docs/REFACTORING_GUIDE.md) - 代码风格和架构约定

---

## 📞 支持和反馈

- 📖 查看文档：[docs/](docs/)
- 🐛 报告问题：[GitHub Issues](https://github.com/TauricResearch/TradingAgents/issues)
- 💬 讨论功能：[GitHub Discussions](https://github.com/TauricResearch/TradingAgents/discussions)

---

## 📄 许可证

本项目采用MIT许可证。详见 [LICENSE](LICENSE) 文件。

---

**最后更新**: 2026年4月1日
**当前版本**: 0.2.1
**项目状态**: ✅ 生产级 | 功能完整 | 积极维护
