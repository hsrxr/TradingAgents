"""
RISKROUTER FEEDBACK MECHANISM - QUICK START GUIDE

本文档说明如何使用新的RiskRouter反馈机制。
"""

# ============================================================================

# 1. 架构概览

# ============================================================================

"""
原有的一单向流程:
Agent决策 → 提交TradeIntent → 完成

新增的双向反馈循环:
Agent决策 → 提交TradeIntent → [等待RiskRouter回应]
↓
批准 or 拒绝?
↓        ↓
更新       记录
portfolio  rejection
↓
记录结果到
Agent Memory
(学习)
"""

# ============================================================================

# 2. 使用流程（自动集成到trading_graph.analyze()）

# ============================================================================

"""
当enable_on_chain_submission=True时，analyze()自动:

1. 生成Agent决策 (final_trade_decision)
2. 调用 submit_decision()
   ↓
   → TradeIntent签名 + RiskRouter提交
   → 返回 OnChainSubmissionResult (带txhash)
3. 新增: 调用 wait_for_feedback()
   ↓
   → 轮询RiskRouter事件 (5分钟超时)
   → 返回批准/拒绝结果
4. 新增: 调用 _apply_on_chain_feedback()
   ↓
   如果批准:
   a. apply_approved_trade() → 更新portfolio
   - 现金扣除/增加
   - 添加/修改position
   - 记录trade_history
   b. 记录到agent memory (学习)

   如果拒绝:
   a. apply_rejected_trade() → 记录拒绝理由
   - 不修改portfolio
   - 记录到trade_history
   b. 记录rejection_reason到agent memory
5. 返回 final_state
   """

# ============================================================================

# 3. 关键类和方法

# ============================================================================

# 3.1 TradeStatusChecker - 查询RiskRouter事件

# ════════════════════════════════════════════════════════════════════════════

"""
from tradingagents.web3_layer import create_trade_status_checker

# 初始化

checker = create_trade_status_checker(web3_client)

# 查询历史批准事件

approvals = checker.get_approval_events(agent_id=40)
for approval in approvals:
print(f"批准: {approval.intent_hash} @ block {approval.block_number}")

# 查询历史拒绝事件

rejections = checker.get_rejection_events(agent_id=40)
for rejection in rejections:
print(f"拒绝: {rejection.reason}")

# 阻塞式等待特定交易结果（自动轮询）

result = checker.poll_trade_result(
agent_id=40,
intent_hash="0xabcd1234...",
max_wait_seconds=300,           # 5分钟超时
poll_interval_seconds=5         # 每5秒查询一次
)

if result:
if result["status"] == "approved":
print(f"✓ 交易已批准: {result['event']}")
elif result["status"] == "rejected":
print(f"✗ 交易被拒绝: {result['reason']}")
else:
print("⏱ 超时未获得结果")
"""

# 3.2 PortfolioFeedbackEngine - 更新portfolio和trade_history

# ════════════════════════════════════════════════════════════════════════════

"""
from tradingagents.web3_layer import create_portfolio_feedback_engine

# 初始化

engine = create_portfolio_feedback_engine(portfolio_manager)

# 应用批准的交易

approval_event = {
"agent_id": 40,
"intent_hash": "0x...",
"amount_usd_scaled": 50000,  # $500 (USD的cents表示)
"transaction_hash": "0x...",
}

trade_intent = {
"action": "BUY",
"pair": "WETH/USDC",
"amountUsdScaled": 50000,
}

outcome = engine.apply_approved_trade(
approval_event=approval_event,
trade_intent=trade_intent,
execution_price_usd=1500.0,    # 可选: 实际成交价
execution_amount_filled=500.0  # 可选: 实际成交额
)

if outcome.success:
print(f"✓ {outcome.message}")
print(f"  前值cash: {outcome.previous_state['cash_usd']}")
print(f"  后值cash: {outcome.new_state['cash_usd']}")
else:
print(f"✗ {outcome.message}")

# 应用拒绝的交易

rejection_event = {
"agent_id": 40,
"intent_hash": "0x...",
"rejection_reason": "Exceeds maximum position size (20%)",
}

outcome = engine.apply_rejected_trade(
rejection_event=rejection_event,
trade_intent=trade_intent,
)

# 获取trade_history

history = engine.get_trade_history(limit=10)
for trade in history:
print(f"[{trade['timestamp']}] {trade['action']} {trade['pair']} "
f"@ {trade['status']}: {trade.get('rejection_reason', 'OK')}")
"""

