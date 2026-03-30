# 项目结构说明

## 📁 目录组织

```
TradingAgents-0.2.1/
├── README.md                      # 项目说明（保留在根目录）
├── LICENSE                        # 许可证
├── pyproject.toml                 # Python 项目配置
├── requirements.txt               # 依赖列表
│
├── main.py                        # 主入口点 - 执行交易分析
├── todo.md                        # 待办事项
│
├── docs/                          # 📚 文档目录
│   ├── README.md                  # 完整使用指南
│   ├── PARALLEL_ARCHITECTURE.md   # 并行架构设计文档
│   ├── PROGRESS_TRACKING_GUIDE.md # 进度追踪完整指南
│   ├── IMPLEMENTATION_SUMMARY.md  # 实现总结
│   ├── QUICK_REFERENCE.md         # 快速参考
│   └── ...其他文档
│
├── examples/                      # 🎯 示例脚本
│   ├── parallel_execution_example.py      # 并行执行演示（4分析师对比）
│   └── progress_tracking_demo.py          # 进度追踪演示（实时显示）
│
├── tests/                         # ✅ 测试脚本
│   ├── test_trading_agents.py             # 基础测试
│   ├── test_parallel_execution.py         # 并行执行单元测试
│   ├── test_progress_tracking.py          # 进度追踪完整测试
│   └── test_progress_tracking_simple.py   # 进度追踪快速验证
│
├── scripts/                       # 🔧 工具脚本
│   └── reset_error_articles.py            # 重置错误文章缓存
│
├── tradingagents/                 # 🤖 核心框架
│   ├── graph/
│   │   ├── trading_graph.py       # 主图编排器
│   │   ├── setup.py               # 串行图设置
│   │   ├── parallel_setup.py      # 并行图设置
│   │   ├── progress_tracker.py    # 实时进度追踪 ✨ (新增)
│   │   ├── conditional_logic.py   # 路由逻辑
│   │   ├── propagation.py         # 图执行传播
│   │   ├── reflection.py          # 反思器
│   │   └── signal_processing.py   # 信号处理
│   ├── agents/
│   │   ├── analysts/              # 数据分析师
│   │   ├── managers/              # 管理器
│   │   ├── researchers/           # 研究员
│   │   ├── risk_mgmt/             # 风险管理
│   │   ├── trader/                # 交易执行
│   │   └── utils/                 # 工具函数
│   ├── dataflows/                 # 数据流
│   ├── llm_clients/               # LLM 客户端
│   └── default_config.py          # 默认配置
│
├── cli/                           # 命令行界面
├── assets/                        # 资源文件
├── results/                       # 📊 执行结果
├── eval_results/                  # 评估结果
├── visualisation/                 # 可视化
│
└── .env                           # 环境变量（本地）
```

## 📖 快速导航

### 🚀 快速开始
1. **查看示例**: `examples/progress_tracking_demo.py`
2. **运行演示**: `python examples/progress_tracking_demo.py`
3. **查看文档**: `docs/PROGRESS_TRACKING_QUICK_START.md`

### 📚 学习资源
| 文档 | 用途 |
|------|------|
| `docs/PROGRESS_TRACKING_GUIDE.md` | 进度追踪完整指南 |
| `docs/PARALLEL_ARCHITECTURE.md` | 并行执行架构 |
| `docs/IMPLEMENTATION_SUMMARY.md` | 实现总结 |
| `docs/QUICK_REFERENCE.md` | 快速参考 |

### ✅ 测试和验证
```bash
# 快速验证进度追踪
python tests/test_progress_tracking_simple.py

# 运行完整测试套件
python tests/test_trading_agents.py

# 对比并行和串行性能
python examples/parallel_execution_example.py

# 查看实时进度
python examples/progress_tracking_demo.py
```

### 🎯 使用示例
```bash
# 执行主程序
python main.py

# 运行特定测试
python tests/test_parallel_execution.py

# 重置缓存
python scripts/reset_error_articles.py
```

## 🔑 核心模块

### 交易图核心 (`tradingagents/graph/`)
- **trading_graph.py** - 主编排器，集成所有组件
- **parallel_setup.py** - 并行执行框架
- **progress_tracker.py** - 实时进度追踪 ✨ (最新)
- **conditional_logic.py** - 路由决策逻辑

### LLM 集成 (`tradingagents/llm_clients/`)
- OpenAI 兼容的 API 支持
- DeepSeek 接入
- 自动重试和故障转移

### 数据流 (`tradingagents/dataflows/`)
- Alpha Vantage 集成
- Yahoo Finance 数据源
- 技术指标计算
- 新闻源处理

## ⚙️ 配置管理

**默认配置**: `tradingagents/default_config.py`

关键配置项：
```python
# 并行执行
"parallel_mode": False/True,

# 进度追踪
"enable_progress_tracking": True,
"enable_colored_output": True,

# 性能调优
"llm_timeout_seconds": 180.0,
"llm_max_retries": 5,
"graph_invoke_retries": 3,
```

## 🎯 工作流程

### 标准分析流程
1. 初始化 `TradingAgentsGraph`
2. 运行 `propagate(ticker, date)`
3. 获取分析结果和交易决策

### 启用进度追踪
```python
config["enable_progress_tracking"] = True
ta = TradingAgentsGraph(config=config)
# 执行时会实时显示进度
```

## 📊 项目统计

| 组件 | 文件数 | 代码行数 |
|------|--------|---------|
| 核心框架 | 8 | ~3000 |
| 数据分析师 | 4 | ~2000 |
| 数据流 | 15+ | ~4000 |
| 进度追踪 | 1 | ~440 |
| 文档 | 8+ | ~1500 |
| 测试 | 4 | ~500 |
| 示例 | 2 | ~200 |

## 🔄 更新历史

### v0.2.1 最新更新
- ✨ **进度追踪系统** - 实时显示 agent 提示词和输出
- 🚀 **改进的并行执行** - 优化性能和错误处理
- 📊 **性能分析工具** - 自动识别瓶颈
- 📁 **项目重组** - 更清晰的目录结构

## 🤝 贡献指南

### 添加新的分析师
1. 在 `tradingagents/agents/analysts/` 中创建新文件
2. 继承 `BaseAnalyst` 并实现 `analyze()` 方法
3. 在 `tradingagents/agents/__init__.py` 中注册

### 添加新的数据源
1. 在 `tradingagents/dataflows/` 中创建新模块
2. 实现数据获取和处理逻辑
3. 在配置中添加支持

## 📞 获取帮助

- 查看文档: `docs/` 目录
- 运行示例: `examples/` 目录
- 查看测试: `tests/` 目录
- 参考快速开始: `docs/PROGRESS_TRACKING_QUICK_START.md`

---

**最后更新**: 2026-03-28  
**项目版本**: 0.2.1
