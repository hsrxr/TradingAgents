# 快速开始：实时进度追踪

## 最简单的使用方式

### 步骤 1: 运行演示脚本
```bash
python progress_tracking_demo.py
```

这将显示实时的：
- 📝 Agent 接收的提示词
- 📤 Agent 的响应
- ⏱️ 每个步骤的执行时间
- 📊 性能摘要

### 步骤 2: 在您的代码中启用

```python
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

# 启用进度追踪
config = DEFAULT_CONFIG.copy()
config["enable_progress_tracking"] = True

# 创建并运行
ta = TradingAgentsGraph(selected_analysts=['market', 'news'], config=config)
final_state, decision = ta.propagate("WETH/USDC", "2026-03-28")

# 查看执行摘要
ta.progress_tracker.print_summary()
```

## 新增文件

| 文件 | 说明 |
|------|------|
| `tradingagents/graph/progress_tracker.py` | 进度追踪核心实现 |
| `progress_tracking_demo.py` | 快速演示脚本 |
| `PROGRESS_TRACKING_GUIDE.md` | 完整使用指南 |

## 修改的文件

| 文件 | 修改内容 |
|------|---------|
| `tradingagents/graph/trading_graph.py` | 集成 ProgressTracker |
| `tradingagents/default_config.py` | 添加追踪配置选项 |
| `parallel_execution_example.py` | 增强输出和日志 |

## 关键特性

✅ **实时提示词显示** - 看到发送给 LLM 的确切提示  
✅ **响应跟踪** - 查看 LLM 返回的内容  
✅ **时间测量** - 精确的执行时间统计  
✅ **彩色输出** - 便于快速识别和理解流程  
✅ **性能分析** - 自动识别瓶颈  
✅ **JSON 导出** - 编程方式访问数据  

## 常见命令

```bash
# 运行演示（推荐首先尝试）
python progress_tracking_demo.py

# 对比串行和并行性能
python parallel_execution_example.py

# 在 Python 脚本中使用
python -c "
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

config = DEFAULT_CONFIG.copy()
config['enable_progress_tracking'] = True
ta = TradingAgentsGraph(config=config)
ta.progress_tracker.print_summary()
"
```

## 查看详细信息

完整的使用指南请参考 `PROGRESS_TRACKING_GUIDE.md`

---

**提示：** 进度追踪可以在串行和并行模式下工作，帮助您理解系统的执行流程！
