# 精简架构测试方案

## 验证状态 ✓

已验证：
- ✓ 模块导入成功
- ✓ 配置加载正确（market/news 默认分析师，20% 最大头寸，10% 最大订单）
- ✓ 语法检查通过（所有 11 个修改文件）
- ✓ 图结构编译成功

## 根据你的环境选择测试脚本

### 推荐：轻量级验证（无需 API 密钥）
```bash
python tests/test_progress_tracking_simple.py
```
- ✓ **无需 API 密钥**
- 验证进度追踪和日志系统
- 运行时间：<5秒

### 方案 A：完整测试（需要 DeepSeek API）
```bash
export DEEPSEEK_API_KEY=sk_xxxxx
# 或：
set DEEPSEEK_API_KEY=sk_xxxxx  # Windows PowerShell
python main.py
```
- 使用 DeepSeek 模型
- 实时执行 WETH/USDC 分析
- 包含完整的 2 分析师 + 2 回合辩论 + 风险引擎流程

### 方案 B：完整测试（需要 OpenAI API）
```bash
export OPENAI_API_KEY=sk-xxxxx
# 或：
set OPENAI_API_KEY=sk-xxxxx  # Windows PowerShell
python main.py
```
- 使用 OpenAI 模型
- 同方案 A，但用 GPT 而非 DeepSeek

### 方案 C：并行执行演示（需要 API 密钥）
```bash
export DEEPSEEK_API_KEY=sk_xxxxx  # 或 OPENAI_API_KEY
python examples/parallel_execution_example.py
```
- 演示市场分析师和新闻分析师并行运行
- 对比序列 vs 并行性能

### 方案 D：进度追踪演示（需要 API 密钥）
```bash
export DEEPSEEK_API_KEY=sk_xxxxx  # 或 OPENAI_API_KEY
python examples/progress_tracking_demo.py
```
- 实时查看 Agent 的提示词和输出
- 展示进度追踪系统工作情况

## 目前已经改动了什么

```
原架构：
  Input → [Market, News, Social, Fundamentals] → Research Manager 
       → [Bull, Bear, Neutral] → Risk Judge → [3个风险分析师] → END

新架构（精简）：
  Input → [Market, News] (并行) → Context Merge → [Bull, Bear] (max 2轮)
       → Chief Trader (JSON 输出) → Risk Engine (纯 Python) → Executable Order
```

## 关键改动清单

| 文件 | 改动 | 影响 |
|------|------|------|
| `setup.py` | 移除 4 个分析师，加入 Context Merge | 只用 market/news |
| `parallel_setup.py` | 同上，保留并行执行 | 并行加速 |
| `conditional_logic.py` | 辩论最多 2 轮 | 速度更快 |
| `trader.py` | 改为 Chief Trader，强制 JSON | 输出确定性 |
| `risk_engine.py` | **新建** - 纯 Python 风险控制 | 无 LLM 延迟 |
| `default_config.py` | 加入 max_position_pct, max_single_order_pct | 配置风险参数 |

## 如果遇到错误

### 错误：`ModuleNotFoundError: No module named 'tradingagents'`
→ 先运行：`pip install -e .`

### 错误：`OPENAI_API_KEY environment variable not set`
→ 改用其他脚本 或 设置环境变量：
```bash
# Linux/Mac
export OPENAI_API_KEY=sk-xxx

# Windows PowerShell
$env:OPENAI_API_KEY="sk-xxx"

# Windows CMD
set OPENAI_API_KEY=sk-xxx
```

### 错误：`module 'anthropic' has no attribute 'Anthropic'`
→ 更新依赖：`pip install --upgrade anthropic`

## 下一步建议

1. **首先**：运行轻量级验证
   ```bash
   python tests/test_progress_tracking_simple.py
   ```

2. **然后**：根据有无 API 密钥选择：
   - ✓ 有 API 密钥 → 运行 `python main.py`
   - ✗ 无 API 密钥 → 仍可运行轻量级测试验证系统可靠性

3. **最后**：如需进一步优化：
   - 参数化风险规则（当前硬编码）
   - 集成 ERC-8004 订单签名
   - 添加历史回测模块
