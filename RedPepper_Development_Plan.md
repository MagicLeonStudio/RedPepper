# <span style="color:#C23B22">RedPepper</span> <span style="color:#7B4B8C">开发计划书</span>

> <span style="color:#D4A017">A股个人投资基础设施 | v0.1</span>  
> <span style="color:#D4A017">马良计划工作室 | 2026年5月</span>

---

## <span style="color:#C23B22">目录</span>

- [一、项目概述](#一项目概述)
  - [1.1 项目背景](#11-项目背景)
  - [1.2 项目定位与核心目标](#12-项目定位与核心目标)
- [二、技术架构](#二技术架构)
  - [2.1 架构选型与系统架构](#21-架构选型与系统架构)
  - [2.2 技术栈详情](#22-技术栈详情)
- [三、数据模型](#三数据模型)
- [四、功能模块](#四功能模块)
  - [4.1 数据导入中心](#41-数据导入中心)
  - [4.2 持仓总览与观察池](#42-持仓总览与观察池)
  - [4.3 操作日志与简报日记](#43-操作日志与简报日记)
  - [4.4 知识聚合中心](#44-知识聚合中心)
  - [4.5 用户认证与数据管理](#45-用户认证与数据管理)
- [五、AI API 集成方案](#五-ai-api-集成方案)
  - [5.1 Kimi API 方案](#51-kimi-api-方案)
  - [5.2 DeepSeek API 方案](#52-deepseek-api-方案)
  - [5.3 统一抽象层设计](#53-统一抽象层设计)
- [六、开发路线图](#六开发路线图)
- [七、配置与安全](#七配置与安全)
  - [7.1 用户密码体系](#71-用户密码体系)
  - [7.2 数据导出加密方案](#72-数据导出加密方案)
  - [7.3 API Key 管理](#73-api-key-管理)
  - [7.4 数据安全](#74-数据安全)
- [八、风险与应对](#八风险与应对)

---

## <span style="color:#C23B22">一、项目概述</span>

### <span style="color:#7B4B8C">1.1 项目背景</span>

AGI2Rich 是一个基于静态 HTML 的个人投资追踪工具，通过截图与 KimiClaw 互动来更新投资数据。随着持仓规模扩大、观察池墨客等需求增长，单页面 HTML 的维护成本越来越高，需要升级为完整的桌面应用。

<span style="color:#C23B22">**RedPepper（红椒）**</span> 作为 AGI2Rich 的升级版本，定位为 **A股个人炒股/基金基础设施（Infra）**，旨在为个人投资者提供一站式的数据管理、情报聚合与决策辅助工具。

### <span style="color:#7B4B8C">1.2 项目定位与核心目标</span>

RedPepper 的核心定位是"<span style="color:#D4A017">个人投资的数字帮手</span>"，不是自动化交易系统，也不是实时行情工具，而是聚焦以下 **四个核心目标**：

| 目标 | 说明 |
|------|------|
| <span style="color:#C23B22">**数据中心化**</span> | 统一管理多账户的持仓、观察池、交易记录，消灭分散在各平台的信息孤岛 |
| <span style="color:#7B4B8C">**AI 辅助决策**</span> | 通过多模型 API 接入，实现截图识别、新闻分析、日报生成等智能功能 |
| <span style="color:#D4A017">**知识聚合**</span> | 收纳知乎文章、B站视频、行业报告等外部信息源，构建个人投资知识图谱 |
| <span style="color:#C23B22">**合规安全**</span> | 本地化部署，API Key 不上云，交易数据不经第三方服务器 |

---

## <span style="color:#C23B22">二、技术架构</span>

### <span style="color:#7B4B8C">2.1 架构选型与系统架构</span>

RedPepper 采用 **前后端分离** 的架构设计，前端为 PyQt6 桌面应用，后端为 FastAPI 提供的本地 HTTP 服务（`localhost:8000`）。这种架构的优势在于：

- **<span style="color:#C23B22">API Key 安全</span>**：Kimi/DeepSeek API Key 存储在 Python 后端，前端无法查看
- **<span style="color:#7B4B8C">本地文件访写</span>**：数据库、配置文件、缓存全部落地本地
- **<span style="color:#D4A017">可扩展性</span>**：后期手机版可直接复用同一套后端 API
- **<span style="color:#C23B22">打包友好</span>**：通过 PyInstaller 可打包为单文件可执行程序

### <span style="color:#7B4B8C">2.2 技术栈详情</span>

| 层级 | 技术选型 | 说明 |
|:------|:----------|:------|
| 前端 GUI | <span style="color:#C23B22">**PyQt6 / PySide6**</span> | 桌面应用，跨平台、功能丰富 |
| 后端 API | <span style="color:#7B4B8C">**FastAPI (Python)**</span> | 高性能异步框架，自动生成 API 文档 |
| 数据库 | <span style="color:#D4A017">**SQLite**</span> | 单文件、零配置、足够个人使用 |
| 打包工具 | <span style="color:#C23B22">**PyInstaller / Nuitka**</span> | 单文件可执行程序，便于分发 |
| HTTP 通信 | <span style="color:#7B4B8C">**httpx / aiohttp**</span> | 异步调用 AI API，支持流式输出 |

---

## <span style="color:#C23B22">三、数据模型</span>

数据库采用 <span style="color:#D4A017">**SQLite**</span>，单文件存储，无需额外安装数据库服务。核心数据表设计如下：

| 表名 | 数据量级 | 核心字段 |
|:------|:----------|:----------|
| `portfolio` | ~100条 | code, name, amount, profit, cost_price, account |
| `watchlist` | ~200条 | code, name, sector, rating, trigger_condition |
| `trade_log` | ~500条 | date, name, action, amount, reason, emotion |
| `briefing` | ~100条 | date, overseas, domestic, market, summary |
| `diary` | ~50条 | date, best_op, worst_op, reflection, focus |
| `knowledge` | ~1000条 | url, title, source, tags, summary, related_stocks |
| `user` | 1条 | password_hash, salt, created_at, last_login |
| `data_backup` | ~50条 | backup_id, created_at, file_path, checksum, size |

其中 `knowledge` 表用于存储知乎文章、B站视频、网页链接等外部知识来源，支持全文搜索、标签分类、知识关联等功能。

<span style="color:#C23B22">**用户认证说明**</span>：`user` 表存储主密码的哈希值和盐值，<span style="color:#D4A017">**明文密码永不保存**</span>，验证时通过 PBKDF2-HMAC-SHA256 比对哈希值。`data_backup` 表记录每次导出的备份元信息，用于管理和追溯历史备份。

---

## <span style="color:#C23B22">四、功能模块</span>

### <span style="color:#7B4B8C">4.1 数据导入中心</span>

支持多种数据导入方式，覆盖主要使用场景：

| 导入方式 | 说明 |
|:----------|:------|
| <span style="color:#C23B22">**截图 + AI OCR**</span> | 截取同花顺/中信软件截图，调用 Kimi/DeepSeek Vision API 识别并导入持仓、收益等数据 |
| <span style="color:#7B4B8C">**CSV/Excel 导入**</span> | 支持同花顺 PC 客户端导出的交割单/对账单 CSV |
| <span style="color:#D4A017">**HTML/MD 导入**</span> | 支持原 AGI2Rich 的 HTML 文件导入，完全兼容历史数据 |

### <span style="color:#7B4B8C">4.2 持仓总览与观察池</span>

- **<span style="color:#C23B22">持仓总览</span>**：多账户汇总（中信/同花顺），实时盈亏、行业分布、集中度警报
- **<span style="color:#7B4B8C">观察池</span>**：股票/ETF/基金分类管理，支持评级、触发条件、状态流转（观察→买入→持有）

### <span style="color:#7B4B8C">4.3 操作日志与简报日记</span>

| 模块 | 功能 |
|:------|:------|
| 操作日志 | 记录每笔交易的日期、标的、金额、理由，支持情绪追踪 |
| 简报系统 | 自动生成日报（09:29 开盘、12:00 AI新闻、15:04 收盘），支持手动补录 |
| 投资日记 | 每周复盘，包含最满意/最丢人的操作、决策复盘、下周关注 |

### <span style="color:#7B4B8C">4.4 知识聚合中心</span>

这是 RedPepper 的**核心差异化功能**，支持以下知识来源：

| 来源 | 接入方式 | 数据提取 |
|:------|:----------|:----------|
| <span style="color:#C23B22">**知乎文章**</span> | 复制链接 → 后端抓取 | 标题/作者/正文 → AI 生成摘要与标签 |
| <span style="color:#7B4B8C">**B站视频**</span> | 提取 BV 号 → B站公开 API | 视频信息/简介 → 提取股票代码 |
| <span style="color:#D4A017">**网页链接**</span> | 通用 URL 抓取 | 行业报告、研究报告等 |

**知识图谱**：知识与知识关联（引用/矛盾/延伸）、知识与股票关联（买入理由/风险提醒）

### <span style="color:#7B4B8C">4.5 用户认证与数据管理</span>

RedPepper 将用户数据安全置于最高优先级，所有个人交易、持仓信息均存储在本地加密数据库中。首次启动必须设置主密码，后续凭密码登录使用。

#### <span style="color:#C23B22">首次启动流程</span>

```
启动 RedPepper
    │
    ▼
检测是否存在 user 表记录
    │
    ├── 否 ──▶ 显示「设置主密码」界面
    │            │
    │            ▼
    │        用户输入密码（≥8位，含字母+数字）
    │            │
    │            ▼
    │        生成随机盐值(salt)
    │            │
    │            ▼
    │        PBKDF2-HMAC-SHA256(password, salt, 100000次)
    │            │
    │            ▼
    │        保存 password_hash + salt 到 user 表
    │            │
    │            ▼
    │        初始化空数据库，进入主界面
    │
    └── 是 ──▶ 显示「登录」界面
                 │
                 ▼
             用户输入密码
                 │
                 ▼
             用保存的 salt 重新计算哈希
                 │
                 ▼
             比对 password_hash
                 │
            匹配 ──▶ 解密数据库，进入主界面
                 │
            不匹配 ──▶ 提示密码错误，3次失败后锁定5分钟
```

#### <span style="color:#7B4B8C">数据导出机制</span>

| 功能 | 说明 |
|:------|:------|
| **一键导出** | 菜单「数据管理」→「导出全部数据」，选择保存路径 |
| **导出内容** | 完整 SQLite 数据库（portfolio/watchlist/trade_log/briefing/diary/knowledge 全表） |
| **加密方式** | AES-256-GCM 加密，密钥由「用户密码 + 随机盐」派生 |
| **文件格式** | `.redpepper` 后缀（实际为加密后的 SQLite 文件 + 元数据头） |
| **元数据** | 包含导出时间、版本号、数据量统计、完整性校验和 |

**导出流程**：
```
用户发起导出
    │
    ▼
读取当前 SQLite 数据库文件
    │
    ▼
生成 256-bit 随机盐值
    │
    ▼
派生加密密钥 = PBKDF2(user_password, salt, 100000)
    │
    ▼
AES-256-GCM 加密数据库文件
    │
    ▼
写入文件头（RedPepper格式标识 + 版本 + 盐值 + 时间戳 + 校验和）
    │
    ▼
输出 .redpepper 文件
```

#### <span style="color:#D4A017">数据导入机制（跨版本迁移）</span>

| 功能 | 说明 |
|:------|:------|
| **导入入口** | 启动时检测 / 菜单「数据管理」→「导入数据」 |
| **验证流程** | 要求输入导出时使用的密码 → 解密验证 → 校验完整性 |
| **数据兼容** | 自动检测导出文件的版本号，执行 schema 迁移（如有变更） |
| **导入策略** | 支持「覆盖」和「合并」两种模式 |

**导入流程**：
```
用户选择 .redpepper 文件
    │
    ▼
读取文件头，解析版本号和盐值
    │
    ▼
用户输入密码
    │
    ▼
派生密钥 = PBKDF2(password, salt, 100000)
    │
    ▼
AES-256-GCM 解密
    │
    ▼
校验完整性（SHA-256 比对）
    │
    ├── 校验失败 ──▶ 提示「文件损坏或密码错误」
    │
    └── 校验成功 ──▶ 检测 schema 版本
                          │
                    当前版本 ──▶ 直接导入
                          │
                    旧版本 ──▶ 自动执行迁移脚本
                          │
                          ▼
                     导入成功，刷新界面
```

#### <span style="color:#C23B22">密码管理</span>

| 功能 | 说明 |
|:------|:------|
| **修改密码** | 菜单「设置」→「修改主密码」，需验证旧密码后重新加密数据库 |
| **密码重置** | 本地应用无后门，密码重置 = 数据清空重来，需二次确认 |
| **自动锁定** | 连续 3 次密码错误锁定 5 分钟，连续 10 次锁定 30 分钟 |
| **安全策略** | 最小 8 位，必须包含字母+数字，建议 12 位以上 |

---

## <span style="color:#C23B22">五、AI API 集成方案</span>

RedPepper 的核心竞争力之一在于 AI 能力的深度集成。本方案同时支持 <span style="color:#C23B22">**Kimi**</span> 和 <span style="color:#7B4B8C">**DeepSeek**</span> 两大模型平台，用户可根据场景和成本灵活切换。

### <span style="color:#C23B22">5.1 Kimi API 方案</span>

#### 5.1.1 基本信息

| 项目 | 内容 |
|:------|:------|
| 平台 | Moonshot AI（月之暗面），地址：platform.moonshot.cn |
| 核心模型 | <span style="color:#C23B22">**K2.6**</span>，支持视觉感知与深度推理 |
| Vision 能力 | 支持截图识别，用于持仓截图导入、K线图分析 |
| 计费方式 | 按 Token 消耗付费，输入+输出分别计费 |

#### 5.1.2 API Key 申请流程

1. 访问 platform.moonshot.cn 注册开发者账号
2. 完成实名认证（个人/企业）
3. 创建 API Key，复制保存（只显示一次）
4. 新用户通常有 <span style="color:#D4A017">**15 元免费额度**</span>
5. 在 RedPepper 后端配置文件 config.yaml 中填入 Key

#### 5.1.3 核心使用场景

| 使用场景 | 调用方式 | 预期效果 |
|:----------|:----------|:----------|
| 截图导入持仓 | Vision API + prompt | 自动识别持仓名称、代码、盈亏 |
| 日报生成 | Chat API + 新闻数据 | 自动生成结构化日报 |
| 知识摘要 | Chat API + 文章内容 | 提取要点、生成标签 |

---

### <span style="color:#7B4B8C">5.2 DeepSeek API 方案</span>

#### 5.2.1 基本信息

| 项目 | 内容 |
|:------|:------|
| 平台 | DeepSeek AI，地址：platform.deepseek.com |
| 核心模型 | <span style="color:#7B4B8C">**DeepSeek-V4**</span>（通用+推理），性价比极高 |
| 特色能力 | R1 模型支持连续推理，适合投资分析、策略回测 |
| 计费方式 | 按 Token 消耗付费，价格显著低于 Kimi |

#### 5.2.2 API Key 申请流程

1. 访问 platform.deepseek.com 注册并登录账号
2. 进入 API Keys 页面，点击创建 API Key
3. 复制 Key 并保存到安全位置（只显示一次）
4. 新用户通常有 <span style="color:#D4A017">**5000 万 Token 免费额度**</span>
5. 在 RedPepper 后端配置文件 config.yaml 中填入 Key

#### 5.2.3 核心使用场景

| 使用场景 | 调用方式 | 预期效果 |
|:----------|:----------|:----------|
| 策略回测分析 | <span style="color:#7B4B8C">**V4 模型**</span> + 历史数据 | 深度推理交易策略效果 |
| 日报/日记生成 | <span style="color:#7B4B8C">**V4 模型**</span> + prompt | 高性价比的文本生成 |
| 知识摘要与分类 | <span style="color:#7B4B8C">**V4 模型**</span> + 文章 | 快速摘要、关键词提取 |
| 代码分析 | <span style="color:#7B4B8C">**V4 模型**</span> + 代码片段 | 分析财务数据、生成报告 |

---

### <span style="color:#D4A017">5.3 统一抽象层设计</span>

为了让两个模型平台可以无缝切换，RedPepper 设计了一套统一的 <span style="color:#C23B22">**AI Provider 抽象层**</span>：

#### 5.3.1 接口抽象

```python
# 统一的 AI Provider 接口
from abc import ABC, abstractmethod

class AIProvider(ABC):
    @abstractmethod
    def chat(self, messages, model=None, temperature=0.7):
        """通用对话"""
        pass

    @abstractmethod
    def vision(self, image_base64, prompt, model=None):
        """图像识别"""
        pass

    @abstractmethod
    def embed(self, texts, model=None):
        """文本嵌入"""
        pass

# 具体实现
class KimiProvider(AIProvider):
    """Kimi (Moonshot) 实现"""
    pass

class DeepSeekProvider(AIProvider):
    """DeepSeek 实现"""
    pass

# 工厂方法
PROVIDERS = {
    "kimi": KimiProvider,
    "deepseek": DeepSeekProvider,
}

def get_provider(name: str) -> AIProvider:
    return PROVIDERS[name]()
```

#### 5.3.2 配置方式

```yaml
# config.yaml - AI 模型配置
ai:
  default_provider: "deepseek"  # 默认使用 DeepSeek（性价比最高）
  
  providers:
    kimi:
      api_key: "sk-xxxxxxxx"
      base_url: "https://api.moonshot.cn/v1"
      default_model: "k2.6"
    
    deepseek:
      api_key: "sk-xxxxxxxx"
      base_url: "https://api.deepseek.com/v1"
      default_model: "deepseek-v4"
  
  # 场景级别模型选择（智能路由）
  scene_models:
    screenshot_ocr: "kimi"         # 截图识别用 Kimi（Vision 能力强）
    daily_report: "deepseek"       # 日报生成用 DeepSeek（便宜）
    knowledge_digest: "deepseek"   # 知识摘要用 DeepSeek
    strategy_analysis: "deepseek"  # 策略分析用 DeepSeek V4（推理强）
    code_analysis: "deepseek"      # 代码分析用 DeepSeek
```

#### 5.3.3 成本对比

| 项目 | Kimi | DeepSeek | <span style="color:#D4A017">**推荐**</span> |
|:------|:------|:----------|:-------------|
| 普通对话 (1M tokens) | ¥12 / ¥12 | ¥2 / ¥8 | **<span style="color:#7B4B8C">DeepSeek</span>** |
| 截图识别 (次) | ~¥0.006 | ¥0.003~¥0.006 | **<span style="color:#C23B22">Kimi</span>** |
| 日报生成 (次) | ~¥0.05 | ~¥0.01 | **<span style="color:#7B4B8C">DeepSeek</span>** |
| 月度估算 (日报x30) | ~¥1.5 | ~¥0.3 | **<span style="color:#7B4B8C">DeepSeek</span>** |
| 免费额度 | 15元 | 5000万 tokens | - |

> <span style="color:#D4A017">**成本优化建议**：日常使用 DeepSeek 降低成本，截图识别等 Vision 场景使用 Kimi，月度总成本可控制在 ¥1 以内。</span>

---

## <span style="color:#C23B22">六、开发路线图</span>

### <span style="color:#C23B22">Phase 1 — MVP 最小可用产品（4周）</span>

| 周次 | 任务 | 产出 |
|:------|:------|:------|
| Week 1-2 | 项目框架搭建（PyQt6 + FastAPI + SQLite），数据库设计与实现 | 可运行的基础框架 |
| Week 2-3 | 持仓总览页面，支持手动录入持仓数据 | 持仓管理功能 |
| Week 3-4 | 截图 + Kimi OCR 导入功能，完成核心闭环验证 | MVP 可验证版本 |

### <span style="color:#7B4B8C">Phase 2 — 功能完善（4周）</span>

| 周次 | 任务 | 产出 |
|:------|:------|:------|
| Week 5-6 | 观察池、操作日志、简报/日记模块 | 完整功能模块 |
| Week 6-7 | DeepSeek API 集成，实现双模型切换 | AI 能力升级 |
| Week 7-8 | CSV/HTML/MD 导入导出，数据备份与迁移 | 数据互通能力 |

### <span style="color:#D4A017">Phase 3 — 知识深化（3周）</span>

| 周次 | 任务 | 产出 |
|:------|:------|:------|
| Week 9-10 | 知识聚合中心（知乎/B站/网页链接导入） | 知识库功能 |
| Week 10-11 | 知识图谱与关联分析 | 知识关联能力 |
| Week 11-12 | 自动化日报生成，定时任务调度 | 自动化能力 |

### <span style="color:#C23B22">Phase 4 — 手机版预研（2周）</span>

| 周次 | 任务 | 产出 |
|:------|:------|:------|
| Week 13 | 后端 API 文档化，为手机版做准备 | API 文档 |
| Week 14 | 移动端方案评估（React Native / Flutter / PWA） | 技术选型报告 |

---

## <span style="color:#C23B22">七、配置与安全</span>

### <span style="color:#C23B22">7.1 用户密码体系</span>

这是 RedPepper 数据安全的第一道防线。用户数据（持仓、交易记录、日记等）全部存储在本地 SQLite 数据库中，<span style="color:#C23B22">**主密码是解锁和加密用户数据的唯一钥匙**</span>。

#### 密码创建与验证

```python
import hashlib
import secrets
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# ── 注册（首次设置密码）──
def create_password(plain_password: str) -> dict:
    """
    用户首次设置主密码时的处理流程
    明文密码永不保存，只存哈希值
    """
    # 生成 256-bit (32字节) 随机盐值
    salt = secrets.token_bytes(32)
    
    # PBKDF2-HMAC-SHA256 迭代 100,000 次
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,           # 256-bit 输出
        salt=salt,
        iterations=100000,   # 10万次迭代，抗暴力破解
    )
    password_hash = kdf.derive(plain_password.encode('utf-8'))
    
    # 保存到 user 表（仅保存 hash + salt）
    return {
        "password_hash": password_hash.hex(),
        "salt": salt.hex(),
        "created_at": datetime.now().isoformat(),
    }

# ── 登录（密码验证）──
def verify_password(plain_password: str, stored_hash: str, salt: str) -> bool:
    """
    登录时验证密码
    使用相同的盐值重新计算哈希，然后比对
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=bytes.fromhex(salt),
        iterations=100000,
    )
    try:
        kdf.verify(plain_password.encode('utf-8'), bytes.fromhex(stored_hash))
        return True
    except InvalidKey:
        return False
```

#### 安全策略

| 策略项 | 要求 | 说明 |
|:--------|:------|:------|
| <span style="color:#C23B22">密码强度</span> | 最少 8 位，含字母+数字 | 低于要求拒绝创建 |
| <span style="color:#7B4B8C">推荐强度</span> | 12 位以上，含大小写+数字+符号 | 界面显示强度条提示 |
| <span style="color:#D4A017">哈希算法</span> | PBKDF2-HMAC-SHA256，100,000 次 | 业界标准，抗彩虹表 |
| <span style="color:#C23B22">错误锁定</span> | 3次失败锁定5分钟，10次锁定30分钟 | 防暴力破解 |
| <span style="color:#7B4B8C">密码重置</span> | 必须清空所有数据 | 无后门，安全第一 |
| <span style="color:#D4A017">修改密码</span> | 旧密码验证 + 重新加密数据库 | 导出文件需用新密码 |

---

### <span style="color:#7B4B8C">7.2 数据导出加密方案</span>

用户可一键导出完整数据为 `.redpepper` 加密文件，用于备份或跨版本迁移。

#### 导出文件格式（.redpepper）

```
┌─────────────────────────────────────────────────────────┐
│                     .redpepper 文件结构                    │
├──────────┬──────────┬──────────┬──────────┬─────────────┤
│  Magic   │ Version  │  Salt    │  IV      │  Encrypted  │
│ (8字节)  │ (4字节)  │(32字节)  │(16字节)  │  Payload    │
│          │          │          │          │  (变长)     │
│ "REPPER" │ 0x0001   │ 随机盐值  │ 随机IV   │ AES-256    │
│          │          │          │          │ -GCM 密文  │
├──────────┴──────────┴──────────┴──────────┴─────────────┤
│                    总大小：~ (原DB + 60) bytes             │
└─────────────────────────────────────────────────────────┘

密钥派生：key = PBKDF2-HMAC-SHA256(user_password, salt, 100000)
认证加密：AES-256-GCM(key, iv, sqlite_db_bytes)
完整性校验：GCM 内置的 128-bit authentication tag
```

#### 导出/导入实现

```python
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import struct

MAGIC = b"REPPER"       # 6 bytes
VERSION = struct.pack("<I", 1)  # uint32 little-endian

def export_database(db_path: str, password: str, output_path: str):
    """
    一键导出：读取 SQLite 文件 → 加密 → 写入 .redpepper
    """
    # 读取原始数据库文件
    with open(db_path, "rb") as f:
        plaintext = f.read()
    
    # 生成随机参数
    salt = secrets.token_bytes(32)
    iv = secrets.token_bytes(16)
    
    # 派生加密密钥
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32,
                     salt=salt, iterations=100000)
    key = kdf.derive(password.encode())
    
    # AES-256-GCM 加密
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(iv, plaintext, None)
    
    # 组装文件
    with open(output_path, "wb") as f:
        f.write(MAGIC)      # 6 bytes
        f.write(VERSION)    # 4 bytes
        f.write(salt)       # 32 bytes
        f.write(iv)         # 16 bytes
        f.write(ciphertext) # 变长 (DB + 16 bytes tag)

def import_database(redpepper_path: str, password: str, output_db_path: str):
    """
    导入恢复：读取 .redpepper → 解密 → 写回 SQLite
    """
    with open(redpepper_path, "rb") as f:
        magic = f.read(6)
        assert magic == MAGIC, "不是有效的 RedPepper 备份文件"
        
        version = struct.unpack("<I", f.read(4))[0]
        salt = f.read(32)
        iv = f.read(16)
        ciphertext = f.read()
    
    # 用相同参数派生密钥
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32,
                     salt=salt, iterations=100000)
    key = kdf.derive(password.encode())
    
    # 解密（失败则抛出 InvalidTag，说明密码错误）
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(iv, ciphertext, None)
    
    with open(output_db_path, "wb") as f:
        f.write(plaintext)
```

---

### <span style="color:#D4A017">7.3 API Key 管理</span>

| 策略 | 说明 |
|:------|:------|
| <span style="color:#C23B22">存储位置</span> | API Key 存储在后端 config.yaml，前端不接触 |
| <span style="color:#7B4B8C">加密存储</span> | 支持使用系统密钥环（Windows DPAPI / macOS Keychain）加密存储 |
| <span style="color:#D4A017">环境变量</span> | 支持通过环境变量覆盖配置文件，方便 CI/CD |
| <span style="color:#C23B22">定期更新</span> | 提供 API Key 刷新功能，建议每 90 天更换一次 |

### <span style="color:#C23B22">7.4 数据安全</span>

| 策略 | 说明 |
|:------|:------|
| <span style="color:#C23B22">本地存储</span> | 所有投资数据保存在本地 SQLite，不上传云端 |
| <span style="color:#7B4B8C">加密导出</span> | 导出文件采用 AES-256-GCM 加密，密码即密钥 |
| <span style="color:#D4A017">版本兼容</span> | `.redpepper` 文件内含版本号，导入时自动 schema 迁移 |
| <span style="color:#C23B22">完整性校验</span> | GCM authentication tag + SHA-256 双重校验 |
| <span style="color:#7B4B8C">日志脱敏</span> | 日志中不记录 API Key、密码等敏感信息 |

---

## <span style="color:#C23B22">八、风险与应对</span>

| 风险项 | 等级 | 应对策略 | 负责人 |
|:--------|:------|:----------|:--------|
| API 供应商变更 | <span style="color:#D4A017">中</span> | 多模型低耦合设计，可快速切换 | 架构 |
| API Key 泄露 | <span style="color:#C23B22">**高**</span> | 后端存储+加密，定期更新 | 安全 |
| <span style="color:#C23B22">用户忘记密码</span> | <span style="color:#C23B22">**高**</span> | 本地应用无后门，重置=清空数据；提供强密码提示和导出提醒 | 用户 |
| <span style="color:#C23B22">导出文件损坏</span> | <span style="color:#7B4B8C">中</span> | GCM authentication tag + SHA-256 双重完整性校验，损坏时明确提示 | 架构 |
| <span style="color:#C23B22">跨版本导入失败</span> | <span style="color:#7B4B8C">中</span> | `.redpepper` 内置版本号，自动 schema 迁移；迁移失败保留原始备份 | 开发 |
| 数据丢失 | <span style="color:#C23B22">**高**</span> | `.redpepper` 加密导出 + 定期提醒用户备份 | 用户 |
| 开发周期延误 | <span style="color:#D4A017">中</span> | MVP 优先，分阶段交付 | PM |
| 同花顺封接口 | <span style="color:#7B4B8C">低</span> | 不依赖官方 API，手动导入 | 产品 |
| 代码质量 | <span style="color:#D4A017">中</span> | Code Review + 单元测试 | 开发 |
| 密码暴力破解 | <span style="color:#7B4B8C">低</span> | PBKDF2 10万次迭代 + 错误次数锁定 + 最小密码强度要求 | 安全 |

---

> <span style="color:#C23B22">**RedPepper（红椒）— 让个人投资更智能、更安全、更高效**</span>  
> <span style="color:#7B4B8C">马良计划工作室 | 2026</span>
