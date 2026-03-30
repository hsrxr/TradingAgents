# 项目文件和 Git 管理指南

## 📋 概述

本指南说明如何正确管理项目中的敏感文件、配置和数据，以确保仓库的安全性和清晰性。

## 🔒 安全文件管理

### 永远不应提交到 Git 的文件

| 文件/目录 | 原因 | 说明 |
|---------|------|------|
| `.env` | 🔐 包含 API 密钥 | 使用 `.env.example` 作为模板 |
| `trade_memory/` | 💾 个人交易数据 | 本地生成的投资组合和交易历史 |
| `*.db` 数据库文件 | 📦 大型二进制数据 | 运行时生成，可由另一端重建 |
| `.venv/` 虚拟环境 | 🔧 环境特定 | 通过 `requirements.txt` 重建 |
| `.idea/`, `.vscode/` | ⚙️ IDE 配置 | 个人 IDE 配置，不应共享 |

### 如何安全地存储敏感信息

#### 方法 1：使用 `.env.example`（推荐）

**步骤1：项目维护者创建模板**
```bash
# .env.example - 提交到 Git
OPENAI_API_KEY=your_key_here
LLM_MODEL_DEEP=deepseek-reasoner
DATABASE_PATH=./trade_memory/portfolio.db
```

**步骤2：开发者本地配置**
```bash
# 克隆项目后
cp .env.example .env

# 然后编辑 .env，填入实际的值
# .env 已被 .gitignore 忽略，不会提交
```

#### 方法 2：使用 `.env.local`（可选）

对于环境特定的配置：
```bash
# .env.local - 本地特定配置（不提交）
OPENAI_API_KEY=my_personal_key_production
TEST_MODE=true
```

#### 方法 3：使用系统环境变量

```bash
# 在 Shell 中设置（Linux/macOS）
export OPENAI_API_KEY="your_key_here"

# 在 PowerShell 中设置（Windows）
$env:OPENAI_API_KEY = "your_key_here"

# Python 代码中使用
import os
api_key = os.getenv('OPENAI_API_KEY')
```

## 📁 项目结构中应上传的文件

### ✅ 应该提交到 Git

| 目录/文件 | 说明 |
|---------|------|
| `tradingagents/` | 源代码（核心库） |
| `cli/` | 命令行工具代码 |
| `docs/` | 文档和指南 |
| `examples/` | 示例代码和文档 |
| `.gitignore` | Git 忽略规则 |
| `.gitkeep` | 空目录占位符（如需） |
| `.env.example` | 环境变量模板 |
| `pyproject.toml` | 项目配置 |
| `requirements.txt` | 依赖声明 |
| `README.md` | 项目介绍 |
| `main.py`, `trigger_main.py` | 入口脚本 |
| `LICENSE` | 许可证 |

### ❌ 不应永久提交的目录

| 目录 | 为什么 | 替代方案 |
|------|------|--------|
| `__pycache__/` | 编译缓存 | 自动生成，无需提交 |
| `.venv/`, `venv/` | 虚拟环境 | 使用 `requirements.txt` 重建 |
| `trade_memory/` | 交易数据 | 各自本地维护 |
| `eval_results/` | 测试输出 | 临时结果，无需保存 |
| `.eggs/`, `build/`, `dist/` | 构建产物 | 构建时生成 |

## 🔄 TeamCollaboration 最佳实践

### 1. 初始化项目（项目维护者）

```bash
# 1. 创建 .env.example 模板
echo "OPENAI_API_KEY=your_key_here" > .env.example
echo ".env" >> .gitignore

# 2. 提交模板到 Git
git add .env.example
git commit -m "Add .env.example template"

# 3. 创建本地 .env
cp .env.example .env
# 编辑 .env，填入真实值

# 验证 .env 被忽略
git status  # .env 不应出现
```

### 2. 队友加入（开发者）

```bash
# 1. 克隆项目
git clone <repository>

# 2. 创建虚拟环境
python -m venv .venv
.\.venv\Scripts\Activate.ps1  # Windows
source .venv/bin/activate    # Linux/macOS

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置本地环境
cp .env.example .env
# 编辑 .env，填入你的 API 密钥

# 5. 验证配置
python docs/scripts/validate_refactoring.py
```

### 3. 更新依赖

```bash
# 添加新的依赖后
pip install new_package
pip freeze > requirements.txt

# 提交更新
git add requirements.txt
git commit -m "Add new_package dependency"

# 通知团队
# 其他成员需运行：pip install -r requirements.txt
```

### 4. 添加新的敏感配置项

```bash
# 更新 .env.example
echo "NEW_API_KEY=your_key_here" >> .env.example

# 提交模板
git add .env.example
git commit -m "Add NEW_API_KEY configuration template"

# 其他成员需更新本地 .env
cp .env.example .env  # 或手动添加
```

## 🚀 常用命令速查

```bash
# 检查哪些文件被忽略
git status --ignored

# 检查特定文件是否被忽略
git check-ignore -v <文件路径>

# 查看所有提交前更改（不包括忽略的文件）
git diff

# 强制添加已被忽略的文件（通常不需要）
git add -f <文件>

# 移除已跟踪但应被忽略的文件
git rm --cached <文件>
```

## 📊 .gitignore 规则分布

当前项目的 `.gitignore` 包含：
- **152 条** 具体规则
- **41 个** 规则分类
- **4 个** 关键安全类别
  - `.env*` 环境变量（安全）
  - `trade_memory/` 交易数据（隐私）
  - `*.db`, `*.sqlite` 数据库（大小和隐私）
  - `__pycache__/` 编译缓存（可再生）

详见：[GITIGNORE_GUIDE.md](docs/GITIGNORE_GUIDE.md)

## ⚠️ 常见陷阱和解决方案

### 问题 1：意外提交了敏感信息

```bash
# 如果已推送到远程
git log --all --full-history -p -- <sensitive_file>
git revert <commit_hash>

# 如果仅在本地
git rm --cached <sensitive_file>
git commit --amend
```

### 问题 2：队友看不到数据库初始化

```bash
# 正确的做法：提供初始化脚本
python -c "from tradingagents import PortfolioManager; PortfolioManager().initialize_database()"

# 而不是：提交 *.db 文件
```

### 问题 3：.venv 被意外提交

```bash
# 从 Git 历史中移除
git rm --cached -r .venv
echo ".venv/" >> .gitignore
git commit -m "Remove virtual environment from tracking"

# 其他成员需重建
python -m venv .venv
pip install -r requirements.txt
```

## 📚 相关文档

- 🔐 [.gitignore 详细指南](docs/GITIGNORE_GUIDE.md)
- 📝 [项目结构说明](docs/PROJECT_STRUCTURE.md)
- 🔧 [项目整理总结](docs/CLEANUP_SUMMARY.md)
- 🚀 [快速导航](NAVIGATION.md)

## ✅ 检查清单

初始化新机器时：

- [ ] 克隆项目
- [ ] 创建虚拟环境 `.venv/`
- [ ] 安装依赖 `pip install -r requirements.txt`
- [ ] 复制 `.env.example` 为 `.env`
- [ ] 在 `.env` 中填入 API 密钥
- [ ] 验证 `git status` 不显示 `.env`
- [ ] 运行 `python docs/scripts/validate_refactoring.py` 验证配置
- [ ] 准备好开始开发！

---

**最后更新**：2026-03-30  
**文档版本**：1.0
