<p align="center">
  <img src="assets/banner.png" alt="RedPepper Logo" width="1080">
</p> 

<h1 align="center"><img src="assets/logo-icon.png" alt="RedPepper Logo" width="32"> RedPepper 红椒</h1>

<p align="center">
  <b>A股个人投资基础设施 | dev. by Magic Leon Studio</b> <img src="assets/logo_mls.png" alt="Magic Leon Studio Logo" width="25"><br>
  <i>Your Personal Investment Digital Companion</i>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Version-v0.0.5-red" alt="Version v0.0.5">
  <img src="https://img.shields.io/badge/Python-3.10%2B-purple" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/License-MIT-yellow" alt="MIT License">
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-cyan" alt="Platform">
</p>

---

## 目录 / Table of Contents

- [项目简介 / Project Overview](#项目简介--project-overview)
- [项目定位 / Project Positioning](#项目定位--project-positioning)
- [功能特性 / Features](#功能特性--features)
- [Roadmap 开发路线图](#roadmap-开发路线图)
  - [Phase 1 — 基础框架（已完成）](#phase-1--基础框架已完成)
  - [Phase 2 — 智能增强（进行中）](#phase-2--智能增强进行中)
  - [Phase 3 — 知识深化（规划中）](#phase-3--知识深化规划中)
  - [Phase 4 — 手机版预研（规划中）](#phase-4--手机版预研规划中)
  - [当前版本进度快照（v0.0.5）](#当前版本进度快照v005)
- [开发日志 / Changelog](#开发日志--changelog)
- [技术架构 / Tech Stack](#技术架构--tech-stack)
- [快速开始 / Quick Start](#快速开始--quick-start)
- [首次使用流程 / First Time Setup](#首次使用流程--first-time-setup)
- [数据导入 / Data Import](#数据导入--data-import)
  - [截图 AI 导入](#截图-ai-导入)
  - [CSV 导入](#csv-导入)
  - [HTML 导入](#html-导入)
- [数据备份与恢复 / Backup & Restore](#数据备份与恢复--backup--restore)
- [双语切换 / Language Switching](#双语切换--language-switching)
- [AI 配置 / AI Configuration](#ai-配置--ai-configuration)
- [项目目录结构 / Directory Structure](#项目目录结构--directory-structure)
- [安全说明 / Security](#安全说明--security)
- [开发团队 / Team](#开发团队--team)

---

## 项目简介 / Project Overview

**当前版本：v0.0.5**

RedPepper（红椒）是一款面向 A 股个人投资者的本地桌面应用，聚焦“数据沉淀 + AI 辅助 + 本地安全”。

- 以账户持仓、交易记录、观察池、知识链接为核心的数据中台
- 以截图 OCR、新闻解读、日报生成为核心的 AI 助手能力
- 以本地 SQLite 与密钥本地管理为核心的隐私与安全策略

适合希望形成长期投资工作流、并且重视数据主权和可持续复盘的个人投资者。

---

## 项目定位 / Project Positioning

**RedPepper（红椒）** 是面向 A 股个人投资者的本地化数字帮手。

**它不是什么：**

- 不是自动化交易系统（不支持自动下单、策略回测）
- 不是实时行情工具（不提供 Level-2 行情、逐笔成交）
- 不是荐股软件（不给出买卖建议或预测涨跌）

**它是什么：**

- 你的个人投资数据中心 —— 聚合多账户持仓、观察池、交易记录
- 你的 AI 投资笔记 —— 截图 OCR、新闻分析、日报生成
- 你的知识管理工具 —— 聚合知乎、B站、网页链接等投资相关资料
- 你的本地安全堡垒 —— 所有数据本地存储，API Key 不上云

> **RedPepper** is a **localized digital companion** for individual A-share investors. It is **NOT** an automated trading system, **NOT** a real-time market data tool, and **NOT** a stock recommendation service. It is your personal investment data hub, AI-powered note-taking assistant, knowledge aggregator, and local security vault.

---

## 功能特性 / Features

### 数据中心化 / Data Centralization

| 功能 | 说明 | Status |
|------|------|--------|
| 多账户持仓管理 | 统一管理多个券商账户的持仓数据 | Phase 1 |
| 观察池 / Watchlist | 跟踪关注股票的动态与笔记 | Phase 2 |
| 交易记录 | 记录每笔操作的理由与复盘 | Phase 2 |
| 知识链接聚合 | 收藏知乎、B站、网页等投资相关资料 | Phase 1 |

### AI 辅助决策 / AI-Assisted Analysis

| 功能 | 说明 | Status |
|------|------|--------|
| 截图 OCR 导入 | 截图识别持仓数据，AI 自动解析入库 | Phase 1 |
| 新闻/公告分析 | AI 解读个股新闻，生成要点摘要 | Phase 2 |
| 投资日报生成 | 每日自动生成持仓简报与复盘日记 | Phase 2 |
| 双 AI 模型支持 | 支持 Kimi + DeepSeek 双模型切换 | Phase 2 |

### 合规安全 / Security & Compliance

| 功能 | 说明 | Status |
|------|------|--------|
| 本地化部署 | 所有数据存储在本地 SQLite 数据库 | Phase 1 |
| API Key 本地管理 | AI 密钥加密存储，不上传云端 | Phase 1 |
| 加密导出备份 | `.redpepper` 加密格式，安全迁移数据 | Phase 1 |
| 密码错误锁定 | 多次错误输入后自动锁定，防止暴力破解 | Phase 1 |

---

## Roadmap 开发路线图

### Phase 1 — 基础框架（已完成） / Foundation

**目标：建立安全可靠的本地化投资数据基础设施**

- [x] 用户认证系统（密码登录 + 错误锁定机制）
- [x] 持仓总览（多账户持仓数据集中展示）
- [x] 手动录入（股票代码、名称、成本、数量等字段）
- [x] 截图 AI 导入（OCR 识别 + AI 解析持仓截图）
- [x] 知识链接收藏（添加/编辑/分类管理网页链接）
- [x] 加密数据导出（`.redpepper` 格式备份与恢复）
- [x] 双语界面支持（中文/English 一键切换）

### Phase 2 — 智能增强（进行中） / Intelligence

**目标：引入 AI 能力，提升投资决策效率**

- [x] 观察池管理（基础 CRUD、导入、状态流转）
- [x] 操作日志（基础记录与回顾）
- [x] 双 AI 模型切换（Kimi + DeepSeek）
- [x] 截图两阶段导入（Kimi 提取 CSV + DeepSeek 结构化入库）
- [x] 文本导入收敛（CSV/纯文本统一入口）
- [x] 持仓与观察池同代码关联同步（导入后自动关联）
- [ ] 投资简报生成（自动化任务链路待完善）
- [ ] 投资日记（AI 深度复盘能力待完善）
- [x] AGI2Rich-Notebook HTML 导入（解析增强）

### Phase 3 — 知识深化（规划中） / Knowledge Deepening

**目标：构建投资知识闭环，提升长期复盘和决策质量**

- [ ] 知识聚合中心增强（知乎/B站/网页链接更完整提取）
- [ ] 知识图谱与关联分析（知识-知识、知识-标的）
- [ ] 自动化日报生成（定时任务与模板稳定）

### Phase 4 — 手机版预研（规划中） / Mobile Exploration

**目标：为后续移动端形态做技术预研与接口准备**

- [ ] 后端 API 文档化与移动端调用约束整理
- [ ] 移动端技术方案评估（React Native / Flutter / PWA）
- [ ] 与桌面端数据与权限模型对齐方案

### 当前版本进度快照（v0.0.5）

- 已完成：Phase 1 全量收口，Phase 2 关键数据链路可用（导入、关联、双模型、日志/简报/日记基础能力）
- 新增：知识库 AGI2Rich HTML 导入增强（多文件 + images 目录 + 自动标签 + 内嵌预览 + 本地浏览器预览 + 批量删除）
- 新增：截图导入重构为多图融合模式（Kimi 逐张 OCR + DeepSeek 跨图聚合 + 模糊名称匹配）；入库策略放宽为「有名称即可入库」，结合可编辑预览确保每次导入都有结果
- 新增：持仓与观察池分组双向同步（任一侧修改分组，另一侧自动跟随）
- 进行中：Phase 2 深化（简报/日记自动化、稳定性回归、可用性打磨）
- 规划中：Phase 3 知识深化、Phase 4 手机版预研
- 下一里程碑：v0.0.6 聚焦 Phase 2 自动化补齐与 Phase 3 知识能力扩展

---

## 开发日志 / Changelog

### v0.0.5-patch (2026-06-11)

本次补丁重点是"观察池文本导入鲁棒性 + 仪表盘模型对话能力 + Chat UI 体验升级"（不升级版本号）。

**观察池导入增强（文本/CSV统一 + DeepSeek补全）**
- 新增观察池 `/import-text` 后端入口：支持同花顺等原始文本粘贴导入，先宽松解析，再由 DeepSeek 归一化并补全代码/字段后入库
- `_import_watchlist_rows` 增加补全模式（upsert）：同代码命中已有条目时不再只计重复，可补齐已有条目的缺失字段
- 导入结果新增 `updated` 统计，并保持“去重 + 持仓状态同步”
- 剪贴板导入改为走文本导入链路，修复“无代码列/名称列别名不匹配导致整批失败”问题

**CSV/文本导入体验修复**
- 进度弹窗新增 text mode：文本导入不再显示“截图OCR导入”文案与截图预览框
- `api_client` 为 `/import-text` 与 `/api/ai/chat` 增加长超时策略，避免长文本/多附件请求过早超时

**仪表盘快捷操作与模型对话能力**
- 修复仪表盘“查看持仓”按钮无响应：补齐 dashboard -> main window 的导航信号与路由
- 新增仪表盘“模型对话”弹窗：支持模型切换 `kimi-k2.6` / `deepseek-v4-flash` / `deepseek-v4-pro`
- 新增后端 `/api/ai/chat` 路由与前端 `chat_service`，支持多轮上下文

**现代 Chat 交互升级（附件 + 气泡 + 代码复制）**
- 上传入口统一为“上传附件”，支持一次多选
- 按模型限制附件类型：
  - Kimi-k2.6：文本附件 + 图片附件（多图逐张识别后汇总）
  - DeepSeek-v4-flash/pro：文本附件
- 会话区升级为客户端风格：用户右侧气泡、模型左侧气泡、代码块卡片化并支持“复制代码”按钮
- 视觉主题回归主应用品牌色（紫色-黄色-西瓜红），不使用纯黑风格

**稳定性修复**
- 修复 Kimi 聊天 gateway 报错：按模型兼容性调整 temperature（Kimi 使用 1.0）

### v0.0.5-patch (2026-06-09)

本次补丁重点是"截图导入鲁棒性重构 + 持仓观察池分组双向同步 + 编辑体验修复"。

**截图导入重构（多图融合 + 永不失败）**
- 截图导入由单张改为多选，支持同时选择多张互补截图（如一张有代码、一张有市值）
- Kimi-k2.6 逐张 OCR 提取 CSV，新增 `/ocr-merge-normalize-csv` 端点，由 DeepSeek 将多张 CSV 跨图融合并结构化
- 新增 `_merge_portfolio_csv_rows` 合并函数，按名称归并行，后来的字段填补先前的空白，实现跨截图信息聚合
- 新增模糊名称匹配：剥离 ETF/LOF/基金/指数 等常见后缀后再比较，确保"科创50"与"科创50ETF"能识别为同一标的并合并
- DeepSeek prompt 增加规则：遇到相似名称主动合并，保留信息更完整的版本
- 后端入库校验放宽为"有名称即可入库"，证券代码可为空，key 用 `code or name:<name>` 兜底
- DeepSeek 归一化不再丢弃无代码行，服务层 `import_from_extracted_items` 增加 `allow_partial` 参数
- 导入前始终弹出可编辑预览（`_edit_items_before_import`），用户可补全缺失字段；不完整条目可先入库、后续在表格中编辑
- 修复之前补丁中 `import_from_screenshot_csv_text` 方法内引用未定义变量 `result`/`text` 导致运行时 NameError 的问题

**持仓与观察池分组双向同步**
- 新增 `_sync_portfolio_groups_from_watchlist_item` helper（watchlist.py）：观察池修改分组时，自动将同代码的所有持仓同步为相同分组
- 观察池的 `PUT /{id}`、`/grouping/auto`、`/grouping/semi`、`/grouping/manual` 四个写入端点均接入双向同步
- 修复持仓侧同步函数只在有分组名称时才写入的问题，现在清空分组也会同步清空观察池的对应分组

**稳定性修复**
- 修复在导入后的条目上点击「编辑」时，`QDoubleSpinBox.setValue` 收到 `None` 导致的 `TypeError`；四个数值字段（amount/profit/cost_price/shares）统一用 `or 0` 兜底

### v0.0.5 (2026-06-05)

本版本重点是“AGI2Rich 全链路导入扩展 + 知识库渲染体验修复 + 文档与版本收口”。

**交易/简报/日记导入增强**
- 交易日志支持 AGI2Rich HTML 导入，补充代码关联、导入进度与结果统计
- 修复交易日志 AGI2Rich HTML 导入后“理由”字段可能截断的问题，增强 JS 字符串解析兼容性
- 市场简报支持 AGI2Rich HTML 导入（简报/事件/持仓影响信息）
- 投资日记支持 AGI2Rich HTML 导入，并统一中英文文案

**知识库能力升级**
- 新增知识库 HTML 批量导入（支持多文件）
- 支持 images 图片目录解析，尽可能保留原文资源引用
- 根据文档内容自动打标签（analysis/tech/product/finance/robotics/general）
- 新增内嵌预览、预览缩放、单删与批量删除
- 新增“本地浏览器预览”按钮，直接调用系统浏览器渲染原始 HTML，规避内嵌渲染兼容差异

**稳定性与兼容修复**
- 补充知识库历史数据兼容：缺失 content_html 时可从原始 URL 回读 HTML
- 优化 Windows 下 Qt 插件路径引导，降低 PyQt/Qt 环境混装导致的启动失败概率
- 持仓导入改为“以待导入数据为准”的增删改同步逻辑，并按最终持仓状态回写观察池
- 修复基金/股票分来源导入互相冲刷的问题，对齐范围改为按账户与类型限定
- 仪表盘总览改为随持仓变更自动刷新，新增、编辑、删除、批量删除、导入后都会联动更新

**工程与文档**
- 完善 README 的 HTML 导入说明与版本快照
- 同步版本至 v0.0.5，并准备发布标记
- 持仓页新增批量删除能力；简报页面将“手动记录 / 添加事件”调整为弹窗模式，为详情展示释放更多空间

### v0.0.4 (2026-06-04)

本版本重点是“导入可靠性 + 数据一致性 + 体验修复”。

**导入链路升级**
- 持仓截图导入升级为两阶段：Kimi-k2.6 先提取 CSV，再由 DeepSeek-v4-flash 结构化入库
- 新增截图提取结果实时确认环节，支持人工校正后再入库
- CSV 与文本导入入口统一为文本导入，简化用户路径

**数据一致性增强**
- 持仓与观察池在导入后按股票代码自动关联，减少重复维护
- 持仓/观察池导入流程补充关联回写与状态映射

**稳定性与界面修复**
- 修复多个页面数值空值导致的格式化异常
- 仪表盘改为真实全局总览口径，并修复关键文案与 i18n 键
- 统一处理部分页面标题文字显示不全问题
- 登录页完成品牌化重构，支持 RedPepper 与 MLS 双 Logo 并排展示

**工程侧清理**
- 清理无用测试与探针脚本，降低仓库噪音

---

## 技术架构 / Tech Stack

| 层级 | 技术选型 | 说明 |
|------|---------|------|
| 前端 GUI | PyQt6 | 跨平台桌面应用框架 |
| 后端 API | FastAPI | 高性能异步 Python Web 框架 |
| 数据库 | SQLite3 | 轻量级本地嵌入式数据库 |
| AI 服务 | Kimi API / DeepSeek API | 大语言模型能力接入 |
| OCR 能力 | 多模态 LLM | 基于视觉能力的截图识别 |
| 加密方案 | PBKDF2 + AES-256-GCM | 军事级数据加密标准 |
| 打包工具 | PyInstaller | 独立可执行文件构建 |

```
┌─────────────────────────────────────────┐
│           PyQt6 桌面前端                  │
│  (持仓界面 / 观察池 / 设置 / 日记)         │
├─────────────────────────────────────────┤
│         FastAPI 本地服务层                │
│  (REST API / 认证 / AI 代理 / 文件处理)     │
├─────────────────────────────────────────┤
│         SQLite3 本地数据库                │
│  (持仓表 / 用户表 / 配置表 / 日志表)        │
├─────────────────────────────────────────┤
│      AI 云服务 (Kimi / DeepSeek)          │
│  (OCR 识别 / 文本分析 / 内容生成)          │
└─────────────────────────────────────────┘
```

---

## 快速开始 / Quick Start

### 方式一：源码运行 / Run from Source (Anaconda)

```bash
# 1. 克隆仓库 / Clone repository
git clone https://github.com/MagicLeonStudio/RedPepper.git
cd RedPepper/redpepper

# 2. 创建 Conda 环境（推荐）/ Create conda environment
conda env create -f environment.yml

# 3. 激活环境 / Activate environment
conda activate redpepper

# 4. 起动
# 终端 1：启动后端
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
# 终端 2：启动前端
python -m frontend.main
```

也可以只启动前端，应用会自动拉起本地后端：

```bash
cd RedPepper/redpepper
conda activate redpepper
python -m frontend.main
```

> **为什么用 Conda？** Conda 对 PyQt6、cryptography 等含 C 扩展的包管理更可靠，跨平台一致性好，避免编译错误。这也是本项目推荐的开发方式。

**如果你没有 Anaconda**，也可以用 Miniconda 或 pip：

```bash
# 备用：pip 方式
pip install -r requirements.txt
python -m frontend.main
```

### 方式二：可执行文件 / Pre-built Binary

下载对应平台的 `.exe`（Windows）或 `.app`（macOS）文件，双击运行即可。

> 详细环境配置请参见 [SETUP.md](./SETUP.md)

---

## 首次使用流程 / First Time Setup

首次启动 RedPepper 时，请按以下步骤完成初始化：

### Step 1: 设置主密码

```
┌──────────────────────────────────────┐
│      RedPepper 首次使用               │
│                                      │
│  请设置您的主密码                     │
│  此密码用于加密保护所有投资数据        │
│                                      │
│  [输入密码...]                       │
│  [确认密码...]                       │
│                                      │
│  密码要求：至少8位，包含字母和数字      │
│                                      │
│         [ 确认设置 ]                  │
└──────────────────────────────────────┘
```

**注意**：主密码是加密密钥的衍生基础，**无法找回**，请务必牢记。

### Step 2: 进入主界面

设置密码后自动进入主界面，左侧为功能导航栏：

| 导航项 | 功能 |
|--------|------|
| 持仓总览 | 查看所有账户的持仓分布与盈亏 |
| 观察池 | 管理关注股票列表（Phase 2） |
| 知识库 | 收藏的投资文章、视频链接 |
| 设置 | AI 配置、语言切换、数据导入/导出 |

### Step 3: 配置 AI（可选）

进入「设置 → AI 配置」，输入 Kimi 或 DeepSeek 的 API Key，启用 AI 功能。详见 [AI 配置](#ai-配置--ai-configuration)。

---

## 数据导入 / Data Import

RedPepper 支持多种方式将现有投资数据导入系统。

### 截图 AI 导入

适用于：券商 App 持仓截图、网页持仓页面截图

1. 打开券商 App 或网页，截取**持仓页面**完整截图
2. 在 RedPepper 中点击「导入 → 截图导入」
3. 选择截图文件（支持 PNG、JPG、JPEG 格式）
4. AI 自动识别截图中的股票代码、名称、成本、数量等信息
5. 核对识别结果，确认后导入数据库

```
支持格式：PNG, JPG, JPEG
截图建议：确保股票代码、成本价、持仓数量清晰可见
处理时间：通常 3-10 秒（取决于网络状况）
```

**示例截图位置：**
```
[截图位置：截图导入界面示例]
assets/screenshots/import_screenshot.png
```

### CSV 导入

适用于：Excel 整理的历史持仓数据（Phase 2）

CSV 文件格式要求：

```csv
stock_code,stock_name,cost_price,quantity,account_name
600519,贵州茅台,1680.50,100,账户A
000858,五粮液,152.30,200,账户A
300750,宁德时代,198.00,50,账户B
```

| 字段 | 必填 | 说明 |
|------|------|------|
| stock_code | 是 | 6位股票代码 |
| stock_name | 是 | 股票名称 |
| cost_price | 是 | 成本价（元） |
| quantity | 是 | 持仓数量（股） |
| account_name | 否 | 账户名称，不填则为"默认账户" |

### HTML 导入

适用于：AGI2Rich-Notebook 导出的研究文章 HTML（analysis / techblog / product 等）

已支持能力：

- 支持一次选择多个 HTML 文件批量导入
- 支持额外选择 images 图片目录（可选），用于还原文档中的本地图片资源
- 导入后自动按文档内容打标签（如 analysis / tech / product / finance / robotics）
- 知识库页面内嵌原文渲染（右侧预览区），尽量保留原始 CSS/布局与视觉效果
- 支持单条删除与批量删除
- 支持本地浏览器预览（原始 HTML 渲染）

导入步骤：

1. 进入「知识库」页面，点击「导入 HTML」
2. 在文件框中多选 `.html/.htm` 文件
3. 若文档引用本地图片，按提示选择 `images` 目录（可选）
4. 导入完成后，在左侧列表选择条目，右侧查看内嵌渲染效果

推荐目录结构：

```text
assets/
  html_assets/
    analysis-1-xxx.html
    analysis-2-xxx.html
    product-1-xxx.html
    images/
      xxx.png
      yyy.jpg
```

---

## 数据备份与恢复 / Backup & Restore

### 加密导出

RedPepper 使用 `.redpepper` 专有格式进行数据备份，所有数据均通过 AES-256-GCM 加密。

**导出步骤：**

1. 进入「设置 → 数据管理 → 导出备份」
2. 选择导出路径
3. 系统将生成 `[日期]_[随机串].redpepper` 文件
4. 妥善保管该文件和您的主密码

```bash
# 导出文件示例
redpepper_20260115_a3f8e2.redpepper
```

### 导入恢复

**恢复步骤：**

1. 进入「设置 → 数据管理 → 导入恢复」
2. 选择 `.redpepper` 备份文件
3. 输入该备份创建时的主密码
4. 数据将完全恢复到备份时的状态

> **警告**：导入恢复将**覆盖当前所有数据**，请谨慎操作。

---

## 双语切换 / Language Switching

RedPepper 支持中文和 English 两种界面语言。

**切换方式：**

1. 点击主界面右上角语言切换按钮
2. 或在「设置 → 通用 → 语言」中选择

```python
# 语言配置存储于 SQLite 配置表
# 切换后立即生效，无需重启
```

| 语言 | 覆盖率 | 状态 |
|------|--------|------|
| 中文 (zh-CN) | 100% | 完整支持 |
| English (en) | 100% | 完整支持 |

---

## AI 配置 / AI Configuration

RedPepper 支持接入 Kimi 和 DeepSeek 两家大语言模型服务。

### Kimi (Moonshot AI)

1. 访问 [platform.moonshot.cn](https://platform.moonshot.cn)
2. 注册账号并登录
3. 进入「API Key 管理」页面
4. 点击「创建 API Key」
5. 复制生成的 Key

```yaml
# 配置示例
AI Provider: Kimi
API Key: sk-your-kimi-api-key-here
Model: moonshot-v1-8k  # 可选: 8k / 32k / 128k
```

### DeepSeek

1. 访问 [platform.deepseek.com](https://platform.deepseek.com)
2. 注册账号并登录
3. 进入「API Keys」页面
4. 点击「创建 API Key」
5. 复制生成的 Key

```yaml
# 配置示例
AI Provider: DeepSeek
API Key: sk-your-deepseek-api-key-here
Model: deepseek-chat  # 或 deepseek-reasoner
```

### 双模型切换

在「设置 → AI 配置」中可自由切换主用模型：

| 模型 | 优势场景 | Token 限制 |
|------|---------|-----------|
| Kimi | 长文本处理、大量持仓分析 | 128K |
| DeepSeek | 深度推理、复杂分析任务 | 64K |

> 两个模型的 API Key 可同时保存，使用时即时切换，无需重复输入。

---

## 项目目录结构 / Directory Structure

```
redpepper/
├── frontend/                   # PyQt6 桌面前端
│   ├── __init__.py
│   ├── main.py                 # GUI 应用入口
│   ├── windows/                # 页面窗口
│   │   ├── login_window.py     # 登录/设密窗口
│   │   ├── main_window.py      # 主窗口（侧边栏导航）
│   │   ├── dashboard_page.py   # 总览页
│   │   ├── portfolio_page.py   # 持仓页
│   │   ├── watchlist_page.py   # 观察池页
│   │   ├── trade_log_page.py   # 操作日志页
│   │   ├── briefing_page.py    # 简报页
│   │   ├── diary_page.py       # 日记页
│   │   ├── knowledge_page.py   # 知识聚合页
│   │   └── settings_page.py    # 设置页
│   ├── widgets/                # 可复用组件
│   │   └── language_switcher.py # 语言切换器
│   ├── services/               # API 调用服务层
│   │   ├── api_client.py
│   │   ├── auth_service.py
│   │   ├── portfolio_service.py
│   │   └── ...
│   └── resources/              # 静态资源
│       └── style.qss           # 深色主题样式表
├── assets/                     # 品牌资源
│   ├── logo.png                # 登录页 / 首页完整 Logo
│   └── logo-icon.png           # 软件缩略图标
├── backend/                    # FastAPI 后端服务
│   ├── app/
│   │   ├── main.py             # FastAPI 入口
│   │   ├── models.py           # 9 个 SQLAlchemy ORM 模型
│   │   ├── schemas.py          # Pydantic 数据模型
│   │   ├── security.py         # 密码哈希 + AES-256-GCM 加密
│   │   ├── database.py         # SQLite 连接管理
│   │   ├── config.py           # YAML 配置管理
│   │   ├── ai/                 # AI Provider 模块
│   │   │   ├── base.py         # 抽象基类
│   │   │   ├── kimi_provider.py    # Kimi (Moonshot)
│   │   │   ├── deepseek_provider.py # DeepSeek
│   │   │   └── factory.py      # 工厂方法
│   │   └── routers/            # 8 个 API 路由
│   │       ├── auth.py
│   │       ├── portfolio.py
│   │       ├── watchlist.py
│   │       ├── trade_log.py
│   │       ├── briefing.py
│   │       ├── diary.py
│   │       ├── knowledge.py
│   │       └── data_manager.py
│   └── config.yaml             # AI/服务器配置
├── environment.yml             # Conda 环境配置（推荐）
├── requirements.txt            # pip 依赖（备用）
├── README.md                   # 项目说明（本文档）
├── SETUP.md                    # 开发环境配置
└── .gitignore
```

---

## 安全说明 / Security

RedPepper 采用多层安全机制保护您的投资数据。

### 密码派生 / Password Derivation

```
主密码 → PBKDF2-HMAC-SHA256 (100,000 迭代) → 256-bit 密钥
```

- 使用 PBKDF2 算法进行密钥派生
- 迭代次数：100,000 次
- 盐值：每次初始化随机生成 16 字节

### 数据加密 / Data Encryption

```
明文数据 → AES-256-GCM → 密文数据
```

- 算法：AES-256-GCM（Galois/Counter Mode）
- 密钥长度：256 位
- 认证标签：确保数据完整性与真实性

### 错误锁定机制 / Brute Force Protection

| 连续错误次数 | 锁定时间 |
|-------------|---------|
| 1-2 次 | 无锁定 |
| 3-4 次 | 30 秒 |
| 5-6 次 | 5 分钟 |
| 7+ 次 | 30 分钟 |

> 所有安全参数均可通过配置文件调整，详见 [SETUP.md](./SETUP.md)。

### 安全实践建议

1. 设置强主密码（至少 12 位，含大小写字母、数字、符号）
2. 定期导出 `.redpepper` 备份文件
3. 将备份文件存储在安全位置（如加密 U 盘）
4. 不在公共电脑上保存主密码
5. API Key 仅存储在本地，不随数据导出

---

## 开发团队 / Team

<p align="center">
  <b>马良计划工作室 / Magic Leon Studio</b>
</p>

<p align="center">
  2026 &copy; All Rights Reserved
</p>

<p align="center">
  <i>用心做好每一件投资工具</i>
</p>

---

## 许可证 / License

本项目采用 [MIT License](LICENSE) 开源协议。

---

<p align="center">
  <a href="#redpepper-红椒">返回顶部 / Back to Top</a>
</p>
