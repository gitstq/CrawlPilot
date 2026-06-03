<!-- 🌐 Language: 简体中文 | [繁體中文](#繁體中文) | [English](#english) -->

<p align="center">
  <img src="https://img.shields.io/badge/version-v0.1.0-blue" alt="Version">
  <img src="https://img.shields.io/badge/python-3.10%2B-green" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-orange" alt="License">
  <img src="https://img.shields.io/badge/dependencies-zero%20mandatory-brightgreen" alt="Dependencies">
</p>

<h1 align="center">🚀 CrawlPilot</h1>

<p align="center">
  <strong>智能自适应 Web 爬虫引擎 —— 零强制依赖，纯 Python 标准库驱动的下一代爬虫框架</strong>
</p>

<p align="center">
  <a href="https://github.com/gitstq/CrawlPilot">GitHub 仓库</a> ·
  <a href="#快速开始">快速开始</a> ·
  <a href="#详细使用指南">使用指南</a> ·
  <a href="#贡献指南">参与贡献</a>
</p>

---

## 🎉 项目介绍

> **CrawlPilot** 是一款用 Python 打造的**智能自适应 Web 爬虫引擎**。它不依赖任何第三方爬虫框架，核心功能完全基于 Python 标准库实现，真正做到**零强制依赖**。

无论你是数据分析师、全栈开发者还是安全研究员，CrawlPilot 都能帮你高效、优雅地抓取 Web 数据。它内置了**智能反爬检测**、**自适应策略切换**、**结构化数据提取管道**和**礼貌爬取**机制，让你专注于数据本身，而不是和反爬系统"斗智斗勇"。

### 为什么选择 CrawlPilot？

| 特性 | CrawlPilot | 传统爬虫框架 |
|------|-----------|-------------|
| 强制依赖 | **零** | 通常 5-20+ |
| 反爬检测 | **内置智能检测** | 需自行实现 |
| 策略切换 | **自动自适应** | 手动配置 |
| 学习成本 | **极低** | 中等偏高 |
| 部署体积 | **轻量** | 较重 |

---

## ✨ 核心特性

### 🌐 HTTP 请求引擎 (Fetcher)

- **20+ 主流浏览器 UA 自动轮换** —— 模拟真实用户，降低被识别风险
- **指数退避自动重试**（最多 3 次） —— 遇到临时故障自动恢复
- **请求超时控制 & Session 管理** —— 精细掌控每次请求
- **代理支持**（HTTP / SOCKS5） —— 灵活应对各种网络环境
- **响应状态码智能处理** —— 自动识别并处理各类 HTTP 状态码

### 🛡️ 反爬检测引擎 (AntiBot)

- **Cloudflare 保护检测** —— 自动识别 CF 挑战页面
- **验证码页面识别** —— 检测 CAPTCHA 并及时预警
- **速率限制响应检测** —— 感知服务端限流行为
- **自适应策略自动切换** —— 检测到封锁后自动调整爬取策略
- **robots.txt 解析与遵守** —— 做一个"好公民"
- **礼貌爬取策略** —— 自动控制请求频率，尊重目标站点

### 🔍 HTML 解析引擎 (Parser)

- **CSS 选择器提取** —— 用你熟悉的方式定位元素
- **XPath 提取** —— 复杂路径也能精准匹配
- **链接提取与规范化** —— 自动补全相对路径，去重处理
- **元数据 / OG 标签 / JSON-LD 提取** —— 结构化元信息一网打尽
- **表格数据提取** —— 轻松解析 HTML 表格

### 🔗 数据管道 (Pipeline)

- **链式数据处理**：`extract → clean → transform` —— 像写流水线一样处理数据
- **CSS 选择器 / 正则 / XPath 规则** —— 多种提取方式任你选择
- **数据清洗与类型转换** —— 自动去除空白、转换类型
- **字段映射与重命名** —— 输出格式由你定义

### ⚙️ 爬取调度器 (Scheduler)

- **并发控制**（Semaphore） —— 精确控制同时请求数
- **速率限制**（全局 + 域名级别） —— 不同站点不同策略
- **断点续爬** —— 中断后从上次位置继续
- **URL 去重与优先级队列** —— 避免重复爬取，优先处理重要页面
- **优雅关闭** —— 安全退出，不丢失进度

### 💾 存储后端 (Storage)

- **JSON / CSV / SQLite** —— 三种格式开箱即用
- **增量写入** —— 边爬边存，不怕中途崩溃
- **自定义字段映射** —— 灵活定义输出结构

### 🖥️ CLI 命令行工具

| 命令 | 说明 |
|------|------|
| `crawl-pilot crawl <url>` | 单页爬取 |
| `crawl-pilot crawl-site <url>` | 整站爬取 |
| `crawl-pilot parse <file>` | 解析本地 HTML 文件 |

---

## 🚀 快速开始

### 📦 安装

```bash
# 从源码安装
git clone https://github.com/gitstq/CrawlPilot.git
cd CrawlPilot
pip install -e .

# 或直接安装（无需下载源码）
pip install git+https://github.com/gitstq/CrawlPilot.git

# 可选依赖 —— 按需安装，不强制
pip install crawl-pilot[httpx]    # 高性能 HTTP 客户端
pip install crawl-pilot[lxml]     # 快速 HTML 解析
pip install crawl-pilot[all]      # 安装全部可选依赖
```

### 🐍 Python API 使用

```python
from crawl_pilot import FetchEngine, HTMLParser, Pipeline

# 1. 爬取网页
engine = FetchEngine()
response = engine.fetch("https://example.com")

# 2. 解析 HTML
parser = HTMLParser(response.text)
title = parser.get_title()
links = parser.extract_links()
content = parser.css_select("article.content")

# 3. 数据管道提取
pipeline = Pipeline()
pipeline.extract(css="h1.title").clean().transform(rename={"text": "heading"})
results = pipeline.run(parser)
```

### 🖥️ CLI 命令行使用

```bash
# 单页爬取，输出为 JSON
crawl-pilot crawl https://example.com -o json

# 整站爬取（深度 2，并发 3），输出为 CSV
crawl-pilot crawl-site https://example.com --depth 2 --concurrency 3 -o csv

# 使用 CSS 选择器精准提取数据
crawl-pilot crawl https://example.com --selector "h1" --selector "p.content" -o json

# 解析本地 HTML 文件
crawl-pilot parse page.html --selector "table.data tr td"
```

---

## 📖 详细使用指南

### 反爬检测与策略切换

CrawlPilot 内置了智能反爬检测引擎，当检测到目标网站启用了反爬措施时，会自动调整爬取策略：

```python
from crawl_pilot import FetchEngine, AntiBot

engine = FetchEngine()
antibot = AntiBot()

response = engine.fetch("https://target-site.com")

# 自动检测反爬特征
if antibot.is_protected(response):
    print("检测到反爬保护！")
    print(f"保护类型: {antibot.detect_protection_type(response)}")
    # 引擎会自动切换策略，你也可以手动干预
    engine.switch_strategy("stealth")
```

### 数据提取管道

Pipeline 是 CrawlPilot 最强大的特性之一，支持链式调用：

```python
from crawl_pilot import HTMLParser, Pipeline

parser = HTMLParser(html_text)

# 构建提取管道
pipeline = Pipeline()
pipeline.extract(css="h1.title", field="title")       # 提取标题
pipeline.extract(css="p.content", field="body")       # 提取正文
pipeline.extract(css="span.date", field="date")       # 提取日期
pipeline.clean()                                       # 清洗数据
pipeline.transform(rename={"body": "content"})         # 字段重命名

results = pipeline.run(parser)
for item in results:
    print(item)
```

### 整站爬取

```python
from crawl_pilot import Scheduler, FetchEngine, HTMLParser

scheduler = Scheduler(
    max_concurrency=3,       # 最大并发数
    rate_limit=1.0,          # 全局速率限制（请求/秒）
    domain_rate_limit=0.5,    # 单域名速率限制
    checkpoint="crawl_state" # 断点续爬文件
)

engine = FetchEngine()

def process_page(url):
    response = engine.fetch(url)
    parser = HTMLParser(response.text)
    return {
        "title": parser.get_title(),
        "links": parser.extract_links()
    }

# 添加种子 URL
scheduler.add_url("https://example.com")

# 启动爬取
results = scheduler.run(process_page, max_depth=2)
```

### 存储数据

```python
from crawl_pilot import Storage

# JSON 存储
storage = Storage("output", backend="json")
storage.save(results)

# CSV 存储
storage = Storage("output", backend="csv")
storage.save(results)

# SQLite 存储
storage = Storage("output", backend="sqlite")
storage.save(results)
```

---

## 💡 设计思路与迭代规划

### 设计哲学：自适应智能

CrawlPilot 的核心设计理念是 **"自适应智能"** —— 爬虫不应只是机械地发送请求，而应该像一位经验丰富的"飞行员"一样，能够感知环境变化并做出智能决策。

- **零强制依赖** —— 核心功能完全基于 Python 标准库，可选增强按需安装
- **智能反爬检测** —— 自动识别 Cloudflare、验证码、速率限制等反爬措施
- **自适应策略调整** —— 检测到封锁后自动切换 User-Agent、调整请求频率
- **礼貌爬取** —— 自动解析 robots.txt，遵守爬取规则，尊重目标网站

### 架构设计

```
┌─────────────────────────────────────────────────┐
│                   CLI 命令行                      │
├─────────────────────────────────────────────────┤
│  Scheduler (调度器)                               │
│  ├── 并发控制 / 速率限制 / 断点续爬               │
│  └── URL 去重 / 优先级队列 / 优雅关闭             │
├─────────────────────────────────────────────────┤
│  FetchEngine (请求引擎)  ←→  AntiBot (反爬检测)   │
│  ├── UA 轮换 / 重试 / 超时                        │
│  └── 代理 / Session / 状态码处理                   │
├─────────────────────────────────────────────────┤
│  HTMLParser (解析引擎)  ←→  Pipeline (数据管道)   │
│  ├── CSS/XPath/链接/元数据提取                     │
│  └── extract → clean → transform                  │
├─────────────────────────────────────────────────┤
│  Storage (存储后端)                               │
│  └── JSON / CSV / SQLite / 增量写入               │
└─────────────────────────────────────────────────┘
```

### 迭代规划

- [x] **v0.1.0** —— 核心引擎发布：Fetcher、Parser、Pipeline、Scheduler、Storage
- [ ] **v0.2.0** —— JavaScript 渲染支持、Cookie/Session 持久化
- [ ] **v0.3.0** —— 分布式爬取、消息队列集成
- [ ] **v0.4.0** —— 可视化监控面板、爬取数据实时预览
- [ ] **v1.0.0** —— 插件系统、自定义中间件、正式稳定版

---

## 📦 安装与部署

### 系统要求

- **Python** 3.10 或更高版本
- **操作系统**：Windows / macOS / Linux 均可
- **网络**：需要能访问目标网站

### 安装方式

```bash
# 方式一：从 PyPI 安装（推荐）
pip install crawl-pilot

# 方式二：从 GitHub 安装最新版
pip install git+https://github.com/gitstq/CrawlPilot.git

# 方式三：从源码安装（开发者推荐）
git clone https://github.com/gitstq/CrawlPilot.git
cd CrawlPilot
pip install -e .
```

### 可选依赖

```bash
# 高性能 HTTP 客户端（推荐用于大规模爬取）
pip install crawl-pilot[httpx]

# 快速 HTML/XML 解析（推荐用于复杂页面）
pip install crawl-pilot[lxml]

# 安装全部可选依赖
pip install crawl-pilot[all]
```

### 验证安装

```bash
# 检查版本
crawl-pilot --version

# 查看帮助
crawl-pilot --help

# 快速测试
crawl-pilot crawl https://example.com -o json
```

---

## 🤝 贡献指南

我们欢迎并感谢每一位贡献者！无论是提交 Bug 报告、改进文档还是贡献代码，你的每一份付出都让 CrawlPilot 变得更好。

### 贡献流程

1. **Fork** 本仓库
2. 创建特性分支：`git checkout -b feature/your-feature-name`
3. 提交更改：`git commit -m "feat: add your feature description"`
4. 推送分支：`git push origin feature/your-feature-name`
5. 提交 **Pull Request**

### 开发环境搭建

```bash
git clone https://github.com/gitstq/CrawlPilot.git
cd CrawlPilot
pip install -e ".[all]"
pip install pytest   # 测试框架

# 运行测试
pytest tests/
```

### 代码规范

- 遵循 **PEP 8** 编码规范
- 编写**单元测试**覆盖新功能
- 保持**向后兼容**，避免破坏性变更
- 提交信息遵循 **Conventional Commits** 规范

### 提交信息格式

```
feat: 新增功能
fix: 修复 Bug
docs: 文档更新
style: 代码格式调整
refactor: 代码重构
test: 测试相关
chore: 构建/工具链相关
```

---

## 📄 开源协议

本项目基于 **[MIT License](https://opensource.org/licenses/MIT)** 开源。

```
MIT License

Copyright (c) 2024 CrawlPilot Team

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

<p align="center">
  用 ❤️ 构建 | CrawlPilot Team
</p>

---
---

<!-- 🌐 Language: [简体中文](#简体中文) | 繁體中文 | [English](#english-1) -->

<p align="center">
  <img src="https://img.shields.io/badge/version-v0.1.0-blue" alt="Version">
  <img src="https://img.shields.io/badge/python-3.10%2B-green" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-orange" alt="License">
  <img src="https://img.shields.io/badge/dependencies-zero%20mandatory-brightgreen" alt="Dependencies">
</p>

<h1 align="center">🚀 CrawlPilot</h1>

<p align="center">
  <strong>智慧自適應 Web 爬蟲引擎 —— 零強制依賴，純 Python 標準庫驅動的下一代爬蟲框架</strong>
</p>

<p align="center">
  <a href="https://github.com/gitstq/CrawlPilot">GitHub 仓库</a> ·
  <a href="#快速開始">快速開始</a> ·
  <a href="#詳細使用指南">使用指南</a> ·
  <a href="#貢獻指南">參與貢獻</a>
</p>

---

## 🎉 專案介紹

> **CrawlPilot** 是一款用 Python 打造的**智慧自適應 Web 爬蟲引擎**。它不依賴任何第三方爬蟲框架，核心功能完全基於 Python 標準庫實現，真正做到**零強制依賴**。

無論你是資料分析師、全端開發者還是安全研究員，CrawlPilot 都能幫你高效、優雅地抓取 Web 資料。它內建了**智慧反爬檢測**、**自適應策略切換**、**結構化資料提取管道**和**禮貌爬取**機制，讓你專注於資料本身，而不是和反爬系統「鬥智鬥勇」。

### 為什麼選擇 CrawlPilot？

| 特性 | CrawlPilot | 傳統爬蟲框架 |
|------|-----------|-------------|
| 強制依賴 | **零** | 通常 5-20+ |
| 反爬檢測 | **內建智慧檢測** | 需自行實現 |
| 策略切換 | **自動自適應** | 手動配置 |
| 學習成本 | **極低** | 中等偏高 |
| 部署體積 | **輕量** | 較重 |

---

## ✨ 核心特性

### 🌐 HTTP 請求引擎 (Fetcher)

- **20+ 主流瀏覽器 UA 自動輪換** —— 模擬真實用戶，降低被識別風險
- **指數退避自動重試**（最多 3 次） —— 遇到臨時故障自動恢復
- **請求逾時控制 & Session 管理** —— 精細掌控每次請求
- **代理支援**（HTTP / SOCKS5） —— 靈活應對各種網路環境
- **回應狀態碼智慧處理** —— 自動識別並處理各類 HTTP 狀態碼

### 🛡️ 反爬檢測引擎 (AntiBot)

- **Cloudflare 保護檢測** —— 自動識別 CF 挑戰頁面
- **驗證碼頁面識別** —— 偵測 CAPTCHA 並及時預警
- **速率限制回應檢測** —— 感知伺服端限流行為
- **自適應策略自動切換** —— 偵測到封鎖後自動調整爬取策略
- **robots.txt 解析與遵守** —— 做一個「好公民」
- **禮貌爬取策略** —— 自動控制請求頻率，尊重目標站點

### 🔍 HTML 解析引擎 (Parser)

- **CSS 選擇器提取** —— 用你熟悉的方式定位元素
- **XPath 提取** —— 複雜路徑也能精準匹配
- **連結提取與正規化** —— 自動補全相對路徑，去重處理
- **元資料 / OG 標籤 / JSON-LD 提取** —— 結構化元資訊一網打盡
- **表格資料提取** —— 輕鬆解析 HTML 表格

### 🔗 資料管道 (Pipeline)

- **鏈式資料處理**：`extract → clean → transform` —— 像寫流水線一樣處理資料
- **CSS 選擇器 / 正則 / XPath 規則** —— 多種提取方式任你選擇
- **資料清洗與型別轉換** —— 自動去除空白、轉換型別
- **欄位映射與重新命名** —— 輸出格式由你定義

### ⚙️ 爬取排程器 (Scheduler)

- **並發控制**（Semaphore） —— 精確控制同時請求數
- **速率限制**（全域 + 網域名稱級別） —— 不同站點不同策略
- **斷點續爬** —— 中斷後從上次位置繼續
- **URL 去重與優先級佇列** —— 避免重複爬取，優先處理重要頁面
- **優雅關閉** —— 安全退出，不遺失進度

### 💾 儲存後端 (Storage)

- **JSON / CSV / SQLite** —— 三種格式開箱即用
- **增量寫入** —— 邊爬邊存，不怕中途崩潰
- **自訂欄位映射** —— 靈活定義輸出結構

### 🖥️ CLI 命令列工具

| 命令 | 說明 |
|------|------|
| `crawl-pilot crawl <url>` | 單頁爬取 |
| `crawl-pilot crawl-site <url>` | 整站爬取 |
| `crawl-pilot parse <file>` | 解析本地 HTML 檔案 |

---

## 🚀 快速開始

### 📦 安裝

```bash
# 從原始碼安裝
git clone https://github.com/gitstq/CrawlPilot.git
cd CrawlPilot
pip install -e .

# 或直接安裝（無需下載原始碼）
pip install git+https://github.com/gitstq/CrawlPilot.git

# 可選依賴 —— 按需安裝，不強制
pip install crawl-pilot[httpx]    # 高效能 HTTP 客戶端
pip install crawl-pilot[lxml]     # 快速 HTML 解析
pip install crawl-pilot[all]      # 安裝全部可選依賴
```

### 🐍 Python API 使用

```python
from crawl_pilot import FetchEngine, HTMLParser, Pipeline

# 1. 爬取網頁
engine = FetchEngine()
response = engine.fetch("https://example.com")

# 2. 解析 HTML
parser = HTMLParser(response.text)
title = parser.get_title()
links = parser.extract_links()
content = parser.css_select("article.content")

# 3. 資料管道提取
pipeline = Pipeline()
pipeline.extract(css="h1.title").clean().transform(rename={"text": "heading"})
results = pipeline.run(parser)
```

### 🖥️ CLI 命令列使用

```bash
# 單頁爬取，輸出為 JSON
crawl-pilot crawl https://example.com -o json

# 整站爬取（深度 2，並發 3），輸出為 CSV
crawl-pilot crawl-site https://example.com --depth 2 --concurrency 3 -o csv

# 使用 CSS 選擇器精準提取資料
crawl-pilot crawl https://example.com --selector "h1" --selector "p.content" -o json

# 解析本地 HTML 檔案
crawl-pilot parse page.html --selector "table.data tr td"
```

---

## 📖 詳細使用指南

### 反爬檢測與策略切換

CrawlPilot 內建了智慧反爬檢測引擎，當偵測到目標網站啟用了反爬措施時，會自動調整爬取策略：

```python
from crawl_pilot import FetchEngine, AntiBot

engine = FetchEngine()
antibot = AntiBot()

response = engine.fetch("https://target-site.com")

# 自動偵測反爬特徵
if antibot.is_protected(response):
    print("偵測到反爬保護！")
    print(f"保護類型: {antibot.detect_protection_type(response)}")
    # 引擎會自動切換策略，你也可以手動介入
    engine.switch_strategy("stealth")
```

### 資料提取管道

Pipeline 是 CrawlPilot 最強大的特性之一，支援鏈式呼叫：

```python
from crawl_pilot import HTMLParser, Pipeline

parser = HTMLParser(html_text)

# 建構提取管道
pipeline = Pipeline()
pipeline.extract(css="h1.title", field="title")       # 提取標題
pipeline.extract(css="p.content", field="body")       # 提取正文
pipeline.extract(css="span.date", field="date")       # 提取日期
pipeline.clean()                                       # 清洗資料
pipeline.transform(rename={"body": "content"})         # 欄位重新命名

results = pipeline.run(parser)
for item in results:
    print(item)
```

### 整站爬取

```python
from crawl_pilot import Scheduler, FetchEngine, HTMLParser

scheduler = Scheduler(
    max_concurrency=3,       # 最大並發數
    rate_limit=1.0,          # 全域速率限制（請求/秒）
    domain_rate_limit=0.5,    # 單網域速率限制
    checkpoint="crawl_state" # 斷點續爬檔案
)

engine = FetchEngine()

def process_page(url):
    response = engine.fetch(url)
    parser = HTMLParser(response.text)
    return {
        "title": parser.get_title(),
        "links": parser.extract_links()
    }

# 新增種子 URL
scheduler.add_url("https://example.com")

# 啟動爬取
results = scheduler.run(process_page, max_depth=2)
```

### 儲存資料

```python
from crawl_pilot import Storage

# JSON 儲存
storage = Storage("output", backend="json")
storage.save(results)

# CSV 儲存
storage = Storage("output", backend="csv")
storage.save(results)

# SQLite 儲存
storage = Storage("output", backend="sqlite")
storage.save(results)
```

---

## 💡 設計思路與迭代規劃

### 設計哲學：自適應智慧

CrawlPilot 的核心設計理念是 **「自適應智慧」** —— 爬蟲不應只是機械地發送請求，而應該像一位經驗豐富的「飛行員」一樣，能夠感知環境變化並做出智慧決策。

- **零強制依賴** —— 核心功能完全基於 Python 標準庫，可選增強按需安裝
- **智慧反爬檢測** —— 自動識別 Cloudflare、驗證碼、速率限制等反爬措施
- **自適應策略調整** —— 偵測到封鎖後自動切換 User-Agent、調整請求頻率
- **禮貌爬取** —— 自動解析 robots.txt，遵守爬取規則，尊重目標網站

### 架構設計

```
┌─────────────────────────────────────────────────┐
│                   CLI 命令列                      │
├─────────────────────────────────────────────────┤
│  Scheduler (排程器)                               │
│  ├── 並發控制 / 速率限制 / 斷點續爬               │
│  └── URL 去重 / 優先級佇列 / 優雅關閉            │
├─────────────────────────────────────────────────┤
│  FetchEngine (請求引擎)  ←→  AntiBot (反爬檢測)    │
│  ├── UA 輪換 / 重試 / 逾時                        │
│  └── 代理 / Session / 狀態碼處理                  │
├─────────────────────────────────────────────────┤
│  HTMLParser (解析引擎)  ←→  Pipeline (資料管道)    │
│  ├── CSS/XPath/連結/元資料提取                     │
│  └── extract → clean → transform                  │
├─────────────────────────────────────────────────┤
│  Storage (儲存後端)                               │
│  └── JSON / CSV / SQLite / 增量寫入               │
└─────────────────────────────────────────────────┘
```

### 迭代規劃

- [x] **v0.1.0** —— 核心引擎發布：Fetcher、Parser、Pipeline、Scheduler、Storage
- [ ] **v0.2.0** —— JavaScript 渲染支援、Cookie/Session 持久化
- [ ] **v0.3.0** —— 分散式爬取、訊息佇列整合
- [ ] **v0.4.0** —— 视覺化監控面板、爬取資料即時預覽
- [ ] **v1.0.0** —— 外掛系統、自訂中介軟體、正式穩定版

---

## 📦 安裝與部署

### 系統需求

- **Python** 3.10 或更高版本
- **作業系統**：Windows / macOS / Linux 均可
- **網路**：需要能存取目標網站

### 安裝方式

```bash
# 方式一：從 PyPI 安裝（推薦）
pip install crawl-pilot

# 方式二：從 GitHub 安裝最新版
pip install git+https://github.com/gitstq/CrawlPilot.git

# 方式三：從原始碼安裝（開發者推薦）
git clone https://github.com/gitstq/CrawlPilot.git
cd CrawlPilot
pip install -e .
```

### 可選依賴

```bash
# 高效能 HTTP 客戶端（推薦用於大規模爬取）
pip install crawl-pilot[httpx]

# 快速 HTML/XML 解析（推薦用於複雜頁面）
pip install crawl-pilot[lxml]

# 安裝全部可選依賴
pip install crawl-pilot[all]
```

### 驗證安裝

```bash
# 檢查版本
crawl-pilot --version

# 查看幫助
crawl-pilot --help

# 快速測試
crawl-pilot crawl https://example.com -o json
```

---

## 🤝 貢獻指南

我們歡迎並感謝每一位貢獻者！無論是提交 Bug 回報、改進文件還是貢獻程式碼，你的每一份付出都讓 CrawlPilot 變得更好。

### 貢獻流程

1. **Fork** 本倉庫
2. 建立特性分支：`git checkout -b feature/your-feature-name`
3. 提交變更：`git commit -m "feat: add your feature description"`
4. 推送分支：`git push origin feature/your-feature-name`
5. 提交 **Pull Request**

### 開發環境建置

```bash
git clone https://github.com/gitstq/CrawlPilot.git
cd CrawlPilot
pip install -e ".[all]"
pip install pytest   # 測試框架

# 執行測試
pytest tests/
```

### 程式碼規範

- 遵循 **PEP 8** 編碼規範
- 編寫**單元測試**涵蓋新功能
- 保持**向後相容**，避免破壞性變更
- 提交訊息遵循 **Conventional Commits** 規範

### 提交訊息格式

```
feat: 新增功能
fix: 修復 Bug
docs: 文件更新
style: 程式碼格式調整
refactor: 程式碼重構
test: 測試相關
chore: 建置/工具鏈相關
```

---

## 📄 開源協議

本專案基於 **[MIT License](https://opensource.org/licenses/MIT)** 開源。

```
MIT License

Copyright (c) 2024 CrawlPilot Team

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

<p align="center">
  用 ❤️ 建構 | CrawlPilot Team
</p>

---
---

<!-- 🌐 Language: [简体中文](#简体中文-1) | [繁體中文](#繁體中文-1) | English -->

<p align="center">
  <img src="https://img.shields.io/badge/version-v0.1.0-blue" alt="Version">
  <img src="https://img.shields.io/badge/python-3.10%2B-green" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-orange" alt="License">
  <img src="https://img.shields.io/badge/dependencies-zero%20mandatory-brightgreen" alt="Dependencies">
</p>

<h1 align="center">🚀 CrawlPilot</h1>

<p align="center">
  <strong>Intelligent Adaptive Web Crawling Engine — Zero mandatory dependencies, powered by pure Python standard library</strong>
</p>

<p align="center">
  <a href="https://github.com/gitstq/CrawlPilot">GitHub Repository</a> ·
  <a href="#quick-start">Quick Start</a> ·
  <a href="#detailed-usage-guide">Usage Guide</a> ·
  <a href="#contributing">Contributing</a>
</p>

---

## 🎉 Introduction

> **CrawlPilot** is an **intelligent adaptive web crawling engine** built with Python. It does not rely on any third-party crawling frameworks — its core functionality is implemented entirely with the Python standard library, achieving **zero mandatory dependencies**.

Whether you are a data analyst, full-stack developer, or security researcher, CrawlPilot helps you crawl web data efficiently and elegantly. It features built-in **smart anti-bot detection**, **adaptive strategy switching**, a **structured data extraction pipeline**, and **polite crawling** mechanisms — so you can focus on the data itself instead of battling anti-scraping systems.

### Why CrawlPilot?

| Feature | CrawlPilot | Traditional Frameworks |
|---------|-----------|----------------------|
| Mandatory Dependencies | **Zero** | Typically 5-20+ |
| Anti-Bot Detection | **Built-in Smart Detection** | Must implement yourself |
| Strategy Switching | **Automatic & Adaptive** | Manual configuration |
| Learning Curve | **Minimal** | Moderate to High |
| Deployment Size | **Lightweight** | Heavy |

---

## ✨ Core Features

### 🌐 HTTP Request Engine (Fetcher)

- **20+ mainstream browser User-Agent auto-rotation** — Mimic real users to reduce detection risk
- **Exponential backoff auto-retry** (up to 3 attempts) — Automatic recovery from transient failures
- **Request timeout control & Session management** — Fine-grained control over every request
- **Proxy support** (HTTP / SOCKS5) — Flexible handling of various network environments
- **Intelligent response status code handling** — Automatically identify and handle HTTP status codes

### 🛡️ Anti-Bot Detection Engine (AntiBot)

- **Cloudflare protection detection** — Automatically identify CF challenge pages
- **CAPTCHA page recognition** — Detect CAPTCHAs and alert in time
- **Rate limit response detection** — Sense server-side throttling behavior
- **Adaptive strategy auto-switching** — Automatically adjust crawling strategy when blocking is detected
- **robots.txt parsing & compliance** — Be a good web citizen
- **Polite crawling strategy** — Automatically control request frequency, respect target sites

### 🔍 HTML Parsing Engine (Parser)

- **CSS selector extraction** — Locate elements the way you're familiar with
- **XPath extraction** — Precisely match even complex paths
- **Link extraction & normalization** — Auto-complete relative paths with deduplication
- **Metadata / OG tags / JSON-LD extraction** — Capture all structured meta information
- **Table data extraction** — Easily parse HTML tables

### 🔗 Data Pipeline

- **Chainable data processing**: `extract → clean → transform` — Process data like an assembly line
- **CSS selector / Regex / XPath rules** — Multiple extraction methods at your disposal
- **Data cleaning & type conversion** — Auto-strip whitespace, convert types
- **Field mapping & renaming** — Define your output format

### ⚙️ Crawl Scheduler

- **Concurrency control** (Semaphore) — Precisely control simultaneous requests
- **Rate limiting** (global + per-domain) — Different strategies for different sites
- **Checkpoint & resume** — Continue from where you left off after interruption
- **URL deduplication & priority queue** — Avoid duplicate crawling, prioritize important pages
- **Graceful shutdown** — Exit safely without losing progress

### 💾 Storage Backends

- **JSON / CSV / SQLite** — Three formats ready out of the box
- **Incremental writes** — Save as you crawl, no data loss from mid-crawl crashes
- **Custom field mapping** — Flexibly define output structure

### 🖥️ CLI Commands

| Command | Description |
|---------|-------------|
| `crawl-pilot crawl <url>` | Crawl a single page |
| `crawl-pilot crawl-site <url>` | Crawl an entire site |
| `crawl-pilot parse <file>` | Parse a local HTML file |

---

## 🚀 Quick Start

### 📦 Installation

```bash
# Install from source
git clone https://github.com/gitstq/CrawlPilot.git
cd CrawlPilot
pip install -e .

# Or install directly (no need to download source)
pip install git+https://github.com/gitstq/CrawlPilot.git

# Optional dependencies — install as needed, never forced
pip install crawl-pilot[httpx]    # High-performance HTTP client
pip install crawl-pilot[lxml]     # Fast HTML parsing
pip install crawl-pilot[all]      # All optional dependencies
```

### 🐍 Python API Usage

```python
from crawl_pilot import FetchEngine, HTMLParser, Pipeline

# 1. Fetch a web page
engine = FetchEngine()
response = engine.fetch("https://example.com")

# 2. Parse HTML
parser = HTMLParser(response.text)
title = parser.get_title()
links = parser.extract_links()
content = parser.css_select("article.content")

# 3. Data pipeline extraction
pipeline = Pipeline()
pipeline.extract(css="h1.title").clean().transform(rename={"text": "heading"})
results = pipeline.run(parser)
```

### 🖥️ CLI Usage

```bash
# Crawl a single page, output as JSON
crawl-pilot crawl https://example.com -o json

# Crawl an entire site (depth 2, concurrency 3), output as CSV
crawl-pilot crawl-site https://example.com --depth 2 --concurrency 3 -o csv

# Extract data using CSS selectors
crawl-pilot crawl https://example.com --selector "h1" --selector "p.content" -o json

# Parse a local HTML file
crawl-pilot parse page.html --selector "table.data tr td"
```

---

## 📖 Detailed Usage Guide

### Anti-Bot Detection & Strategy Switching

CrawlPilot features a built-in smart anti-bot detection engine. When it detects that a target site has enabled anti-scraping measures, it automatically adjusts the crawling strategy:

```python
from crawl_pilot import FetchEngine, AntiBot

engine = FetchEngine()
antibot = AntiBot()

response = engine.fetch("https://target-site.com")

# Automatically detect anti-bot signatures
if antibot.is_protected(response):
    print("Anti-bot protection detected!")
    print(f"Protection type: {antibot.detect_protection_type(response)}")
    # The engine auto-switches strategy, but you can also intervene manually
    engine.switch_strategy("stealth")
```

### Data Extraction Pipeline

Pipeline is one of CrawlPilot's most powerful features, supporting chainable method calls:

```python
from crawl_pilot import HTMLParser, Pipeline

parser = HTMLParser(html_text)

# Build an extraction pipeline
pipeline = Pipeline()
pipeline.extract(css="h1.title", field="title")       # Extract titles
pipeline.extract(css="p.content", field="body")       # Extract body text
pipeline.extract(css="span.date", field="date")        # Extract dates
pipeline.clean()                                       # Clean data
pipeline.transform(rename={"body": "content"})         # Rename fields

results = pipeline.run(parser)
for item in results:
    print(item)
```

### Site-Wide Crawling

```python
from crawl_pilot import Scheduler, FetchEngine, HTMLParser

scheduler = Scheduler(
    max_concurrency=3,       # Maximum concurrent requests
    rate_limit=1.0,          # Global rate limit (requests/second)
    domain_rate_limit=0.5,   # Per-domain rate limit
    checkpoint="crawl_state" # Checkpoint file for resume
)

engine = FetchEngine()

def process_page(url):
    response = engine.fetch(url)
    parser = HTMLParser(response.text)
    return {
        "title": parser.get_title(),
        "links": parser.extract_links()
    }

# Add seed URL
scheduler.add_url("https://example.com")

# Start crawling
results = scheduler.run(process_page, max_depth=2)
```

### Storing Data

```python
from crawl_pilot import Storage

# JSON storage
storage = Storage("output", backend="json")
storage.save(results)

# CSV storage
storage = Storage("output", backend="csv")
storage.save(results)

# SQLite storage
storage = Storage("output", backend="sqlite")
storage.save(results)
```

---

## 💡 Design Philosophy & Roadmap

### Design Philosophy: Adaptive Intelligence

CrawlPilot's core design principle is **"Adaptive Intelligence"** — a crawler should not just mechanically send requests. Like an experienced pilot, it should sense environmental changes and make intelligent decisions.

- **Zero mandatory dependencies** — Core functionality built entirely on the Python standard library, with optional enhancements installed on demand
- **Smart anti-bot detection** — Automatically identify Cloudflare, CAPTCHAs, rate limiting, and other anti-scraping measures
- **Adaptive strategy adjustment** — Auto-switch User-Agents and adjust request frequency when blocking is detected
- **Polite crawling** — Auto-parse robots.txt, respect crawling rules, and be kind to target websites

### Architecture Overview

```
┌─────────────────────────────────────────────────┐
│                   CLI Interface                   │
├─────────────────────────────────────────────────┤
│  Scheduler                                       │
│  ├── Concurrency Control / Rate Limiting / Resume│
│  └── URL Dedup / Priority Queue / Graceful Exit │
├─────────────────────────────────────────────────┤
│  FetchEngine (Request)  ←→  AntiBot (Detection) │
│  ├── UA Rotation / Retry / Timeout               │
│  └── Proxy / Session / Status Code Handling       │
├─────────────────────────────────────────────────┤
│  HTMLParser (Parsing)  ←→  Pipeline (Data)       │
│  ├── CSS/XPath/Links/Metadata Extraction         │
│  └── extract → clean → transform                  │
├─────────────────────────────────────────────────┤
│  Storage (Persistence)                           │
│  └── JSON / CSV / SQLite / Incremental Writes    │
└─────────────────────────────────────────────────┘
```

### Roadmap

- [x] **v0.1.0** — Core engine release: Fetcher, Parser, Pipeline, Scheduler, Storage
- [ ] **v0.2.0** — JavaScript rendering support, Cookie/Session persistence
- [ ] **v0.3.0** — Distributed crawling, message queue integration
- [ ] **v0.4.0** — Visual monitoring dashboard, real-time crawl data preview
- [ ] **v1.0.0** — Plugin system, custom middleware, official stable release

---

## 📦 Installation & Deployment

### System Requirements

- **Python** 3.10 or later
- **OS**: Windows / macOS / Linux
- **Network**: Access to target websites required

### Installation Methods

```bash
# Option 1: Install from PyPI (recommended)
pip install crawl-pilot

# Option 2: Install latest from GitHub
pip install git+https://github.com/gitstq/CrawlPilot.git

# Option 3: Install from source (recommended for developers)
git clone https://github.com/gitstq/CrawlPilot.git
cd CrawlPilot
pip install -e .
```

### Optional Dependencies

```bash
# High-performance HTTP client (recommended for large-scale crawling)
pip install crawl-pilot[httpx]

# Fast HTML/XML parsing (recommended for complex pages)
pip install crawl-pilot[lxml]

# Install all optional dependencies
pip install crawl-pilot[all]
```

### Verify Installation

```bash
# Check version
crawl-pilot --version

# View help
crawl-pilot --help

# Quick test
crawl-pilot crawl https://example.com -o json
```

---

## 🤝 Contributing

We welcome and appreciate every contributor! Whether it's filing a bug report, improving documentation, or contributing code — every effort makes CrawlPilot better.

### Contribution Workflow

1. **Fork** this repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Commit your changes: `git commit -m "feat: add your feature description"`
4. Push the branch: `git push origin feature/your-feature-name`
5. Submit a **Pull Request**

### Development Setup

```bash
git clone https://github.com/gitstq/CrawlPilot.git
cd CrawlPilot
pip install -e ".[all]"
pip install pytest   # Testing framework

# Run tests
pytest tests/
```

### Code Standards

- Follow **PEP 8** coding conventions
- Write **unit tests** to cover new features
- Maintain **backward compatibility**, avoid breaking changes
- Follow the **Conventional Commits** specification for commit messages

### Commit Message Format

```
feat: new feature
fix: bug fix
docs: documentation update
style: code formatting
refactor: code refactoring
test: test-related
chore: build/tooling
```

---

## 📄 License

This project is licensed under the **[MIT License](https://opensource.org/licenses/MIT)**.

```
MIT License

Copyright (c) 2024 CrawlPilot Team

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

<p align="center">
  Built with ❤️ | CrawlPilot Team
</p>
