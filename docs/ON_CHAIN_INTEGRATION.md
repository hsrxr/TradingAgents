# 链上集成指南 — TradingAgents Path B On-Chain Integration

本指南说明如何将 TradingAgents 的决策自动提交到 Sepolia 的 ERC-8004 共享合约。

## 概览

链上集成在以下流程中自动发生：

```
Agent 生成交易决策 
     ↓ 
Final Trade Decision JSON  
     ↓
On-Chain Integrator 构建 TradeIntent 
     ↓ 
签名并提交到 RiskRouter 
     ↓ 
构建并提交 Checkpoint 到 ValidationRegistry 
     ↓ 
TradeApproved / TradeRejected 事件
```

## 前置条件

**已完成**：
- ✅ 在 AgentRegistry 上注册了代理（获得 `agentId`）
- ✅ 从 HackathonVault 领取了 0.05 ETH 分配

**所需变量**：
```bash
SEPOLIA_RPC_URL              # Sepolia RPC 端点
OPERATOR_PRIVATE_KEY         # 操作者钱包私钥（支付 gas）
AGENT_WALLET_PRIVATE_KEY     # 代理钱包私钥（签署意图）
AGENT_ID                     # 已注册的代理 ID
AGENT_WALLET                 # 代理钱包地址
```

## 配置

### 1. 设置 `.env`

从 `.env.example_on_chain` 复制示例完成配置：

```bash
cp .env.example_on_chain .env  # 如果还没有 .env
# 然后打开 .env 并填充以下内容：
```

```env
SEPOLIA_RPC_URL=https://ethereum-sepolia-rpc.publicnode.com
OPERATOR_PRIVATE_KEY=0x...  # 你的操作者私钥
AGENT_WALLET_PRIVATE_KEY=0x...  # 你的代理钱包私钥
AGENT_ID=123  # 你注册时获得的 agentId
AGENT_WALLET=0x...  # 你的代理钱包地址
```

### 2. 启用链上提交

修改 `main.py` 或 `trigger_main.py` 中的配置：

```python
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

config = DEFAULT_CONFIG.copy()
config["enable_on_chain_submission"] = True  # ← 启用
config["on_chain_simulation_enabled"] = True  # ← 可选：提交前模拟

ta = TradingAgentsGraph(
    debug=True,
    selected_analysts=['market', 'news', 'quant'],
    config=config,
    parallel_mode=True,
)
```

### 3. 运行分析

```bash
# 一次性分析
python trigger_main.py

# 或 uv run
uv run python trigger_main.py

# 或持续运行（来自 trigger_main.py）
python -m cli.main analyze
```

## 工作流细节

### 自动操作序列

1. **解析决策**  
   - 从 `final_trade_decision` JSON 提取 `action`、`pair`、`notional_usd` 等
   - 跳过 HOLD 订单（无链上提交）

2. **准备 TradeIntent**  
   - 获取当前 nonce：`AgentRegistry.getSigningNonce(agentId)`
   - 构建 TradeIntent 结构体（pair、action、amount、deadline 等）
   - deadline 默认为现在 + 5 分钟

3. **模拟（可选）**  
   - 调用 `RiskRouter.simulateIntent()` 验证是否通过风险检查
   - 如果模拟失败，日志记录原因但不提交

4. **签名和提交**  
   - 使用 EIP-712 签署 TradeIntent（使用 agentWallet）
   - 通过 operatorWallet 提交 TradeIntent 到 RiskRouter
   - 等待交易确认，记录 tx hash

5. **构建 Checkpoint**
   ```
   Checkpoint {
       agentId: uint256
       timestamp: uint256
       action: string
       pair: string
       amountUsdScaled: uint256
       priceUsdScaled: uint256
       reasoningHash: bytes32 (keccak256 of reasoning)
   }
   ```

6. **提交 Checkpoint**
   - 签署 Checkpoint（使用 AITradingAgent 域）
   - 提交哈希 + 评分（0-100）+ notes 到 ValidationRegistry
   - Notes 包括 action、confidence、reasoning 摘要

7. **事件监听**  
   - RiskRouter 发出 `TradeApproved` 或 `TradeRejected` 事件
   - 自动记录到日志

## 对现有 Agent 决策结构的限制

### Risk Engine 输出映射

Agent 的 final_trade_decision 包含：

```json
{
  "action": "BUY",               // 必需
  "confidence": 0.75,            // 必需
  "order": {
    "ticker": "WETH/USDC",       // → pair
    "side": "BUY",               // → action
    "notional_usd": 500.00,      // → amountUsdScaled (× 100)
    "risk_status": "allowed"
  },
  "reason": "Momentum signal confirmed"  // → checkpoint reasoning
}
```

