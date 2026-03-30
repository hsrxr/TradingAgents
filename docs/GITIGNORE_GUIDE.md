# .gitignore 配置说明

## 概述

本项目的 `.gitignore` 文件包含 **152 条忽略规则**，分为 **41 个类别**，用于防止不必要的文件被上传到 Git 仓库。

## 规则分类详解

### 1️⃣ Python 编译和缓存
- `__pycache__/` - Python 编译缓存目录
- `*.pyc`, `*.pyo` - Python 编译字节码
- `*.py[cod]` - Python 编译文件
- `*$py.class` - Python 类文件

### 2️⃣ 虚拟环境
- `.venv/`, `venv/`, `ENV/`, `env/` - 各种虚拟环境目录
- 这些目录可以由队友通过 `pip install -r requirements.txt` 重建

### 3️⃣ 环境变量和密钥（🔒 安全相关）
- `.env` - 本地环境变量文件（包含敏感信息）
- `.env.local` - 本地特定的环境变量
- `.env.*.local` - 环境特定的本地配置
- `.envrc` - direnv 配置文件

### 4️⃣ IDE 和编辑器配置
**VS Code**
- `.vscode/` - 工作区设置目录
- `*.code-workspace` - Workspace 配置文件

**PyCharm/IntelliJ**
- `.idea/` - IDE 配置目录
- `*.iml` - IntelliJ 项目文件

**Sublime Text**
- `*.sublime-workspace` - Sublime 工作区
- `*.sublime-project` - Sublime 项目配置

**Vim**
- `.vim/`, `Session.vim` - Vim 配置和会话

**Emacs**
- `*~`, `\#*\#`, `.\#*` - Emacs 临时文件

### 5️⃣ 操作系统文件（🖥️ 系统文件）
**Windows**
- `Thumbs.db` - Windows 缩略图缓存
- `$RECYCLE.BIN/` - 回收站
- `ehthumbs.db` - Edge 缩略图缓存
- `desktop.ini` - Windows 文件夹配置

**macOS**
- `.DS_Store` - macOS 文件夹配置文件
- `.AppleDouble`, `.LSOverride` - Apple 特定文件
- `._*` - macOS 资源 fork
- `.Spotlight-V100`, `.Trashes` - Spotlight 和回收站

**通用**
- `*.lnk` - Windows 快捷链接
- `.desktop` - Linux 快捷方式

### 6️⃣ 项目运行时数据（💾 重要：本地生成数据）

**交易和投资组合数据**
- `trade_memory/portfolio.db` - 投资组合持久化数据库
- `trade_memory/chroma_data/` - ChromaDB 向量数据库（大文件）
- `trade_memory/*.db` 和 `trade_memory/*.sqlite*` - 所有数据库文件

**缓存数据**
- `data/*.db`, `data/*.sqlite*` - 数据目录中的数据库
- `crypto_news.db` - 加密货币新闻缓存

**评估和测试结果**
- `eval_results/` 及其下所有文件 - 评估输出结果
- 这些是运行测试时的临时结果

**可视化输出**
- `visualisation/*.html`, `visualisation/*.json` - 生成的仪表板文件

### 7️⃣ 构建和分发文件（📦 包管理）
- `build/`, `dist/` - Python 构建输出目录
- `*.egg-info/`, `.eggs/` - 包元数据
- `*.egg`, `*.whl`, `*.tar.gz` - 分发包
- `MANIFEST` - 包清单文件

### 8️⃣ 日志文件（📝 调试文件）
- `*.log`, `*.log.[0-9]*` - 日志文件及其轮转副本
- `logs/`, `log/` - 日志目录
- `npm-debug.log` - npm 调试日志

### 9️⃣ 临时文件（⏱️ 临时和备份）
- `*.tmp`, `*.temp` - 临时文件
- `*.bak`, `*.orig`, `*.rej` - 备份和合并冲突文件
- `*.swp`, `*.swo`, `*~` - 编辑器临时文件
- `*.swp~` - 另一种临时文件格式

### 🔟 代码质量工具（🔍 检查和格式化）

**Coverage 和测试**
- `.coverage`, `.coverage.*` - 代码覆盖率数据
- `coverage.xml` - 覆盖率报告
- `.pytest_cache/`, `.cache` - pytest 缓存
- `.hypothesis/`, `.tox/`, `.nox/` - 测试工具缓存
- `htmlcov/`, `nosetests.xml` - 测试报告

**类型检查**
- `.mypy_cache/`, `.dmypy.json` - MyPy 缓存
- `.pyre/` - Pyre 类型检查器缓存

**Linting 和格式化**
- `.black`, `.isort.cfg`, `.flake8` - 代码风格工具配置缓存
- `*.cover` - Coverage 覆盖文件

### 1️⃣1️⃣ 数据库相关（🗄️ 数据库文件）
- `*.db-journal`, `*.db-wal`, `*.db-shm` - SQLite 日志和临时文件
- 这些是 SQLite 在事务处理时创建的临时文件

### 1️⃣2️⃣ 分发包管理（📦 依赖）
- `poetry.lock` - Poetry 依赖锁文件（用 requirements.txt 代替）
- `setup.cfg` - Setuptools 配置
- `uv.lock` - uv 包管理器的锁文件

### 1️⃣3️⃣ Jupyter 和 IPython（📔 笔记本）
- `.ipynb_checkpoints/` - Jupyter 检查点目录
- `*.ipynb` - Jupyter 笔记本文件（如果不是项目核心）
- `.ipython/` - IPython 配置目录

### 1️⃣4️⃣ NPM 相关（包管理器）
- `node_modules/` - Node.js 依赖目录
- `npm-debug.log` - npm 错误日志

### 1️⃣5️⃣ 浏览器自动化（🌐 测试工具）
- `screenshots/`, `artifacts/` - 测试截图和工件目录
- `*.png`, `*.jpg`, `*.jpeg` - 测试生成的图像文件

## 重要提示

### 🔒 安全性
- **从不提交** `.env` 文件（包含 API 密钥）
- **从不提交** `trade_memory/` 和 `data/` 目录
- **从不提交** 本地IDE配置和历史记录

### 📋 维护建议

1. **保留可共享配置**：如果有需要共享的配置，创建 `.env.example`
   ```bash
   # .env.example
   OPENAI_API_KEY=your_key_here
   LLM_MODEL=deepseek-reasoner
   ```

2. **当地特定的设置**：使用 `.env.local` 而不是 `.env`

3. **定期审查**：定期检查是否有新文件类型需要被忽略
   ```bash
   git status --ignored
   ```

4. **团队同步**：如果添加新规则，通知团队重新构建虚拟环境
   ```bash
   pip install -r requirements.txt
   ```

## 验证规则

检查当前忽略的文件：
```bash
git status --ignored
```

检查特定文件是否会被忽略：
```bash
git check-ignore -v <文件路径>
```

强制查看所有状态（包括忽略的文件）：
```bash
git status --ignored --renames
```

## 统计数据

- **总规则数**：152 条
- **规则分类**：41 个主要类别
- **最重要的规则**：`.env`, `trade_memory/`, `*.db`, `__pycache__/`

## 相关文件

- 依赖声明：[requirements.txt](../requirements.txt)
- 项目配置：[pyproject.toml](../pyproject.toml)
- 环境示例：`.env.example`（建议创建）

---
**最后更新**：2026-03-30
