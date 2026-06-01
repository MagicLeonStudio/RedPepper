# RedPepper (红椒) — 项目规范文档 SPEC.md

> A股个人投资基础设施 | v0.1 | 2026年5月
> 技术架构: PyQt6 GUI + FastAPI 后端 + SQLite 数据库
> 支持: 中文/英文双语切换

---

## 1. 架构总览

### 1.1 系统架构图

```
┌─────────────────────────────────────────────────────────┐
│                    RedPepper Desktop App                  │
│  ┌─────────────────────────────────────────────────────┐  │
│  │                PyQt6 Frontend (GUI)                   │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌───────────┐  │  │
│  │  │ 登录页   │ │ 总览页   │ │ 持仓页   │ │ 观察池页   │  │  │
│  │  └─────────┘ └─────────┘ └─────────┘ └───────────┘  │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌───────────┐  │  │
│  │  │ 日志页   │ │ 简报页   │ │ 日记页   │ │ 设置页     │  │  │
│  │  └─────────┘ └─────────┘ └─────────┘ └───────────┘  │  │
│  │                        i18n (zh_CN / en_US)          │  │
│  └──────────────────────┬──────────────────────────────┘  │
│                         │ HTTP (localhost:8000)           │
│  ┌──────────────────────┴──────────────────────────────┐  │
│  │                FastAPI Backend                        │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐  │  │
│  │  │ Auth API │ │Portfolio │ │ Watchlist│ │ Trade   │  │  │
│  │  │ (安全)    │ │ API      │ │ API      │ │ Log API │  │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └─────────┘  │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐  │  │
│  │  │ Briefing │ │  Diary   │ │Knowledge │ │  Data   │  │  │
│  │  │ API      │ │ API      │ │ API      │ │ Export  │  │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └─────────┘  │  │
│  │  ┌──────────────────┐  ┌──────────────────────────┐   │  │
│  │  │ AI Provider Layer │  │  Security (PBKDF2/AES)   │   │  │
│  │  │ (Kimi/DeepSeek)  │  │                          │   │  │
│  │  └──────────────────┘  └──────────────────────────┘   │  │
│  └──────────────────────────┬───────────────────────────┘  │
│                             │                              │
│  ┌──────────────────────────┴───────────────────────────┐  │
│  │                  SQLite Database                      │  │
│  │   portfolio / watchlist / trade_log / briefing /      │  │
│  │   diary / knowledge / user / data_backup              │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### 1.2 技术栈

| 层级 | 技术 | 版本 |
|------|------|------|
| 前端 GUI | PyQt6 | >= 6.6 |
| 后端 API | FastAPI | >= 0.110 |
| 数据库 | SQLite + SQLAlchemy | 3.x / 2.x |
| ORM | SQLAlchemy | >= 2.0 |
| 数据验证 | Pydantic | >= 2.0 |
| HTTP 客户端 | httpx | >= 0.27 |
| 加密 | cryptography | >= 42.0 |
| AI API | openai (兼容接口) | >= 1.0 |
| 打包 | PyInstaller | >= 6.0 |

---

## 2. 目录结构

```
redpepper/
├── README.md                     # 项目说明
├── SETUP.md                      # 开发环境配置
├── requirements.txt              # 项目依赖
├── config.yaml                   # 应用配置
├── backend/                      # FastAPI 后端
│   ├── __init__.py
│   ├── main.py                   # FastAPI 入口
│   ├── database.py               # 数据库连接与初始化
│   ├── models.py                 # SQLAlchemy ORM 模型
│   ├── schemas.py                # Pydantic 数据模型
│   ├── dependencies.py           # 依赖注入
│   ├── security.py               # 安全模块（密码/加密）
│   ├── config.py                 # 配置管理
│   ├── ai/                       # AI Provider 模块
│   │   ├── __init__.py
│   │   ├── base.py               # AIProvider 抽象基类
│   │   ├── kimi_provider.py      # Kimi 实现
│   │   ├── deepseek_provider.py  # DeepSeek 实现
│   │   └── factory.py            # 工厂方法
│   └── routers/                  # API 路由
│       ├── __init__.py
│       ├── auth.py               # 认证路由
│       ├── portfolio.py          # 持仓路由
│       ├── watchlist.py          # 观察池路由
│       ├── trade_log.py          # 交易日志路由
│       ├── briefing.py           # 简报路由
│       ├── diary.py              # 日记路由
│       ├── knowledge.py          # 知识路由
│       └── data_manager.py       # 数据导入导出路由
├── frontend/                     # PyQt6 前端
│   ├── __init__.py
│   ├── main.py                   # GUI 入口
│   ├── app.py                    # 主应用类
│   ├── config.py                 # 前端配置
│   ├── i18n/                     # 国际化
│   │   ├── __init__.py
│   │   ├── translator.py         # 翻译引擎
│   │   ├── zh_CN.json            # 中文翻译
│   │   └── en_US.json            # 英文翻译
│   ├── services/                 # API 调用服务
│   │   ├── __init__.py
│   │   ├── api_client.py         # HTTP 客户端基类
│   │   ├── auth_service.py
│   │   ├── portfolio_service.py
│   │   ├── watchlist_service.py
│   │   ├── trade_log_service.py
│   │   ├── briefing_service.py
│   │   ├── diary_service.py
│   │   ├── knowledge_service.py
│   │   └── data_service.py
│   ├── windows/                  # 主窗口和页面
│   │   ├── __init__.py
│   │   ├── main_window.py        # 主窗口
│   │   ├── login_window.py       # 登录/注册窗口
│   │   ├── dashboard_page.py     # 总览页
│   │   ├── portfolio_page.py     # 持仓页
│   │   ├── watchlist_page.py     # 观察池页
│   │   ├── trade_log_page.py     # 交易日志页
│   │   ├── briefing_page.py      # 简报页
│   │   ├── diary_page.py         # 日记页
│   │   ├── knowledge_page.py     # 知识页
│   │   └── settings_page.py      # 设置页
│   ├── widgets/                  # 可复用组件
│   │   ├── __init__.py
│   │   ├── language_switcher.py  # 语言切换器
│   │   ├── holding_card.py       # 持仓卡片
│   │   ├── watch_item.py         # 观察项
│   │   ├── log_entry.py          # 日志条目
│   │   └── chart_widget.py       # 图表组件
│   └── resources/                # 资源文件
│       ├── logo.png              # Logo
│       └── style.qss             # Qt 样式表
└── tests/                        # 测试
    ├── __init__.py
    ├── test_security.py
    ├── test_api.py
    └── test_database.py
