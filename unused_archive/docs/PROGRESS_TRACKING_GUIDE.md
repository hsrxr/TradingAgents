# Real-Time Progress Tracking 使用指南

## 概述

您现在可以在 TradingAgents 的执行过程中实时查看：
- **Agent 接收的提示词**（Prompts）
- **Agent 的相应输出**（Responses）
- **执行进度和时间统计**

## 功能特性

### 1. **实时进度显示**
- 每个节点执行时显示开始和结束时间
- 彩色输出便于快速识别不同阶段
- 执行时间统计和性能分析

### 2. **LLM 调用跟踪**
- 显示发送给 LLM 的完整或摘要提示词
- 显示 LLM 返回的响应
- 记录每个调用的执行时间

### 3. **性能分析**
- 按节点类型统计时间分布
- 识别最慢的节点（瓶颈分析）
- 总执行时间和调用次数统计

## 使用方法

### 方法 1: 在现有代码中启用

```python
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

# 创建配置，启用进度追踪
config = DEFAULT_CONFIG.copy()
config["enable_progress_tracking"] = True      # 启用进度追踪
config["enable_colored_output"] = True         # 启用彩色输出

# 创建图
ta = TradingAgentsGraph(
    selected_analysts=['market', 'news'],
    config=config,
    parallel_mode=False  # 或 True
)

# 执行分析 - 进度将实时显示
final_state, decision = ta.propagate("WETH/USDC", "2026-03-28")

# 获取 LLM 调用历史（JSON 格式）
llm_calls = ta.progress_tracker.get_llm_calls_json()
```

### 方法 2: 使用演示脚本

我们提供了两个演示脚本：

#### a) 快速演示（推荐）
```bash
python progress_tracking_demo.py
```

**输出示例：**
```
▶ [2026-03-28 10:30:45] ANALYST         Market Analyst
   Processing market data...
✓ Market Analyst completed in 12.34s

▶ [2026-03-28 10:30:57] ANALYST         News Analyst  
   Processing news data...
✓ News Analyst completed in 8.56s

📊 EXECUTION SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Time by Node Type:
  analyst              20.90s (65.2%)
  tool                 10.45s (32.5%)
  debate                0.75s  (2.3%)

Total Execution Time: 32.10s
Total LLM Calls: 8
```

#### b) 完整对比脚本
```bash
python parallel_execution_example.py
```

这个脚本会：
- 先以串行模式运行 2 个分析师
- 再以并行模式运行 4 个分析师
- 显示性能对比和加速倍数

## 配置选项

### default_config.py

```python
DEFAULT_CONFIG = {
    # ... 其他配置 ...
    
    # 进度追踪设置
    "enable_progress_tracking": True,   # 启用/禁用进度显示
    "enable_colored_output": True,      # 启用/禁用彩色输出
}
```

### 在运行时修改

```python
config = DEFAULT_CONFIG.copy()

# 关闭进度追踪（用于编程集成）
config["enable_progress_tracking"] = False

# 禁用彩色输出（用于日志文件）
config["enable_colored_output"] = False
```

## 输出说明

### 节点类型颜色编码

| 节点类型 | 颜色 | 用途 |
|---------|------|------|
| ANALYST | 青色 | 数据分析阶段 |
| TOOL | 黄色 | 工具调用 |
| DEBATE | 品红 | 投资辩论 |
| RISK | 红色 | 风险管理 |
| TRADER | 绿色 | 交易决策 |

### 输出符号

- `▶` 节点开始
- `✓` 节点完成
- `📝` LLM 提示词
- `📤` LLM 响应
- `📊` 分析报告
- `⚠️` 警告信息
- `❌` 错误信息

## 实际应用例子

### 例 1: 基础使用

```python
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

config = DEFAULT_CONFIG.copy()
config["enable_progress_tracking"] = True

ta = TradingAgentsGraph(
    selected_analysts=['market', 'news'],
    config=config
)

# 执行时会看到实时进度
final_state, decision = ta.propagate("WETH/USDC", "2026-03-28")
```

### 例 2: 保存进度日志

```python
from tradingagents.graph.progress_tracker import ProgressTracker
import json

ta = TradingAgentsGraph(config=config)
final_state, decision = ta.propagate("WETH/USDC", "2026-03-28")

# 获取 LLM 调用历史
llm_calls = ta.progress_tracker.get_llm_calls_json()

# 保存到文件
with open("llm_calls.json", "w") as f:
    json.dump(llm_calls, f, indent=2)

# 保存执行摘要
with open("execution_summary.txt", "w") as f:
    f.write(f"Total nodes executed: {len(ta.progress_tracker.node_history)}\n")
    f.write(f"Total LLM calls: {len(llm_calls)}\n")
```

### 例 3: 性能分析

```python
ta = TradingAgentsGraph(config=config)
final_state, decision = ta.propagate("WETH/USDC", "2026-03-28")

# 显示执行摘要
ta.progress_tracker.print_summary()

# 找出最慢的 5 个节点
slow_nodes = sorted(
    ta.progress_tracker.node_history,
    key=lambda x: x.get('duration', 0),
    reverse=True
)[:5]

print("Top 5 slowest nodes:")
for node in slow_nodes:
    print(f"  {node['name']}: {node.get('duration', 0):.2f}s")
```

## 故障排除

### Q: 为什么看不到进度信息？
**A:** 检查以下几点：
1. `config["enable_progress_tracking"]` 是否为 `True`
2. 日志级别是否设置为 `INFO` 或更低
3. 是否使用了 `debug=True` 模式（该模式会输出更详细的信息）

### Q: 为什么没有颜色输出？
**A:** 
1. 检查 `config["enable_colored_output"]` 是否为 `True`
2. 在某些终端（如 VS Code 集成终端）中，可能需要更新设置
3. 如果在文件输出中，颜色代码会被保留（可以用文本编辑器查看）

### Q: 如何以编程方式处理进度数据？
**A:** 使用 `progress_tracker.get_llm_calls_json()` 获取 JSON 格式的数据：
```python
llm_calls = ta.progress_tracker.get_llm_calls_json()
for call in llm_calls:
    print(f"{call['analyst']}: {call['duration']:.2f}s")
```

## 性能建议

### 串行 vs 并行的进度显示

**串行模式：**
- 适合快速理解 Agent 的思考过程
- 清晰显示每个分析师的个体逻辑
- 总时间 = 所有分析师的时间之和

**并行模式：**
- 分析师同时执行，总时间更短
- 进度显示会交错（正常现象）
- 适合性能敏感的应用

### 优化建议

1. **若要识别瓶颈：**
   - 运行 `progress_tracker.print_summary()`
   - 查看 "Time by Node Type" 部分
   - 关注占比最高的节点

2. **若要改进性能：**
   - 对于少于 3 个分析师，使用串行模式
   - 复用数据缓存以减少 API 调用
   - 考虑使用更快的 LLM 模型（如果准确性允许）

## 相关文件

- `tradingagents/graph/progress_tracker.py` - 核心实现
- `tradingagents/graph/trading_graph.py` - 集成点
- `tradingagents/default_config.py` - 配置定义
- `progress_tracking_demo.py` - 快速演示
- `parallel_execution_example.py` - 完整对比演示

## 后续扩展

未来可能的增强功能：
- 导出到 HTML 格式的可视化报告
- 与外部监控系统集成（如 Prometheus）
- Web UI 实时仪表板
- 自动性能优化建议