### 映射规则

| Agent 字段 | TradeIntent 字段 | 转换 |
|-----------|-----------------|------|
| order.ticker | pair | 规范化（"WETH" → "WETH/USDC"） |
| action | action | 大写（BUY/SELL） |
| order.notional_usd | amountUsdScaled | × 100（美分） |
| confidence | notes | 作为百分比包含 |
| reason | reasoning (Checkpoint) | 作为推理哈希 |

### 不兼容情况处理

❌ **HOLD 订单**  
- 跳过链上提交（不提交交易意图）
- 仍然记录到日志

❌ **notional_usd = 0**  
- 跳过提交
- 日志记录原因

❌ **缺失 action/pair**  
- 跳过并记录错误
- 不影响本地决策

## 错误处理

### 交易意图失败

如果 `submitTradeIntent()` 失败：
- 日志记录交易哈希和错误信息
- Checkpoint 提交被跳过（防止孤立 Checkpoint）
- Analyzer 继续（不会中断 agent）

### Checkpoint 失败（非关键）

如果 `postCheckpoint()` 失败：
- 日志记录错误但不中断流程
- TradeIntent 已提交，Checkpoint 失败不影响链上状态

### RPC 连接错误

如果 RPC 端点不可达：
- 详细日志记录（连接拒绝、超时等）
- 整个链上提交被跳过
- Agent 继续本地决策过程

## 日志和调试

### 启用详细日志

```python
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)

# 特别是 on_chain_integration：
logging.getLogger('tradingagents.web3_layer.on_chain_integration').setLevel(logging.DEBUG)
```

### 预期输出

```
2026-04-08 10:30:45 - tradingagents.web3_layer.on_chain_integration - INFO - Submitting on-chain: action=BUY, pair=WETH/USDC, amount=500.00 USD
2026-04-08 10:30:48 - tradingagents.web3_layer.on_chain_integration - INFO - TradeIntent submitted: 0xabc123...
2026-04-08 10:30:55 - tradingagents.web3_layer.on_chain_integration - INFO - Checkpoint submitted: 0xdef456...
```

## 高级选项

### 自定义 Checkpoint 评分

默认评分为 75/100。可以通过创建自定义 OnChainIntegrator 更改：

```python
from tradingagents.web3_layer import OnChainIntegrator

integrator = OnChainIntegrator(
    web3_client=client,
    agent_id=123,
    agent_wallet="0x...",
    checkpoint_score=85,  # ← 自定义评分
)
```

### 禁用模拟

模拟会增加延迟。如果想跳过：

```python
config["on_chain_simulation_enabled"] = False
```

## 故障排除

### 错误："缺少必需的环境变量"

检查 .env 中的以下变量是否全部设置：
- `SEPOLIA_RPC_URL`
- `OPERATOR_PRIVATE_KEY`
- `AGENT_WALLET_PRIVATE_KEY`
- `AGENT_ID`
- `AGENT_WALLET`

### 错误："RiskRouter.simulateIntent() 失败"

可能原因：
- 余额不足（已花费 0.05 ETH 中的太多）
- 超过风险限制（$500/交易、10/小时、5% 缩水）
- 交易对无效（pair 格式不匹配）

**解决**：检查日志中的详细理由，或禁用模拟重试。

### 错误："交易确认超时"

Sepolia 有时很慢。增加超时时间：

```python
# tradingagents/web3_layer/client.py 中：
# 修改 wait_for_transaction_receipt() 的超时参数
```

## 合约限制提醒

所有 agents 共享相同的风险限制（在 RiskRouter 中）：

| 限制 | 值 |
|-----|---|
| 每笔交易最大仓位 | $500 USD |
| 每小时最大交易数 | 10 |
| 最大缩水 | 5% |

任何违反的交易都会被 RiskRouter 拒绝。

## 下一步

完成后，所有决策都将自动在链上原子记录。可以：

1. **监控声誉分数**：
   ```bash
   python web3_path_b.py scores
   ```

2. **查看链上活动**：  
   https://sepolia.etherscan.io/address/0xd6A6952545FF6E6E6681c2d15C59f9EB8F40FdBC

3. **收集本地 checkpoints**：  
   查看 `eval_results/{PAIR}/TradingAgentsStrategy_logs/` 中的日志

---

更多信息，见 [SHARED_CONTRACTS.md](./SHARED_CONTRACTS.md)
