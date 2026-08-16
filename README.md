# 在线翻译小工具（桌面版）

轻量级桌面翻译辅助工具：框选屏幕任意区域、全局取词、区域持续翻译，**本地 OCR** 识别文字后经翻译引擎翻译，结果以伪流式（打字机）效果展示。免去「复制 → 切换页面 → 粘贴 → 翻译」的繁琐流程。

面向需要频繁处理多语言内容的办公人群、学生和开发者。

## ✨ 功能特性

- **截屏翻译**：框选屏幕任意区域 → 本地 OCR 识别 → 翻译。适用于图片文字、视频字幕、软件界面、无法复制的文本。
- **取词翻译**：在任意应用选中文字，按全局热键（默认 `Ctrl+Alt+T`，可自定义）→ 经剪贴板读取选中文本 → 翻译 → 置顶气泡展示，不抢焦点。
- **区域翻译**：呼出透明悬浮框，覆盖到目标区域后点击「开始」，持续截图 + OCR + 翻译；区域内文字变化时自动跟进翻译；内容未变化或已是目标语言时**跳过翻译**，避免浪费 API 额度。
- **多翻译引擎**：DeepL / Google Cloud Translation / OpenAI 兼容接口（可接 ChatGPT、DeepSeek、通义、月之暗面等），右上角设置内一键切换并测试连接。
- **伪流式输出**：WebSocket 逐句推送，前端逐字打字机渲染。
- **系统托盘常驻**：主窗口关闭最小化到托盘，取词、区域翻译后台可用。
- **本地 OCR**：PP-OCRv6（PaddleOCR 3.x）本地部署，数据不出内网、零调用成本。
- **深色科技感 UI**：玻璃拟态、发光描边、暗色主题。

## 🛠 技术架构

桌面单进程应用：`python run.py` 单进程同时运行 FastAPI（托管前端构建产物、REST/WebSocket API、进程内 PP-OCRv6）与 pywebview（WebView2）原生窗口。

| 层 | 选型 |
| --- | --- |
| 桌面壳 | pywebview（Windows WebView2）+ pystray 系统托盘 + keyboard 全局热键 + mss 截屏 |
| 前端 | Vue 3 + Vite + TypeScript + Arco Design Vue + Pinia |
| 后端 | Python + FastAPI（REST + WebSocket 伪流式） |
| OCR | PP-OCRv6（PaddleOCR 3.x，本地 CPU/GPU 推理） |
| 翻译引擎 | DeepL API / Google Cloud Translation v2 / OpenAI 兼容接口（可插拔） |

## 📁 目录结构

```
.
├── run.py                  # 桌面应用入口（pywebview 窗口 + 托盘 + 热键 + FastAPI）
├── backend/                # FastAPI 后端
│   ├── config.py           # .env 配置（Pydantic Settings）
│   ├── main.py             # 应用工厂、路由挂载、静态托管
│   ├── routers/            # translate / wordpick / ws / region / settings
│   └── services/           # ocr / provider / deepl / google / openai_compat / streaming / wordpick / region
├── frontend/               # Vue 3 前端
│   ├── src/                # 主界面（App.vue、组件、stores、api）
│   └── public/             # 取词气泡 bubble.html、区域翻译框 region.html
├── utils/                  # screenshot.py（mss）、hotkey.py（全局热键）
├── .env.example            # 配置模板（复制为 .env）
└── requirements.txt        # Python 依赖
```

## 📋 环境要求

- **Python 3.10+**
- **Node.js 18+**（仅构建前端时需要）
- **Windows 10/11**（依赖 WebView2 运行时，通常系统自带）
- 首次使用 OCR 会联网下载 PP-OCRv6 模型（约数百 MB，取决于网络）

## 🚀 快速开始

### 1. 克隆并安装后端依赖

```bash
git clone <仓库地址> && cd 在线翻译小工具
python -m venv .venv
.venv\Scripts\activate          # Windows 激活虚拟环境
pip install -r requirements.txt
```

> GPU 推理（可选）：安装 GPU 版 PaddlePaddle 后，将 `.env` 中 `OCR_DEVICE=gpu`。

### 2. 构建前端

```bash
cd frontend
npm install
npm run build
```

