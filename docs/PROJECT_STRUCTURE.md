# TradingAgents v0.2.1 项目结构说明

## 快速导航

```
TradingAgents-0.2.1/
├── tradingagents/          # 核心交易代理库
│   ├── agents/             # 交易员、分析员、风险管理器等
│   ├── graph/              # LangGraph 交易流程定义
│   ├── dataflows/          # 数据流处理（价格、新闻、指标等）
│   ├── llm_clients/        # LLM 客户端（OpenAI, Anthropic, Google）
│   └── ...
├── docs/                   # 文档和指南
│   ├── INTEGRATION_CHECKLIST.md
│   ├── REFACTORING_GUIDE.md
│   ├── IMPLEMENTATION_SUMMARY.md
│   └── scripts/            # 验证和工具脚本
├── examples/               # 使用示例
│   └── archived/           # 归档的过时示例
├── data/                   # 数据文件
│   └── crypto_news.db      # 新闻缓存数据库
├── trade_memory/           # 运行时数据（持久化）
│   ├── portfolio.db        # 投资组合和交易历史
│   └── chroma_data/        # 向量化语义记忆
├── eval_results/           # 评估结果（测试输出）
├── visualisation/          # 可视化资源（HTML仪表板）
├── cli/                    # 命令行界面
├── main.py                 # 主入口点
├── pyproject.toml          # 项目配置和依赖
├── requirements.txt        # Python 依赖（简化版）
├── validate_refactoring.py # 验证脚本（已移到 docs/scripts/）
└── ...

```

## 目录说明

### `tradingagents/` - 核心库代码
- **agents/** - 交易员角色定义
  - `analysts/` - 技术分析、新闻分析、量化分析
  - `managers/` - 投资组合和资金管理
  - `researchers/` - 牛市/熊市研究员
  - `trader/` - 交易执行
  - `risk_mgmt/` - 风险管理
  - `utils/memory.py` - 语义记忆接口（ChromaDB）

- **graph/** - LangGraph 工作流
  - `trading_graph.py` - 主图定义
  - `setup.py` / `parallel_setup.py` - 图拓扑配置
  - `context_merger.py` - 投资组合上下文注入
  - `reflection.py` - 交易后反思和记忆写入

- **dataflows/** - 数据处理管道
  - `geckoterminal_price.py` - 加密货币价格
  - `rss_processor.py` - 新闻RSS处理
  - `calculate_indicators.py` - 技术指标计算
  - `utils.py` - 缓存和工具函数

- **llm_clients/** - LLM 集成
  - `factory.py` - 客户端工厂
  - `anthropic_client.py` - Anthropic Claude API
  - `openai_client.py` - OpenAI API（用于DeepSeek兼容端点）
  - `validators.py` - 输出验证

### `docs/` - 文档和验证脚本
- **主文档**
  - `README.md` - 项目介绍（根目录）
  - `INTEGRATION_CHECKLIST.md` - 集成测试检查清单
  - `REFACTORING_GUIDE.md` - 重构指南
  - `IMPLEMENTATION_SUMMARY.md` - 实现总结
  - `QUICK_REFERENCE.md` - 快速参考
  - `BEFORE_AFTER.md` - 重构前后对比

- **scripts/**
  - `validate_refactoring.py` - 验证所有依赖和配置

### `examples/` - 使用示例
- `archived/` - 来自 unused_archive 的历史示例
- 可以添加新的示例用例

### `data/` - 数据文件
- 数据库文件（crypto_news.db 等）
- 应避免提交大型数据文件

### `trade_memory/` - 持久化运行时数据
- **portfolio.db** - SQLite 数据库
  - `portfolio_state` - 当前投资组合状态
  - `trade_history` - 历史交易记录
- **chroma_data/** - ChromaDB 对话和记忆
  - 包含多个向量集合（bull_memory, bear_memory, trader_memory等）

## 重要文件清单

| 文件 | 位置 | 用途 |
|------|------|------|
| `main.py` | 根目录 | 主程序入口 |
| `pyproject.toml` | 根目录 | 依赖和项目配置 |
| `requirements.txt` | 根目录 | Python 依赖列表 |
| `portfolio_manager.py` | `tradingagents/` | 投资组合持久化 |
| `default_config.py` | `tradingagents/` | 默认配置（模型、API等） |
| `INTEGRATION_CHECKLIST.md` | `docs/` | 测试和验证进度 |
| `.gitignore` | 根目录 | Git 忽略规则 |

## 已移除/归档的内容

### `unused_archive/`
历史代码和过时数据源：
- 旧的价格数据源（alpha_vantage, yfinance, dexscreener 等）
- 旧的新闻源（lunarcrush, cryptopanic, coinmarketcap 等）
- 历史实现和文档
- 已提取有用内容到 `examples/archived/`

### 生成的目录（git 忽略）
- `__pycache__/` - Python 编译缓存
- `tradingagents.egg-info/` - 包元数据
- `.venv/` - 虚拟环境

## 版本和历史记录

- **当前版本**：0.2.1
- **主要特性**：
  - 多代理交易系统（分析、评研、交易）
  - 双内存系统（向量化语义 + 结构化投资组合）
  - 动态投资组合上下文注入
  - LangGraph 并行执行
  - Kelly 公式头寸调整

## 下一步

1. **开发**: 在 `tradingagents/` 中添加新功能
2. **文档**: 更新 `docs/` 中的相关文档
3. **示例**: 添加新用例到 `examples/`
4. **测试**: 运行 `docs/scripts/validate_refactoring.py` 验证配置
5. **运行**: 执行 `python main.py` 启动交易代理

## 常见命令

```bash
# 验证配置和依赖
python docs/scripts/validate_refactoring.py

# 启动主程序
python main.py

# 列出所有已安装依赖
pip list

# 升级依赖
pip install -r requirements.txt --upgrade
```

---
*最后更新: 2026-03-30*