# 3.3 TradeOutcomeRecorder - 记录到Agent内存

# ════════════════════════════════════════════════════════════════════════════

"""
from tradingagents.graph.trade_outcome_recorder import create_trade_outcome_recorder

# 初始化

recorder = create_trade_outcome_recorder()

# 记录批准的交易到特定agent的memory

success = recorder.record_approved_trade(
memory=bull_memory,
decision_state=final_state,
approval_event={...},
portfolio_outcome={...},
trade_date="2026-04-08T10:30:00",
)

# 或同时记录到所有agent memory

agent_memories = {
"bull": bull_memory,
"bear": bear_memory,
"trader": trader_memory,
"invest_judge": invest_judge_memory,
"risk_manager": risk_manager_memory,
}

results = recorder.record_trade_outcome_for_all_agents(
agent_memories=agent_memories,
decision_state=final_state,
approval_status="approved",
approval_event={...},
)

# 获取统计

stats = recorder.get_stats()
print(f"总交易记录数: {stats['total_trades_recorded']}")
"""

# 3.4 Trading Graph集成 - 自动化反馈循环

# ════════════════════════════════════════════════════════════════════════════

"""

# 在TradingAgentsGraph.analyze()中自动执行:

# 1. 提交决策

submission_result = self.on_chain_integrator.submit_decision(...)

# 2. 等待反馈（新增）

submission_result = self.on_chain_integrator.wait_for_feedback(
submission_result,
max_wait_seconds=300,
)

# 3. 应用反馈到portfolio和memory（新增）

self._apply_on_chain_feedback(
submission_result,
final_state,
trade_date,
)

# 用户无需手动调用这些方法，都是自动的！

"""

# ============================================================================

# 4. 配置

# ============================================================================

"""
在config.py或.env中设置:

enable_on_chain_submission=true          # 启用链上提交和反馈
on_chain_simulation_enabled=true         # 在RiskRouter中模拟交易(可选)
"""

# ============================================================================

# 5. 数据库表更新

# ============================================================================

"""
SQLite trade_history表新增字段:

- on_chain_hash: RiskRouter提交的tx hash
- intent_hash: TradeIntent hash
- rejection_reason: 拒绝理由(如果被拒绝)

exemplary row:
{
timestamp: "2026-04-08T10:30:00",
action: "BUY",
pair: "WETH/USDC",
quantity: 0.333,
price: 1500.0,
amount_usd: 500.0,
status: "approved",
on_chain_hash: "0x1234...",
intent_hash: "0x5678...",
rejection_reason: null
}
"""

# ============================================================================

# 6. Agent内存集成

# ============================================================================

"""
当交易被批准或拒绝时，结果自动存储到ChromaDB:

批准示例:
Memory entry: "Trade BUY WETH approved for 500 USD"
Metadata: {
approval_status: "approved",
trade_date: "2026-04-08T10:30:00",
on_chain: true
}

拒绝示例:
Memory entry: "Trade SELL WETH REJECTED: Exceeds risk limit"
Metadata: {
approval_status: "rejected",
rejection_reason: "Exceeds risk limit",
trade_date: "2026-04-08T10:31:00",
on_chain: true
}

这样Agent下次遇到类似情况时，可以通过语义搜索找到
历史记录，优化决策逻辑。
"""

# ============================================================================

# 7. 错误处理和降级

# ============================================================================

"""
场景1: Feedback超时 (5分钟内未获得结果)
└─ 处理: submission_result.metadata['feedback_timeout'] = True
可实现的降级:

- 假设批准，继续执行（乐观）
- 假设拒绝，回滚portfolio（保守）
- 人工介入，查询RiskRouter链上状态

场景2: RiskRouter离线/不可达
└─ 处理: exception捕获，logged但不block后续流程
可实现的降级:

- 重试(with exponential backoff)
- 异步后台重试
- 警告管理员

场景3: Portfolio更新失败
└─ 处理: TradeExecutionOutcome.success = False
可实现的降级:

- 记录失败但继续
- 记录异常到sentry/日志
- 管理员可通过手动SQL修复
  """

