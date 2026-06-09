<p align="center">
  <img src="assets/banner.png" alt="RedPepper Logo" width="1080">
</p> 

<h1 align="center"><img src="assets/logo-icon.png" alt="RedPepper Logo" width="32"> RedPepper · 红椒 | 用户使用手册</h1>

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

# 1. 关于导入
RedPepper 针对的是 A 股用户，为了照顾 A 股用户的使用习惯，对“同花顺”手机APP + “同花顺”PC版本软件的个人 Setup 进行了兼容。

## 1.1 持仓导入逻辑

**可选项:**
- 手机截图 → Kimi-k2.6 逐张 OCR 提取 CSV，DeepSeek-v4-flash 跨图融合并结构化入库；
  优点：股票/基金双账户均支持，支持多张互补截图融合（如一张有代码、一张有市值），ETF 别名自动匹配（如"科创50"=="科创50ETF"），缺字段可在预览弹窗中手动补全后入库；
  缺点：初始识别精度依赖截图清晰度，部分字段需人工核对
- PC .txt 文件导入 → deepseek-v4-flash 格式匹配并导入；
  优点：信息完整，缺点：基金账户目前开发者还没发现如何获取

> ⚠️ 手机截图导入支持同时选择多张截图，系统会自动融合互补信息。若融合后仍有字段缺失，可在"确认并补全持仓"预览弹窗中直接编辑 CSV 补全后再入库；有名称的条目始终可以入库，不会因缺少代码而失败。