```

---

## 3. 数据模型

### 3.1 SQLAlchemy ORM 模型 (models.py)

```python
# 所有模型共享 Base
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class User(Base):
    """用户认证表 — 仅1条记录存储主密码哈希"""
    __tablename__ = "user"
    id = Column(Integer, primary_key=True)
    password_hash = Column(String(128), nullable=False)  # PBKDF2 哈希 hex
    salt = Column(String(64), nullable=False)            # 盐值 hex
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

class Portfolio(Base):
    """持仓表 — 股票/ETF/基金持仓"""
    __tablename__ = "portfolio"
    id = Column(Integer, primary_key=True)
    code = Column(String(20), nullable=False)            # 代码如 510300
    name = Column(String(100), nullable=False)           # 名称
    type = Column(String(20), default="ETF")             # ETF/股票/基金
    sector = Column(String(50), nullable=True)           # 行业分类
    amount = Column(Float, default=0.0)                  # 持仓金额
    profit = Column(Float, default=0.0)                  # 累计收益
    cost_price = Column(Float, default=0.0)              # 成本价
    current_price = Column(Float, default=0.0)           # 当前价
    shares = Column(Integer, default=0)                  # 持仓份额
    account = Column(String(50), default="中信")          # 所属账户
    reason = Column(Text, nullable=True)                 # 持有原因
    target = Column(String(200), nullable=True)          # 操作目标
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Watchlist(Base):
    """观察池表"""
    __tablename__ = "watchlist"
    id = Column(Integer, primary_key=True)
    code = Column(String(20), nullable=True)             # 代码
    name = Column(String(100), nullable=False)            # 名称
    type = Column(String(20), default="股票")             # 股票/ETF/基金
    sector = Column(String(50), nullable=True)            # 行业
    reason = Column(Text, nullable=True)                  # 关注原因
    trigger_condition = Column(String(200), nullable=True) # 买入触发条件
    rating = Column(String(20), default="⭐⭐⭐")          # 评级
    status = Column(String(20), default="观察")            # 观察/买入/持有
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class TradeLog(Base):
    """操作日志表"""
    __tablename__ = "trade_log"
    id = Column(Integer, primary_key=True)
    date = Column(String(10), nullable=False)             # YYYY-MM-DD
    name = Column(String(100), nullable=False)            # 标的名称
    code = Column(String(20), nullable=True)              # 代码
    action = Column(String(50), nullable=False)           # 买入/卖出/计划买入...
    amount = Column(Float, default=0.0)                   # 金额/份额
    reason = Column(Text, nullable=True)                  # 理由
    emotion = Column(String(50), nullable=True)           # 情绪追踪
    created_at = Column(DateTime, default=datetime.utcnow)