# ============================================================================

# 8. 完整流程示例

# ============================================================================

"""
用户执行:
graph = TradingAgentsGraph(...)
final_state, signal = graph.analyze(...)

TradingAgentsGraph内部自动:

Step 1: Agent分析 (bull, bear, quant等)
↓ 生成 final_trade_decision

Step 2: 链上提交 (OnChainIntegrator.submit_decision)
↓ TradeIntent → RiskRouter
↓ OnChainSubmissionResult (trade_intent_hash, checkpoint_hash)

Step 3: 等待反馈 (新增)
↓ TradeStatusChecker.poll_trade_result()
↓ 轮询RiskRouter事件，获得批准/拒绝

Step 4: 应用反馈 (新增)
├─ PortfolioFeedbackEngine
│  ├─ 批准: 更新cash, positions, trade_history
│  └─ 拒绝: 记录rejection_reason
│
└─ TradeOutcomeRecorder
└─ 所有5个agent memory记录结果

Step 5: 返回最终状态
↓ final_state (包含on_chain_feedback信息)
↓ processed signal

用户获得:
✓ final_state包含反馈结果
✓ portfolio已更新（若批准）
✓ trade_history已记录（批准/拒绝）
✓ agent memory已学习（ChromaDB）
"""

# ============================================================================

# 9. 监控和调试

# ============================================================================

"""
查看反馈处理日志:
logs:

- "Waiting for RiskRouter feedback..." (等待开始)
- "Trade APPROVED: 0xabcd..." (批准)
- "Trade REJECTED: Exceeds risk limit" (拒绝)
- "Trade REJECTED poll timeout" (超时)
- "Portfolio updated with approved trade: ..." (成功)
- "Rejection recorded: ..." (拒绝记录)

检查database:
SELECT * FROM trade_history WHERE status='approved' OR status='rejected';
SELECT * FROM portfolio_state ORDER BY id DESC LIMIT 1;

浏览ChromaDB:

# 直接查询Python

approvals = bull_memory.get_memories(
query="WETH SELL被拒绝",
metadata_filter={"approval_status": "rejected"}
)
"""

# ============================================================================

# 10. 常见问题

# ============================================================================

"""
Q: 如果poll_trade_result()超时怎么办？
A: 返回None，submission_result.metadata['feedback_timeout']=True
可实现降级策略（重试、乐观假设、等待）

Q: 如果RiskRouter拒绝但portfolio已经预留了资金怎样？
A: portfolio不会被修改，拒绝会被记录在database中
用户可以手动检查并撤销预留

Q: Agent memory中存储了拒绝原因，如何使用？
A: 下一轮Agent决策时通过semantic search:
similar = memory.get_memories(query="position size限制")
返回:[("历史拒绝","Exceeds position size"), ...]
Agent可据此优化风险参数

Q: 如何追踪一笔交易从提交到最终结果？
A: 使用intent_hash作为key

1. on_chain_integration中的trade_intent_hash
2. trade_history表中的intent_hash
3. RiskRouter事件中的intentHash
   这三处一致，可跟踪完整生命周期

Q: 如何手动查询某笔交易的状态？
A: from trading_agents.web3_layer import create_trade_status_checker
checker = create_trade_status_checker(web3_client)
approvals = checker.get_approval_events(agent_id=40)
rejections = checker.get_rejection_events(agent_id=40)
"""

# ============================================================================

# 11. 生产检查清单

# ============================================================================


部署前确认:
□ enable_on_chain_submission = true (if on Sepolia)
□ SEPOLIA_RPC_URL configured
□ OPERATOR_PRIVATE_KEY set
□ AGENT_WALLET_PRIVATE_KEY set
□ AGENT_ID matching registered agent
□ portfolio database initialized
□ chromadb directory exists (trade_memory/chromadb)
□ agent-id.json has valid claim.balanceEth
□ test_riskrouter_feedback.py all pass ✓

监控指标:
□ approval_rate: TradeApproved / TradeIntentSubmitted
□ rejection_rate: TradeRejected / TradeIntentSubmitted
□ feedback_timeout_rate: Timeouts / Total submissions
□ portfolio_update_success_rate: Successful updates / Total feedbacks
□ memory_recording_rate: Recorded / received feedbacks


# ============================================================================
