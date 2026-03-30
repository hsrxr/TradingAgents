# 如何运行项目脚本

## 📋 目录结构说明

项目文件已重新组织：
```
TradingAgents-0.2.1/
├── examples/           # 演示脚本
├── tests/              # 测试脚本
├── docs/               # 文档
├── scripts/            # 工具脚本
├── main.py             # 主程序
└── tradingagents/      # 核心框架
```

## 🚀 运行脚本

### 从根目录运行（推荐）

```bash
# 进度追踪演示
python examples/progress_tracking_demo.py

# 并行执行演示  
python examples/parallel_execution_example.py

# 快速测试
python tests/test_progress_tracking_simple.py

# 完整测试
python tests/test_trading_agents.py

# 工具脚本
python scripts/reset_error_articles.py

# 主程序
python main.py
```

### 从任何目录运行

确保已安装项目：
```bash
pip install -e .
```

然后可以设置系统路径：
```bash
# Windows PowerShell
$env:PYTHONPATH = "D:\11150\vscode\project\erc8004-ai-trading-agent\Tradingagent\TradingAgents-0.2.1"

# Windows CMD
set PYTHONPATH=D:\11150\vscode\project\erc8004-ai-trading-agent\Tradingagent\TradingAgents-0.2.1

# Linux/Mac
export PYTHONPATH=/path/to/TradingAgents-0.2.1
```

## 📁 常见脚本说明

### 演示脚本 (`examples/`)

#### `progress_tracking_demo.py`
**用途**: 展示进度追踪功能

```bash
python examples/progress_tracking_demo.py
```

**输出内容**:
- 实时进度显示
- Agent 提示词和响应
- 执行时间统计
- LLM 调用历史

#### `parallel_execution_example.py`
**用途**: 对比串行和并行性能

```bash
python examples/parallel_execution_example.py
```

**对比内容**:
- 串行模式 (2 分析师)
- 并行模式 (4 分析师)
- 速度提升倍数
- 性能分析

### 测试脚本 (`tests/`)

#### `test_progress_tracking_simple.py` ✅ 推荐先运行
**快速验证进度追踪功能**

```bash
python tests/test_progress_tracking_simple.py
```

**验证内容**:
- [✓] 导入检查
- [✓] 基本方法
- [✓] 数据导出

#### `test_parallel_execution.py`
**单元测试并行执行**

```bash
python tests/test_parallel_execution.py
```

#### `test_trading_agents.py`
**整体功能测试**

```bash
python tests/test_trading_agents.py
```

### 工具脚本 (`scripts/`)

#### `reset_error_articles.py`
**重置出错的文章缓存**

```bash
python scripts/reset_error_articles.py
```

### 主程序 (`main.py`)
**执行交易分析**

```bash
python main.py
```

## 🔧 VS Code 集成

### 快速运行配置

在 VS Code 中按 `Ctrl+Shift+D` 调试，或在 `launch.json` 中添加：

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Progress Tracking Demo",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/examples/progress_tracking_demo.py",
      "console": "integratedTerminal",
      "justMyCode": true
    },
    {
      "name": "Test Progress Tracking",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/tests/test_progress_tracking_simple.py",
      "console": "integratedTerminal",
      "justMyCode": true
    }
  ]
}
```

### Terminal 快捷方式

在 `.vscode/settings.json` 中添加：

```json
{
  "terminal.integrated.tasks.slowTask": {
    "commands": [
      // 快速命令
    ]
  }
}
```

## 📊 典型工作流

### 1️⃣ 初次运行
```bash
# 验证安装
python tests/test_progress_tracking_simple.py

# 查看演示
python examples/progress_tracking_demo.py
```

### 2️⃣ 开发和测试
```bash
# 修改代码后运行测试
python tests/test_parallel_execution.py

# 查看进度追踪效果
python examples/progress_tracking_demo.py
```

### 3️⃣ 完整分析
```bash
# 运行主程序
python main.py

# 或通过 API 使用
python -c "
from tradingagents.graph.trading_graph import TradingAgentsGraph
ta = TradingAgentsGraph(config={'enable_progress_tracking': True})
result = ta.propagate('WETH/USDC', '2026-03-28')
"
```

## 🐛 常见问题

### 问: 导入错误 ModuleNotFoundError: No module named 'tradingagents'

**答**: 确保从根目录运行，或设置 PYTHONPATH：
```bash
cd /path/to/TradingAgents-0.2.1
set PYTHONPATH=%CD%
python examples/progress_tracking_demo.py
```

### 问: 找不到 .env 文件

**答**: 在项目根目录创建 `.env` 文件：
```
OPENAI_API_KEY=sk-...
DEEPSEEK_API_KEY=sk-...
```

### 问: 脚本超时

**答**: 检查网络连接和 API 密钥，或增加超时：
```python
config["llm_timeout_seconds"] = 300  # 增加到 300 秒
```

## 📝 编辑脚本建议

### 添加新示例

在 `examples/` 中创建新脚本：
```python
# examples/my_example.py
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

config = DEFAULT_CONFIG.copy()
config["enable_progress_tracking"] = True

ta = TradingAgentsGraph(config=config)
result = ta.propagate("WETH/USDC", "2026-03-28")
```

运行：
```bash
python examples/my_example.py
```

---

**提示**: 所有脚本都支持在任何目录运行，只需确保 PYTHONPATH 正确设置！