class Briefing(Base):
    """每日简报表"""
    __tablename__ = "briefing"
    id = Column(Integer, primary_key=True)
    date = Column(String(10), nullable=False)
    title = Column(String(200), nullable=False)
    overseas = Column(Text, nullable=True)                # 海外关键事件
    domestic = Column(Text, nullable=True)                # 国内关键事件
    market = Column(Text, nullable=True)                  # 市场走势
    summary = Column(String(500), nullable=True)          # 综合判断
    holdings = Column(Text, nullable=True)                # JSON 持仓影响
    created_at = Column(DateTime, default=datetime.utcnow)

class Diary(Base):
    """投资日记表"""
    __tablename__ = "diary"
    id = Column(Integer, primary_key=True)
    date = Column(String(10), nullable=False)
    best_op = Column(Text, nullable=True)                 # 最满意操作
    worst_op = Column(Text, nullable=True)                # 最蠢操作
    reflection = Column(Text, nullable=True)              # 决策复盘
    focus = Column(Text, nullable=True)                   # 下周关注
    created_at = Column(DateTime, default=datetime.utcnow)

class Knowledge(Base):
    """知识聚合表"""
    __tablename__ = "knowledge"
    id = Column(Integer, primary_key=True)
    url = Column(String(500), nullable=False)
    title = Column(String(200), nullable=False)
    source = Column(String(50), nullable=False)           # 知乎/B站/网页
    tags = Column(String(200), nullable=True)             # 逗号分隔标签
    summary = Column(Text, nullable=True)                 # AI 生成摘要
    related_stocks = Column(String(200), nullable=True)   # 关联股票代码
    created_at = Column(DateTime, default=datetime.utcnow)

class DataBackup(Base):
    """数据备份记录表"""
    __tablename__ = "data_backup"
    id = Column(Integer, primary_key=True)
    backup_id = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    file_path = Column(String(500), nullable=True)
    checksum = Column(String(64), nullable=True)
    size = Column(Integer, default=0)

class EventCalendar(Base):
    """事件日历表"""
    __tablename__ = "event_calendar"
    id = Column(Integer, primary_key=True)
    date = Column(String(10), nullable=False)
    description = Column(String(500), nullable=False)
    impact = Column(String(200), nullable=True)
    level = Column(String(10), default="中")               # 高/中/低
    created_at = Column(DateTime, default=datetime.utcnow)
```

### 3.2 Pydantic Schemas (schemas.py)

所有请求/响应模型使用 Pydantic v2 定义。示例：

```python
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# Portfolio
class PortfolioBase(BaseModel):
    code: str
    name: str
    type: str = "ETF"
    sector: Optional[str] = None
    amount: float = 0.0
    profit: float = 0.0
    cost_price: float = 0.0
    current_price: float = 0.0
    shares: int = 0
    account: str = "中信"
    reason: Optional[str] = None
    target: Optional[str] = None

class PortfolioCreate(PortfolioBase):
    pass

