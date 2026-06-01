# RedPepper 开发计划

## 项目概述
RedPepper（红椒）— A股个人投资基础设施桌面应用，前后端分离架构（PyQt6 GUI + FastAPI 后端 + SQLite 数据库），支持中英文双语切换。

## 技术栈
- **前端 GUI**: PyQt6
- **后端 API**: FastAPI (Python)
- **数据库**: SQLite (单文件)
- **AI 集成**: Kimi (Moonshot) + DeepSeek 双模型
- **安全**: PBKDF2-HMAC-SHA256, AES-256-GCM
- **打包**: PyInstaller

---

## Stage 1 — 项目骨架搭建（Phase 1 基础框架）

### 1.1 目录结构创建
```
redpepper/
├── backend/              # FastAPI 后端
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py       # FastAPI 入口
│   │   ├── database.py   # SQLite 数据库
│   │   ├── models.py     # SQLAlchemy 数据模型
│   │   ├── schemas.py    # Pydantic 模型
│   │   ├── routers/      # API 路由
│   │   ├── services/     # 业务逻辑
│   │   └── security.py   # 加密/安全
│   ├── config.yaml       # 配置文件
│   └── requirements.txt
├── frontend/             # PyQt6 前端
│   ├── main.py           # GUI 入口
│   ├── widgets/          # 自定义组件
│   ├── windows/          # 窗口/页面
│   ├── services/         # API 调用服务
│   ├── i18n/             # 国际化翻译文件
│   └── resources/        # Logo、样式等
├── tests/
├── README.md
├── setup_dev.py
└── requirements.txt
```

### 1.2 数据库模型实现
按开发计划文档中定义的所有表：portfolio, watchlist, trade_log, briefing, diary, knowledge, user, data_backup

### 1.3 后端基础框架
- FastAPI 应用启动
- SQLite 数据库连接与初始化
- CORS 配置（本地开发）
- 基础 API 路由

### 1.4 前端基础框架
- PyQt6 主窗口
- 侧边栏导航
- 页面路由/切换机制
- 国际化（i18n）框架

---

## Stage 2 — 核心功能模块（Phase 1 功能）

### 2.1 用户认证模块
- 首次启动设置主密码
- 登录验证（PBKDF2-HMAC-SHA256）
- 密码强度检查
- 错误锁定机制

### 2.2 持仓总览模块
- 多账户持仓展示（中信/同花顺）
- 手动录入持仓数据
- 盈亏统计与行业分布
- 集中度警报

### 2.3 截图 AI OCR 导入
- 截图上传界面
- Kimi Vision API 集成
- 持仓数据自动识别与导入

---

## Stage 3 — 功能完善（Phase 2）

### 3.1 观察池模块
- 股票/ETF/基金观察池分类
- 评级、触发条件、状态流转

### 3.2 操作日志模块
- 交易记录 CRUD
- 情绪追踪

### 3.3 简报与日记模块
- 每日简报（开盘/午间/收盘）
- 投资日记（每周复盘）
- 事件日历

### 3.4 AI 双模型集成
- DeepSeek API 集成
- 统一 AI Provider 抽象层
- 场景级别模型智能路由
- API Key 管理

### 3.5 数据导入导出
- CSV/Excel 导入
- HTML/MD 导入（兼容 AGI2Rich）
- .redpepper 加密导出/导入
- 数据备份与恢复

---

## Stage 4 — 国际化与文档

### 4.1 双语切换
- 中文/英文翻译文件
- 动态语言切换
- 所有界面文本国际化

### 4.2 文档交付
- README.md（项目说明、安装、使用）
- 开发环境配置文档（SETUP.md）
- API 文档（FastAPI 自动生成）

---

## Stage 5 — 整合测试与打包

### 5.1 整合测试
- 端到端功能测试
- 数据流验证
- 安全功能验证

### 5.2 打包配置
- PyInstaller 配置
- 资源文件打包
- 单文件可执行程序
