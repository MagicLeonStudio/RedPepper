<p align="center">
  <img src="assets/logo.png" alt="RedPepper Logo" width="80">
</p>

<h1 align="center">RedPepper 开发环境配置指南</h1>

<p align="center">
  <i>RedPepper Development Environment Setup Guide</i>
</p>

---

## 目录 / Table of Contents

- [系统要求 / System Requirements](#系统要求--system-requirements)
- [Python 安装 / Python Installation](#python-安装--python-installation)
  - [Windows](#windows)
  - [macOS](#macos)
  - [Linux](#linux)
- [环境搭建 / Environment Setup](#环境搭建--environment-setup)
- [开发工具配置 / IDE Configuration](#开发工具配置--ide-configuration)
  - [VS Code 配置](#vs-code-配置)
  - [推荐插件](#推荐插件)
- [开发工作流 / Development Workflow](#开发工作流--development-workflow)
  - [启动后端服务](#启动后端服务)
  - [启动前端应用](#启动前端应用)
  - [运行测试](#运行测试)
  - [代码格式化](#代码格式化)
- [数据库 / Database](#数据库--database)
- [AI API 配置 / AI API Configuration](#ai-api-配置--ai-api-configuration)
  - [Kimi API Key 申请](#kimi-api-key-申请)
  - [DeepSeek API Key 申请](#deepseek-api-key-申请)
- [项目打包 / Packaging](#项目打包--packaging)
- [常见问题 FAQ / Troubleshooting](#常见问题-faq--troubleshooting)
- [目录说明 / Directory Guide](#目录说明--directory-guide)

---

## 系统要求 / System Requirements

| 项目 | 最低要求 | 推荐配置 |
|------|---------|---------|
| Python 版本 | 3.10 | 3.11 或 3.12 |
| 操作系统 | Windows 10 / macOS 11 / Ubuntu 20.04 | Windows 11 / macOS 14 / Ubuntu 22.04 |
| 内存 (RAM) | 4 GB | 8 GB |
| 磁盘空间 | 500 MB | 2 GB（含虚拟环境与依赖） |
| 网络连接 | 可选 | 推荐（用于 AI 功能） |
| Git | 2.30+ | 最新版 |

> 注：AI 功能（截图 OCR、日报生成等）需要网络连接调用云端 API。纯本地功能（数据录入、查看、导出）无需网络。

---

## 安装 Anaconda / Install Anaconda

RedPepper 推荐使用 **Anaconda**（或轻量版 Miniconda）管理 Python 环境和依赖包。Conda 对 PyQt6、cryptography 等含 C 扩展的包管理更可靠，能避免大部分编译错误。

### 安装 Anaconda（推荐）

**Windows：**

1. 访问 [anaconda.com/download](https://www.anaconda.com/download)
2. 下载 Anaconda Distribution 安装包（Python 3.11+）
3. 双击安装，**勾选 "Add Anaconda3 to my PATH"**
4. 打开 **Anaconda Prompt**（在开始菜单中找到）验证：

```bash
conda --version
# 应显示 conda 23.x.x 或更高版本

python --version
# 应显示 Python 3.11.x
```

**macOS：**

```bash
# 方式一：官网安装包
# 下载 .pkg 安装包后双击安装

# 方式二：Homebrew
brew install --cask anaconda

# 验证
conda --version
```

**Linux：**

```bash
# 下载安装脚本（以 Python 3.11 为例）
wget https://repo.anaconda.com/archive/Anaconda3-2024.02-1-Linux-x86_64.sh

# 运行安装（按提示操作，建议接受默认路径）
bash Anaconda3-2024.02-1-Linux-x86_64.sh

# 重新加载 shell 配置
source ~/.bashrc

# 验证
conda --version
```

### 安装 Miniconda（轻量版，推荐有经验用户）

如果不需要 Anaconda 自带的 IDE 和数据科学工具，可以安装更轻量的 Miniconda：

**Windows：**
下载 [Miniconda Installer](https://docs.conda.io/en/latest/miniconda.html) 并运行。

**macOS / Linux：**

```bash
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh
source ~/.bashrc
```

### 配置 Conda（推荐）

```bash
# 配置国内镜像（加速下载，可选）
# 中科大镜像
conda config --add channels https://mirrors.ustc.edu.cn/anaconda/pkgs/main/
conda config --add channels https://mirrors.ustc.edu.cn/anaconda/pkgs/free/
conda config --set show_channel_urls yes

# 更新 conda 本身
conda update -n base -c defaults conda
```

---

## 环境搭建 / Environment Setup

### Step 1: 克隆仓库

```bash
# 使用 HTTPS
git clone https://github.com/magic-leon-studio/redpepper.git

# 或使用 SSH
git clone git@github.com:magic-leon-studio/redpepper.git

cd redpepper
```

### Step 2: 创建 Conda 环境（一键完成）

项目根目录已包含 `environment.yml`，所有依赖均已声明，一键创建：

```bash
# 创建环境（自动安装所有依赖，包括 PyQt6）
conda env create -f environment.yml

# 环境创建完成后激活
conda activate redpepper
```

> **Tip**: 如果 `conda env create` 速度较慢，可尝试使用 mamba（conda 的高性能实现）：
> ```bash
> conda install mamba -n base -c conda-forge
> mamba env create -f environment.yml
> ```

### Step 3: 验证安装

```bash
# 确认环境已激活（提示符前显示 redpepper）
which python  # macOS/Linux
where python  # Windows

# 应显示 conda envs/redpepper 路径
# 例如: /Users/xxx/anaconda3/envs/redpepper/bin/python

# 逐项验证关键依赖
python -c "from backend.app.main import app; print('FastAPI 后端: OK')"
python -c "from PyQt6 import QtWidgets; print('PyQt6 前端: OK')"
python -c "from cryptography.hazmat.primitives.ciphers.aead import AESGCM; print('加密模块: OK')"
python -c "import sqlalchemy; print(f'SQLAlchemy: {sqlalchemy.__version__} OK')"
python -c "import httpx; print(f'httpx: {httpx.__version__} OK')"
```

### 日常环境管理命令速查

| 操作 | 命令 |
|------|------|
| 激活环境 | `conda activate redpepper` |
| 退出环境 | `conda deactivate` |
| 删除环境（彻底重置） | `conda env remove -n redpepper` |
| 重新创建环境 | `conda env create -f environment.yml --force` |
| 更新依赖 | `conda env update -f environment.yml --prune` |
| 查看已安装包 | `conda list` |
| 临时安装新包 | `conda install <包名>` 或 `pip install <包名>` |

### 常见问题：Conda 环境创建失败

**Q: `conda env create` 报 `ResolvePackageNotFound` 错误？**

A: 通常是 channels 配置问题，尝试以下步骤：

```bash
# 1. 确保 channels 已配置
conda config --add channels conda-forge
conda config --set channel_priority flexible

# 2. 重新创建
conda env create -f environment.yml --force
```

**Q: PyQt6 在 conda 中安装后找不到？**

A: Conda 的 PyQt6 包名可能略有不同，尝试：

```bash
# 激活环境后手动安装
conda activate redpepper
conda install pyqt -c conda-forge

# 或明确指定版本
conda install pyqt=6.6 -c conda-forge
```

**Q: 想用 pip 安装部分包（conda 中没有的最新版）？**

A: 混合使用完全没问题，推荐顺序：

```bash
conda activate redpepper

# 先尝试 conda 安装（更稳定）
conda install <package_name>

# conda 找不到再用 pip
pip install <package_name>
```

---

## 开发工具配置 / IDE Configuration

### VS Code 配置

在项目根目录创建 `.vscode/settings.json`：

```json
{
  "python.defaultInterpreterPath": "${env:CONDA_PREFIX}/bin/python",
  "python.terminal.activateEnvironment": true,
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll.ruff": "explicit"
  },
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests"],
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true,
    "**/.pytest_cache": true,
    "**/build": true,
    "**/dist": true,
    "**/*.spec": true
  },
  "search.exclude": {
    "**/data/*.db": true,
    "**/*.redpepper": true
  }
}
```

**Windows 用户注意**：`python.defaultInterpreterPath` 应改为：

```json
{
  "python.defaultInterpreterPath": "${env:CONDA_PREFIX}\\python.exe"
}
```

> **Tip**: `${env:CONDA_PREFIX}` 自动指向当前激活的 conda 环境，无需硬编码路径。只需在 VS Code 终端中先 `conda activate redpepper`，然后用 `Ctrl+Shift+P` → "Python: Select Interpreter" 选择 redpepper 环境即可。

### 推荐插件

| 插件名 | 功能 | 推荐度 |
|--------|------|--------|
| Python (Microsoft) | Python 语言支持 | 必需 |
| Pylance | Python 类型检查与智能提示 | 必需 |
| Ruff | Python 代码检查与格式化 | 必需 |
| Black Formatter | Python 代码格式化 | 必需 |
| autoDocstring | 自动生成文档字符串 | 推荐 |
| GitLens | Git 增强功能 | 推荐 |
| Markdown All in One | Markdown 编辑增强 | 推荐 |
| Qt for Python | PyQt6/QML 开发支持 | 推荐 |

安装命令（VS Code 命令面板 → 输入以下 ID 安装）：

```
ms-python.python
ms-python.vscode-pylance
charliermarsh.ruff
ms-python.black-formatter
njpwerner.autodocstring
eamodio.gitlens
yzhang.markdown-all-in-one
theqtcompany.qt
```

---

## 开发工作流 / Development Workflow

### 启动后端服务

```bash
# 激活环境
conda activate redpepper

# 启动 FastAPI 开发服务器
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

# 参数说明：
# --reload    代码变更后自动重启（仅开发环境）
# --host      绑定地址，127.0.0.1 仅本机访问
# --port      服务端口，默认 8000
```

启动成功后访问：

- API 文档（Swagger UI）：[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- 替代文档（ReDoc）：[http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- 健康检查：[http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

### 启动前端应用

在**新的终端窗口**中执行：

```bash
# 激活环境
conda activate redpepper

# 启动 PyQt6 桌面应用
python -m frontend.main

# 或使用模块方式
python frontend/main.py
```

> **开发模式**：前后端需要分别启动。后端提供 API 服务，前端提供 GUI 界面。
>
> **生产模式**：前端通过 PyInstaller 打包为独立可执行文件，内嵌后端服务。

### 运行测试

```bash
# 确保在 redpepper 环境中
conda activate redpepper

# 运行所有测试
pytest tests/ -v

# 运行特定测试文件
pytest tests/test_security.py -v
pytest tests/test_api.py -v

# 运行并生成覆盖率报告
pytest tests/ --cov=backend/app --cov-report=html

# 运行 GUI 测试（需要显示环境）
pytest tests/test_gui.py --qt-api=pyqt6
```

### 代码格式化

```bash
# 使用 black 格式化代码
black app/ frontend/ tests/

# 使用 ruff 检查并修复问题
ruff check app/ frontend/ tests/ --fix

# 两者结合（推荐提交前执行）
black app/ frontend/ tests/ && ruff check app/ frontend/ tests/ --fix
```

**Git 提交前检查脚本**（可选）：

```bash
#!/bin/bash
# .git/hooks/pre-commit

echo "Running code formatters..."

# Black 格式化
black --check app/ frontend/ tests/
if [ $? -ne 0 ]; then
    echo "Black formatting failed. Run: black app/ frontend/ tests/"
    exit 1
fi

# Ruff 检查
ruff check app/ frontend/ tests/
if [ $? -ne 0 ]; then
    echo "Ruff check failed. Run: ruff check app/ frontend/ tests/ --fix"
    exit 1
fi

# 运行测试
pytest tests/ -q
if [ $? -ne 0 ]; then
    echo "Tests failed. Fix before committing."
    exit 1
fi

echo "Pre-commit checks passed!"
```

---

## 数据库 / Database

RedPepper 使用 **SQLite3** 作为本地数据库，无需单独安装数据库服务。

### 数据库文件位置

```
data/
└── redpepper.db          # 主数据库文件
```

### 数据库表结构

| 表名 | 说明 |
|------|------|
| `users` | 用户信息（密码哈希、盐值、锁定状态） |
| `portfolios` | 持仓记录（股票代码、成本、数量、账户） |
| `watchlists` | 观察池股票列表 |
| `knowledge_links` | 知识库收藏链接 |
| `trade_logs` | 交易操作日志 |
| `app_settings` | 应用配置（语言、AI Key 等） |

### 数据库查看工具

推荐使用以下 GUI 工具查看和调试 SQLite 数据库：

| 工具 | 平台 | 下载 |
|------|------|------|
| DB Browser for SQLite | Win/Mac/Linux | [sqlitebrowser.org](https://sqlitebrowser.org) |
| DBeaver Community | Win/Mac/Linux | [dbeaver.io](https://dbeaver.io) |
| TablePlus | Mac/Win | [tableplus.com](https://tableplus.com) |
| SQLiteStudio | Win/Mac/Linux | [sqlitestudio.pl](https://sqlitestudio.pl) |

### 命令行操作

```bash
# 进入 SQLite 命令行
sqlite3 data/redpepper.db

# 查看所有表
.tables

# 查看表结构
.schema portfolios

# 查询数据
SELECT * FROM portfolios;

# 退出
.quit
```

---

## AI API 配置 / AI API Configuration

### Kimi API Key 申请

**Kimi**（月之暗面）是 Moonshot AI 出品的大语言模型，擅长长文本处理。

**申请步骤：**

1. 访问开放平台：[platform.moonshot.cn](https://platform.moonshot.cn)
2. 点击右上角「注册」，使用手机号完成注册
3. 登录后进入「控制台」
4. 左侧菜单选择「API Key 管理」
5. 点击「创建 API Key」按钮
6. 输入 Key 名称（如 "RedPepper"），点击确认
7. **立即复制**生成的 Key（仅显示一次）
8. 在 RedPepper 设置中粘贴 Key

**可选模型：**

| 模型 | 上下文长度 | 适用场景 |
|------|-----------|---------|
| moonshot-v1-8k | 8K | 短文本、快速响应 |
| moonshot-v1-32k | 32K | 中等长度分析 |
| moonshot-v1-128k | 128K | 长文档、大量持仓分析 |

**费用说明：** 新用户赠送 15 元体验额度，后续按 Token 使用量计费。

### DeepSeek API Key 申请

**DeepSeek** 是深度求索出品的大语言模型，推理能力强。

**申请步骤：**

1. 访问开放平台：[platform.deepseek.com](https://platform.deepseek.com)
2. 点击「注册」，使用手机号完成注册
3. 登录后进入「API Keys」页面
4. 点击「创建 API Key」
5. 输入 Key 名称，点击「创建」
6. **立即复制**生成的 Key（仅显示一次）
7. 在 RedPepper 设置中粘贴 Key

**可选模型：**

| 模型 | 特点 | 适用场景 |
|------|------|---------|
| deepseek-chat | 通用对话模型 | 日常分析、OCR 识别 |
| deepseek-reasoner | 深度推理模型 | 复杂投资分析、策略评估 |

**费用说明：** 新用户赠送 10 元体验额度，后续按 Token 使用量计费。

### 本地配置

API Key 存储在 SQLite 数据库的 `app_settings` 表中，**经过加密处理**，不会以明文形式存储。

```python
# 配置存储结构（示例）
{
    "ai_provider": "kimi",           # 或 "deepseek"
    "kimi_api_key": "enc:xxxx...",   # 加密存储
    "kimi_model": "moonshot-v1-8k",
    "deepseek_api_key": "enc:xxxx...", # 加密存储
    "deepseek_model": "deepseek-chat"
}
```

---

## 项目打包 / Packaging

使用 **PyInstaller** 将 RedPepper 打包为独立可执行文件。

### 安装 PyInstaller

```bash
pip install pyinstaller
```

### 打包命令

```bash
# 单文件模式（推荐测试）
pyinstaller --onefile --windowed \
    --name RedPepper \
    --icon=assets/logo.ico \
    --add-data "assets:assets" \
    frontend/main.py

# 单目录模式（推荐分发，启动更快）
pyinstaller --onedir --windowed \
    --name RedPepper \
    --icon=assets/logo.ico \
    --add-data "assets:assets" \
    --add-data "data:data" \
    frontend/main.py

# 使用 spec 文件打包（推荐正式发布）
pyinstaller redpepper.spec
```

**打包参数说明：**

| 参数 | 说明 |
|------|------|
| `--onefile` | 打包为单个可执行文件 |
| `--onedir` | 打包为目录（包含依赖文件） |
| `--windowed` | 不显示控制台窗口（GUI 应用） |
| `--icon` | 应用图标 |
| `--add-data` | 附加资源文件 |
| `--name` | 输出文件名 |

### 输出位置

```
dist/
├── RedPepper/              # 单目录模式输出
│   ├── RedPepper           # 可执行文件
│   ├── _internal/          # 依赖库
│   └── assets/             # 资源文件
│
# 或
dist/
└── RedPepper               # 单文件模式输出
```

### 各平台打包注意事项

**Windows：**

```powershell
# 使用 PowerShell
pyinstaller --onedir --windowed `
    --name RedPepper `
    --icon=assets\logo.ico `
    frontend\main.py

# 输出: dist/RedPepper/RedPepper.exe
```

**macOS：**

```bash
# 打包为 .app 应用包
pyinstaller --onedir --windowed \
    --name RedPepper \
    --icon=assets/logo.icns \
    frontend/main.py

# 可选：创建 DMG 安装包
create-dmg \
    --volname "RedPepper Installer" \
    --window-pos 200 120 \
    --window-size 800 400 \
    --icon-size 100 \
    --app-drop-link 600 185 \
    "RedPepper.dmg" \
    "dist/RedPepper.app"
```

**Linux：**

```bash
# 打包
pyinstaller --onedir --windowed \
    --name redpepper \
    frontend/main.py

# 可选：创建 AppImage（需要 appimagetool）
# 或创建 .deb 包（需要 dpkg-deb）
```

---

## 常见问题 FAQ / Troubleshooting

### Q1: 后端启动失败 / Backend Won't Start

**问题表现**：
```
Error: [Errno 98] Address already in use
```

**解决方案**：
```bash
# 查找占用 8000 端口的进程
# macOS/Linux:
lsof -i :8000

# Windows:
netstat -ano | findstr :8000

# 使用其他端口启动
uvicorn app.main:app --reload --port 8080
```

**问题表现**：
```
ModuleNotFoundError: No module named 'app'
```

**解决方案**：
```bash
# 确保在项目根目录运行
pwd  # 应显示 .../redpepper

# 确保虚拟环境已激活
which python  # 应显示 .../envs/redpepper/bin/python

# 重新安装依赖
pip install -r requirements.txt
```

### Q2: PyQt6 安装失败 / PyQt6 Installation Failed

**问题表现**：
```
ERROR: Could not find a version that satisfies the requirement PyQt6
```

**解决方案**：

**Windows：**
```powershell
# 确保 Python 是 64 位
python -c "import struct; print(struct.calcsize('P') * 8)"  # 应显示 64

# 升级 pip
python -m pip install --upgrade pip

# 单独安装 PyQt6
pip install PyQt6 --only-binary :all:
```

**Linux（缺少 Qt 依赖）：**
```bash
# Ubuntu/Debian
sudo apt install -y libgl1-mesa-dev libxkbcommon-x11-dev libxcb-*

# CentOS/RHEL
sudo yum install -y mesa-libGL-devel libxkbcommon-x11-devel libxcb*

# 然后重新安装
pip install PyQt6
```

**macOS：**
```bash
# 通常无需额外依赖
# 如遇到问题，尝试：
pip install --force-reinstall PyQt6
```

### Q3: 前端无法连接后端 / Frontend Can't Connect to Backend

**问题表现**：
```
ConnectionError: HTTPConnectionPool(host='127.0.0.1', port=8000)
```

**解决方案**：

1. 确认后端服务已启动：
```bash
curl http://127.0.0.1:8000/health
# 应返回 {"status": "ok"}
```

2. 检查防火墙设置，确保 8000 端口未被阻止

3. 修改前端配置指向正确地址：
```python
# frontend/config.py
API_BASE_URL = "http://127.0.0.1:8000"  # 修改为实际地址
```

### Q4: AI 功能无法使用 / AI Features Not Working

**问题表现**：
```
AI Analysis Failed: 401 Unauthorized
```

**解决方案**：

1. 检查 API Key 是否正确配置
2. 确认 API Key 余额充足
3. 检查网络连接
4. 查看详细错误日志：
```bash
# 后端日志会显示详细错误信息
# 常见错误：
# - 401: Key 无效或过期
# - 429: 请求频率限制
# - 500: 服务商内部错误
```

### Q5: 数据库权限错误 / Database Permission Error

**问题表现**：
```
sqlite3.OperationalError: attempt to write a readonly database
```

**解决方案**：
```bash
# 检查数据目录权限
ls -la data/

# 修复权限（Linux/macOS）
chmod 755 data/
chmod 644 data/redpepper.db

# Windows: 右键 → 属性 → 安全 → 编辑权限
```

### Q6: Conda 环境相关问题 / Conda Environment Issues

**问题表现**：`python` 或 `pip` 指向了系统 Python 而不是 redpepper 环境

**解决方案**：
```bash
# 确认环境已激活
conda activate redpepper

# 验证路径
which python  # macOS/Linux — 应包含 .../envs/redpepper/...
where python  # Windows — 应包含 ...\envs\redpepper\...

# 如未激活，重新激活
conda activate redpepper

# 如果某个包安装了但找不到，可能是环境损坏，重建即可
conda env remove -n redpepper
conda env create -f environment.yml
```

### Q7: 打包后应用无法运行 / Packaged App Won't Run

**问题表现**：双击可执行文件无反应

**解决方案**：

```bash
# 1. 使用命令行运行查看错误
dist/RedPepper/RedPepper  # macOS/Linux
dist\RedPepper\RedPepper.exe  # Windows

# 2. 检查是否缺少数据文件
# 确保 --add-data 参数包含了所有必要资源

# 3. 重新打包并查看详细日志
pyinstaller --onedir --windowed \
    --name RedPepper \
    --log-level DEBUG \
    frontend/main.py 2>&1 | tee build.log
```

### Q8: macOS 提示"无法打开应用" / macOS App Can't Open

**解决方案**：
```bash
# 方式一：系统设置 → 隐私与安全性 → 允许

# 方式二：命令行移除隔离属性
xattr -dr com.apple.quarantine dist/RedPepper.app

# 方式三：签名（开发者）
codesign --force --deep --sign - dist/RedPepper.app
```

---

## 目录说明 / Directory Guide

```
redpepper/                          # 项目根目录
│
├── frontend/                       # PyQt6 桌面前端代码
│   ├── __init__.py                 # 包初始化
│   ├── main.py                     # 前端应用入口，初始化 QApplication
│   ├── windows/                    # 主窗口与子窗口
│   │   ├── login_window.py         # 登录/注册窗口（密码输入、错误锁定）
│   │   ├── main_window.py          # 主窗口（侧边栏导航、内容区域）
│   │   ├── portfolio_window.py     # 持仓总览界面（股票列表、盈亏统计）
│   │   ├── settings_window.py      # 设置界面（AI、语言、导入导出）
│   │   └── watchlist_window.py     # 观察池界面（关注股票管理）
│   ├── widgets/                    # 可复用 UI 组件
│   │   ├── stock_card.py           # 股票信息卡片组件
│   │   ├── chart_widget.py         # 图表展示组件
│   │   └── ai_chat_panel.py        # AI 对话面板组件
│   └── resources/                  # 前端静态资源
│       ├── i18n/                   # 国际化翻译文件
│       │   ├── zh_CN.json          # 中文翻译
│       │   └── en.json             # 英文翻译
│       ├── icons/                  # 应用图标（PNG/SVG）
│       └── styles/                 # QSS 样式文件
│           └── dark_theme.qss      # 暗色主题样式
│
├── app/                            # FastAPI 后端服务
│   ├── __init__.py                 # 包初始化
│   ├── main.py                     # FastAPI 应用入口，注册路由
│   ├── routers/                    # API 路由模块（按功能划分）
│   │   ├── __init__.py
│   │   ├── auth.py                 # 认证路由（登录、注册、密码修改）
│   │   ├── portfolio.py            # 持仓路由（CRUD、查询）
│   │   ├── watchlist.py            # 观察池路由
│   │   ├── ai_proxy.py             # AI 代理路由（转发 AI 请求）
│   │   └── import_export.py        # 导入导出路由
│   ├── models/                     # 数据模型与数据库操作
│   │   ├── __init__.py
│   │   ├── database.py             # SQLite 连接引擎与会话管理
│   │   ├── user.py                 # 用户模型（SQLAlchemy ORM）
│   │   ├── stock.py                # 股票/持仓模型
│   │   └── settings.py             # 应用配置模型
│   ├── services/                   # 业务逻辑层
│   │   ├── __init__.py
│   │   ├── auth_service.py         # 认证业务（密码验证、锁定逻辑）
│   │   ├── ai_service.py           # AI 调用封装（Kimi/DeepSeek 统一接口）
│   │   ├── ocr_service.py          # OCR 识别服务（截图解析）
│   │   └── crypto_service.py       # 加密服务（数据加解密）
│   └── utils/                      # 工具函数
│       ├── __init__.py
│       ├── crypto.py               # 加解密工具（PBKDF2、AES-256-GCM）
│       └── validators.py           # 数据校验工具
│
├── data/                           # 本地数据存储（不纳入版本控制）
│   ├── redpepper.db                # SQLite 主数据库
│   └── backups/                    # 自动备份目录
│
├── tests/                          # 测试用例
│   ├── __init__.py
│   ├── test_auth.py                # 认证模块测试
│   ├── test_portfolio.py           # 持仓模块测试
│   ├── test_crypto.py              # 加密模块测试
│   └── test_gui.py                 # GUI 测试（pytest-qt）
│
├── assets/                         # 项目资产文件
│   ├── logo.png                    # 应用 Logo（PNG 格式）
│   ├── logo.ico                    # Windows 图标
│   ├── logo.icns                   # macOS 图标
│   └── screenshots/                # 文档用截图
│
├── requirements.txt                # Python 依赖清单
├── setup.py                        # Python 包安装配置
├── redpepper.spec                  # PyInstaller 打包配置
├── README.md                       # 项目说明文档
├── SETUP.md                        # 开发环境配置文档（本文档）
├── LICENSE                         # MIT 开源协议
└── .gitignore                      # Git 忽略规则
```

---

<p align="center">
  <b>马良计划工作室 / Magic Leon Studio</b> &copy; 2026
</p>

<p align="center">
  <a href="./README.md">返回 README</a> |
  <a href="#redpepper-开发环境配置指南">返回顶部</a>
</p>