### 3. 配置 API Key

复制配置模板并按需填写，或**直接启动后在右上角「设置」中填写**（推荐，无需手动编辑文件）：

```bash
cp .env.example .env
```

### 4. 启动

```bash
python run.py
```

## ⚙️ 配置说明（.env）

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `HOST` / `PORT` | `127.0.0.1` / `8765` | 本地服务监听地址与端口 |
| `TRANSLATE_PROVIDER` | `deepl` | 翻译引擎：`deepl` / `google` / `openai` |
| `DEEPL_API_KEY` | 空 | DeepL API Key（[注册获取](https://www.deepl.com/pro-api)，Free 版每月 50 万字符） |
| `GOOGLE_API_KEY` | 空 | Google Cloud Translation v2 API Key |
| `OPENAI_API_KEY` / `OPENAI_BASE_URL` / `OPENAI_MODEL` | 空 | OpenAI 兼容接口（可填 DeepSeek/通义等 base_url 与模型名） |
| `OCR_LANG` | `ch` | OCR 语言（`ch`=中英混合；50 语言可改 `en` 等，见 PaddleOCR 文档） |
| `OCR_DEVICE` | `cpu` | OCR 推理设备（`cpu` / `gpu`） |
| `WORD_PICK_HOTKEY` | `ctrl+alt+t` | 取词翻译全局热键（避免 `Ctrl+Shift+T` 浏览器冲突） |
| `WORD_PICK_LANG` | `ZH` | 取词翻译目标语言（ZH/EN/JA/KO…） |
| `REGION_POLL_INTERVAL` | `2.0` | 区域翻译轮询间隔（秒） |
| `EXIT_ON_CLOSE` | `false` | 点主窗口 × 直接退出，否则最小化到托盘 |

## 🖱 使用说明

**截屏翻译**：主界面点「截图翻译」→ 框选屏幕区域 → 本地 OCR 识别填入原文 → 确认/修正后点「翻译」。

**取词翻译**：在任意应用选中文字 → 按全局热键（默认 `Ctrl+Alt+T`）→ 译文在置顶气泡中展示。

**区域翻译**：主界面点「区域翻译」→ 透明悬浮框出现（可拖动、缩放）→ 覆盖到目标区域 → 点「开始」→ 译文覆盖显示在框内，文字变化自动跟进；「停止」结束；「关闭」返回主界面。目标语言复用「取词翻译语言」设置。

## 💻 开发模式

前端热更新开发：

```bash
# 终端 1：启动后端（run.py 或 uvicorn backend.main:app）
python run.py

# 终端 2：启动 Vite 开发服务器（http://localhost:5173，已代理 /api 与 /ws 到 8765）
cd frontend
npm run dev
```

> 注意：截屏、全局热键、区域翻译等桌面能力依赖 pywebview 桥，仅桌面窗口（`python run.py`）可用；浏览器开发模式只用于界面调试。

## ❓ 常见问题

- **热键注册失败**：`keyboard` 库在某些系统/权限下无法全局监听，尝试以管理员身份运行；或更换热键（`WORD_PICK_HOTKEY`）。
- **首次 OCR 较慢/失败**：PaddleOCR 首次调用会下载模型，请保证网络；模型下载失败可手动从 PaddleOCR 官方源下载放入用户目录。
- **GPU 推理报错**：PaddlePaddle 3.x CPU/GPU 版本不兼容混装，按需安装对应版本并设置 `OCR_DEVICE`。
- **端口被占用**：修改 `.env` 中 `PORT`。
- **区域翻译框透明不生效**：透明窗口依赖 WebView2，个别环境可能显示灰底，属 pywebview 平台限制。

## 🔒 安全说明

- API Key 一律通过 `.env` 或应用内「设置」管理，**切勿硬编码进源码**；`.env` 已被 `.gitignore` 忽略。
- OCR 为本地部署，截图与文本不出内网。
- 本地服务仅监听 `127.0.0.1`，前端 CORS 仅放行本机来源，防止任意网页读取本机数据。

## 📚 参考资料

- [DeepL API](https://www.deepl.com/pro-api) · [PaddleOCR / PP-OCRv6](https://www.paddleocr.ai/)
