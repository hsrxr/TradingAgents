## 项目结构快速导航 🗂️

### 📄 常用文件位置

#### 项目配置 (根目录)
- `main.py` - 主程序入口
- `pyproject.toml` - 项目和依赖配置
- `requirements.txt` - Python 依赖列表
- `README.md` - 项目介绍

#### 📚 文档 → 查看 `docs/` 目录
| 文档 | 说明 |
|------|------|
| `PROJECT_STRUCTURE.md` | 📍 项目组织详细说明（从这里开始） |
| `CLEANUP_SUMMARY.md` | 最近的整理工作总结 |
| `INTEGRATION_CHECKLIST.md` | 集成测试和验证清单 |
| `REFACTORING_GUIDE.md` | 详细的重构实现指南 |
| `IMPLEMENTATION_SUMMARY.md` | 功能实现总结 |
| `QUICK_REFERENCE.md` | 快速参考和常用命令 |

#### 🔧 验证和脚本
```bash
python docs/scripts/validate_refactoring.py    # 验证项目配置和依赖
```

#### 💾 数据和缓存
- `data/` - 数据文件（crypto_news.db等）
- `trade_memory/` - 运行时数据（投资组合、交易历史）
  - `portfolio.db` - SQLite 数据库
  - `chroma_data/` - 向量化记忆数据

#### 📊 工具和示例
- `examples/archived/` - 历史示例代码
- `visualisation/` - 仪表板和可视化
- `cli/` - 命令行工具

#### 📦 核心代码
- `tradingagents/` - 主库代码
  - `agents/` - 交易代理
  - `graph/` - LangGraph 工作流
  - `dataflows/` - 数据处理
  - `llm_clients/` - LLM 集成

### 🚀 常用命令

```bash
# 启动交易代理
python main.py

# 验证项目配置
python docs/scripts/validate_refactoring.py

# 查看依赖
pip list

# 查看详细的项目结构
cat docs/PROJECT_STRUCTURE.md
```

### 🗂️ 完整目录树
```
TradingAgents-0.2.1/
├── 📁 tradingagents/        # 核心库
├── 📁 cli/                  # 命令行工具
├── 📁 docs/**               # 📍 所有文档
├── 📁 data/**               # 📍 数据文件
├── 📁 examples/             # 使用示例
├── 📁 trade_memory/         # 运行时数据
├── 📁 eval_results/         # 评估结果
├── 📁 visualisation/        # 仪表板
├── 📄 main.py               # 主入口
├── 📄 pyproject.toml        # 项目配置
└── 📄 README.md             # 项目说明
```

---

**💡 提示**: 第一次了解项目？请先查看 `docs/PROJECT_STRUCTURE.md`