class PortfolioResponse(PortfolioBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# 其他模型类似定义...
```

---

## 4. API 接口定义

### 4.1 认证路由 (/api/auth)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/setup` | 首次设置主密码 |
| POST | `/api/auth/login` | 登录验证 |
| POST | `/api/auth/change-password` | 修改密码 |
| GET | `/api/auth/has-user` | 检查是否已有用户 |

### 4.2 持仓路由 (/api/portfolio)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/portfolio/` | 获取所有持仓 |
| GET | `/api/portfolio/{id}` | 获取单个持仓 |
| POST | `/api/portfolio/` | 添加持仓 |
| PUT | `/api/portfolio/{id}` | 更新持仓 |
| DELETE | `/api/portfolio/{id}` | 删除持仓 |
| GET | `/api/portfolio/summary` | 获取持仓汇总统计 |

### 4.3 观察池路由 (/api/watchlist)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/watchlist/` | 获取观察池 |
| POST | `/api/watchlist/` | 添加观察项 |
| PUT | `/api/watchlist/{id}` | 更新观察项 |
| DELETE | `/api/watchlist/{id}` | 删除观察项 |

### 4.4 交易日志路由 (/api/trade-log)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/trade-log/` | 获取日志列表 |
| POST | `/api/trade-log/` | 添加日志 |
| DELETE | `/api/trade-log/{id}` | 删除日志 |

### 4.5 简报路由 (/api/briefing)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/briefing/` | 获取简报列表 |
| POST | `/api/briefing/` | 创建简报 |
| DELETE | `/api/briefing/{id}` | 删除简报 |

### 4.6 日记路由 (/api/diary)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/diary/` | 获取日记列表 |
| POST | `/api/diary/` | 创建日记 |
| PUT | `/api/diary/{id}` | 更新日记 |
| DELETE | `/api/diary/{id}` | 删除日记 |

### 4.7 数据管理路由 (/api/data)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/data/export` | 导出 .redpepper 文件 |
| POST | `/api/data/import` | 导入 .redpepper 文件 |
| POST | `/api/data/import-csv` | CSV 导入 |
| POST | `/api/data/import-html` | HTML/MD 导入 |

### 4.8 AI 路由 (/api/ai)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/ai/ocr-screenshot` | 截图 OCR 识别 |
| POST | `/api/ai/daily-report` | 生成日报 |
| POST | `/api/ai/summarize` | 文章摘要 |

---

## 5. 安全模块

### 5.1 密码管理 (security.py)

```python
# 密码创建 - PBKDF2-HMAC-SHA256
def create_password(plain_password: str) -> dict:
    salt = secrets.token_bytes(32)
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32,
                     salt=salt, iterations=100000)
    password_hash = kdf.derive(plain_password.encode())
    return {"password_hash": hash.hex(), "salt": salt.hex()}

# 密码验证
def verify_password(plain: str, stored_hash: str, salt: str) -> bool:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32,
                     salt=bytes.fromhex(salt), iterations=100000)
    try:
        kdf.verify(plain.encode(), bytes.fromhex(stored_hash))
        return True
    except InvalidKey:
        return False
```

### 5.2 数据导出加密

```python
MAGIC = b"REPPER"
VERSION = struct.pack("<I", 1)

def export_encrypted(db_path: str, password: str, output_path: str):
    """AES-256-GCM 加密导出"""
    # 读取 SQLite 文件 -> 派生密钥 -> GCM 加密 -> 写入 .redpepper
    
def import_encrypted(redpepper_path: str, password: str, output_db: str):
    """解密导入"""
    # 读取 .redpepper -> 派生密钥 -> GCM 解密 -> 写回 SQLite
```

---

## 6. AI Provider 模块

### 6.1 抽象接口 (ai/base.py)

```python
from abc import ABC, abstractmethod

class AIProvider(ABC):
    @abstractmethod
    async def chat(self, messages, model=None, temperature=0.7):
        """通用对话"""
        pass
    
    @abstractmethod
    async def vision(self, image_base64: str, prompt: str, model=None):
        """图像识别"""
        pass
    
    @abstractmethod
    async def embed(self, texts, model=None):
        """文本嵌入"""
        pass
```

### 6.2 配置 (config.yaml)

```yaml
app:
  name: "RedPepper"
  version: "0.1.0"
  data_dir: "./data"
  
ai:
  default_provider: "deepseek"
  providers:
    kimi:
      api_key: ""
      base_url: "https://api.moonshot.cn/v1"
      default_model: "moonshot-v1-8k"
    deepseek:
      api_key: ""
      base_url: "https://api.deepseek.com/v1"
      default_model: "deepseek-chat"
  scene_models:
    screenshot_ocr: "kimi"
    daily_report: "deepseek"
    knowledge_digest: "deepseek"
    strategy_analysis: "deepseek"

server:
  host: "127.0.0.1"
  port: 8000
```

---

## 7. 国际化 (i18n)

### 7.1 翻译文件格式 (zh_CN.json / en_US.json)

```json
{
  "app_name": "RedPepper 红椒",
  "login": {
    "title": "登录",
    "set_password_first": "首次使用，请设置主密码",
    "password_placeholder": "请输入密码",
    "confirm_password": "确认密码",
    "login_btn": "登录",
    "setup_btn": "设置密码",
    "password_error": "密码错误，还剩 {attempts} 次机会"
  },
  "nav": {
    "dashboard": "总览",
    "portfolio": "持仓",
    "watchlist": "观察池",
    "trade_log": "日志",
    "briefing": "简报",
    "diary": "日记",
    "knowledge": "知识",
    "settings": "设置"
  }
}
```

### 7.2 翻译引擎

```python
class Translator:
    def __init__(self, locale="zh_CN"):
        self.locale = locale
        self.translations = self._load_translations(locale)
    
    def tr(self, key: str, **kwargs) -> str:
        """通过点号路径获取翻译, 如 'login.title' """
        keys = key.split(".")
        value = self.translations
        for k in keys:
            value = value.get(k, key)
        return value.format(**kwargs) if kwargs else value
    
    def set_locale(self, locale: str):
        self.locale = locale
        self.translations = self._load_translations(locale)
```

---

## 8. 前端页面规范

### 8.1 主窗口布局

```
┌──────────────────────────────────────┐
│ [Logo] RedPepper    [EN/中文] [-][X] │  <- 标题栏
├──────────┬───────────────────────────┤
│          │                           │
│  侧边栏   │      内容区域              │
│  导航    │                           │
│          │                           │
│ [总览]   │                           │
│ [持仓]   │                           │
│ [观察池]  │                           │
│ [日志]   │                           │
│ [简报]   │                           │
│ [日记]   │                           │
│ [知识]   │                           │
│ [设置]   │                           │
│          │                           │
├──────────┤                           │
│ 账户信息  │                           │
│ 数据状态  │                           │
├──────────┴───────────────────────────┤
│ 状态栏: 后端连接状态 | 数据最后更新     │
└──────────────────────────────────────┘
```

### 8.2 配色方案

参考 AGI2Rich 深色主题，RedPepper 品牌色系：

| 用途 | 色值 | 说明 |
|------|------|------|
| 主背景 | #0D0D1A | 深蓝黑 |
| 卡片背景 | rgba(22,22,45,0.8) | 半透明深蓝 |
| 主文字 | #E8E8F0 | 浅灰白 |
| 次要文字 | #7A7A9E | 灰紫 |
| 强调色(红) | #E62E2E | RedPepper 品牌红 |
| 强调色(紫) | #8B5CF6 | 辅助紫 |
| 盈利色 | #EF4444 | 红涨 (A股) |
| 亏损色 | #22C55E | 绿跌 (A股) |
| 边框 | rgba(139,92,246,0.2) | 淡紫边框 |

---

## 9. 启动流程

### 9.1 应用启动序列

```
1. 启动后端 (FastAPI on localhost:8000)
2. 启动前端 (PyQt6)
3. 前端检查后端健康 (/api/health)
4. 检查是否有用户 (/api/auth/has-user)
   ├── 无用户 → 显示设置密码界面
   │             → 用户设置密码 → 创建 user 记录 → 进入主界面
   └── 有用户 → 显示登录界面
                  → 验证密码 → 进入主界面
```

### 9.2 前后端启动脚本

```bash
# 开发模式 - 分别启动
# 终端1: 后端
cd backend && uvicorn main:app --reload --port 8000

# 终端2: 前端
cd frontend && python main.py

# 生产模式 - 前端启动后端子进程
python -m frontend.main  # 前端启动时自动启动后端
```

---

## 10. 测试规范

### 10.1 安全模块测试

- test_password_hashing: 密码哈希生成与验证
- test_password_strength: 密码强度检查
- test_export_import: 加密导出与解密导入循环
- test_invalid_password: 错误密码解密失败

### 10.2 API 测试

- test_portfolio_crud: 持仓增删改查
- test_watchlist_crud: 观察池增删改查
- test_data_export: 数据导出
- test_data_import: 数据导入

---

## 11. Phase 1 & Phase 2 功能清单

### Phase 1 — MVP (已完成)
- [x] 项目框架搭建 (PyQt6 + FastAPI + SQLite)
- [x] 数据库设计与实现 (8张表)
- [x] 后端基础框架 (API 路由, 依赖注入)
- [x] 前端基础框架 (主窗口, 导航, 页面切换)
- [x] 国际化框架 (zh_CN / en_US)
- [x] 用户认证 (密码设置/登录/验证)
- [x] 持仓总览 (多账户, 盈亏统计)
- [x] 持仓 CRUD (手动录入)
- [x] 截图 AI OCR 导入 (Kimi Vision)

### Phase 2 — 功能完善 (已完成)
- [x] 观察池模块 (股票/ETF/基金, 评级, 触发条件)
- [x] 操作日志模块 (交易记录, 情绪追踪)
- [x] 简报模块 (开盘/午间/收盘简报)
- [x] 日记模块 (每周复盘)
- [x] 事件日历
- [x] DeepSeek API 集成 (双模型切换)
- [x] AI Provider 抽象层
- [x] CSV/Excel 导入
- [x] HTML/MD 导入 (AGI2Rich 兼容)
- [x] .redpepper 加密导出/导入
- [x] 数据备份与恢复
- [x] 设置页面 (语言切换, API Key 配置)
- [x] README.md
- [x] SETUP.md (开发环境配置)
