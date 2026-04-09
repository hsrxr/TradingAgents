# 🚀 快速启动指南：自动链上提交

已完成 **链上自动化集成**。以下是快速启动步骤。

## ⚡ 5分钟启动

### 1️⃣ 前置条件（已完成）

```bash
✅ AgentRegistry.register() 注册 → 获得 agentId
✅ HackathonVault.claimAllocation() 领取 0.05 ETH
```

### 2️⃣ 配置 `.env`

从 `.env.example_on_chain` 复制并填充：

```bash
# 核心配置
SEPOLIA_RPC_URL=https://ethereum-sepolia-rpc.publicnode.com
OPERATOR_PRIVATE_KEY=0x<你的操作者私钥>
AGENT_WALLET_PRIVATE_KEY=0x<你的代理钱包私钥>
AGENT_ID=<你的 agentId，例如 123>
AGENT_WALLET=0x<你的代理钱包地址>

# LLM 配置（如果还没有）
LLM_PROVIDER=openai
DEEP_THINK_LLM=gpt-4-turbo
QUICK_THINK_LLM=gpt-4-turbo
OPENAI_API_KEY=sk-...
```

### 3️⃣ 启用链上提交

编辑 `trigger_main.py` 或 `main.py`：

```python
config = DEFAULT_CONFIG.copy()
config["enable_on_chain_submission"] = True  # ← 加这一行
```

### 4️⃣ 运行

```bash
# 选项 A：运行示例脚本（推荐新手）
python example_on_chain_integration.py

# 选项 B：运行既有流程
python trigger_main.py

# 选项 C：持续监听（需配置 trigger_main.py）
python -m cli.main analyze
```

### 5️⃣ 查看日志

```
2026-04-08 10:30:48 - tradingagents.web3_layer.on_chain_integration - INFO - Submitting on-chain: action=BUY, pair=WETH/USDC, amount=500.00 USD
2026-04-08 10:30:50 - tradingagents.web3_layer.on_chain_integration - INFO - TradeIntent submitted: 0x1234abcd...
2026-04-08 10:30:55 - tradingagents.web3_layer.on_chain_integration - INFO - Checkpoint submitted: 0x5678efgh...
```

✅ **完毕！** TradeIntent 和 Checkpoint 现已自动提交。

---

## 📁 新增和修改的文件

### 新增
- `tradingagents/web3_layer/on_chain_integration.py` — 核心集成模块
- `ON_CHAIN_INTEGRATION.md` — 完整文档
- `ON_CHAIN_INTEGRATION_SUMMARY.md` — 实现总结
- `.env.example_on_chain` — 环境变量模板
- `example_on_chain_integration.py` — 可运行示例

### 修改
- `tradingagents/graph/trading_graph.py` — 添加导入和集成代码
- `tradingagents/web3_layer/__init__.py` — 导出新类
- `README.md` — 添加自动化说明章节

---

## 🔄 工作流

```
Agent 决策 (BUY/SELL/HOLD)
    ↓
自动解析并构建 TradeIntent
    ↓
可选：链上模拟 (RiskRouter.simulateIntent)
    ↓
EIP-712 签名 + 提交到 RiskRouter
    ↓
构建 Checkpoint (action + reasoning + confidence)
    ↓
提交 Checkpoint 到 ValidationRegistry
    ↓
✅ 完成（TradeApproved / TradeRejected）
```

**关键点**：
- ✅ HOLD 订单自动跳过
- ✅ 零金额订单自动跳过
- ✅ 失败非阻塞（Checkpoint 失败不影响整体）
- ✅ 完全向后兼容（disable 配置即可关闭）

---

## ❓ 常见问题

### Q: 需要修改 Agent 代码吗？
**A**: 不需要。自动适配现有 `final_trade_decision` JSON。

### Q: 如果 Checkpoint 提交失败怎么办？
**A**: TradeIntent 已成功提交到链，Checkpoint 的失败不影响。可以稍后手动提交：
```bash
python web3_path_b.py post-checkpoint \
  --agent-id 123 \
  --action BUY \
  --pair WETH/USDC \
  --amount-usd 500 \
  --reasoning "Momentum signal"
```

### Q: 可以禁用模拟来加速吗？
**A**: 可以，在配置中设置：
```python
config["on_chain_simulation_enabled"] = False
```

### Q: 链接断了怎么办？
**A**: 安全失败。Agent 继续本地决策，链上提交失败只会被记录。

---

## 📚 下一步

1. **监控链上活动**  
   https://sepolia.etherscan.io/address/0xd6A6952545FF6E6E6681c2d15C59f9EB8F40FdBC

2. **查询声誉分数**
   ```bash
   python web3_path_b.py scores --agent-id 123
   ```

3. **查看本地日志**
   ```bash
   cat eval_results/WETH/USDC/TradingAgentsStrategy_logs/full_states_log_*.json
   ```

4. **阅读详细文档**
   - [ON_CHAIN_INTEGRATION.md](./ON_CHAIN_INTEGRATION.md) — 完整配置指南
   - [ON_CHAIN_INTEGRATION_SUMMARY.md](./ON_CHAIN_INTEGRATION_SUMMARY.md) — 实现细节
   - [SHARED_CONTRACTS.md](./SHARED_CONTRACTS.md) — 合约 ABI 和地址

---

## 🆘 故障排除

| 问题 | 原因 | 解决方案 |
|------|------|--------|
| "缺少环境变量" | .env 不完整 | 检查 SEPOLIA_RPC_URL, OPERATOR_PRIVATE_KEY 等 |
| "Cannot connect to RPC" | RPC 端点下线 | 更换公共 RPC 端点 |
| "Simulation failed" | 超出风险限制 | 检查提交的金额、频率、缩水 |
| "Transaction failed" | Gas 不足 | 确保有足够的 ETH 支付 gas |
| 无日志输出 | on_chain_submission 未启用 | config["enable_on_chain_submission"] = True |

---

## ✅ 验证清单

- [ ] `.env` 配置完整
- [ ] `enable_on_chain_submission = True`
- [ ] AgentID 和 钱包地址正确
- [ ] 有足量 ETH 支付 gas (约 0.001 ETH/交易)
- [ ] 运行 `python example_on_chain_integration.py` 看到日志
- [ ] 在 Etherscan 上看到 TradeIntent 和 Checkpoint 交易

---

**🎉 准备就绪！开始自动化链上提交吧！**
