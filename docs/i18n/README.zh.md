<div align="center">

# ✍️ Escriba

**通往 AI 语言的通用翻译器。**

将任何文档转换为干净、匿名的 Markdown —— 可直接喂给任意 LLM，还能导出为 Word、XML 等格式。一个可自托管的工具，解决向 LLM 喂文档时的种种烦恼：嘈杂、耗 token 的输入 → 干净的 Markdown，敏感数据泄露 → 内置带可还原假名化的 PII 匿名化，以及一个内置的 LLM 准备面板，可统计 token、用实时定价估算成本、检查是否适配上下文窗口并为 RAG 分块。本地运行，支持 7 种语言，基于 [Microsoft MarkItDown](https://github.com/microsoft/markitdown) 构建。

[![License: MIT](https://img.shields.io/badge/License-MIT-e07f5c.svg)](../../LICENSE)
[![Docker 镜像](https://img.shields.io/badge/image-ghcr.io%2Fdiegoparras%2Fescriba-2496ED?logo=docker&logoColor=white)](https://github.com/diegoparras/escriba/pkgs/container/escriba)
[![界面：7 种语言](https://img.shields.io/badge/UI-7%20languages-f0a98c.svg)](#-国际化)
![可自托管](https://img.shields.io/badge/self--hosted-✓-30d158.svg)

<img src="../../assets/demo.gif" alt="Escriba 演示" width="840">

📖 **完整手册（PDF）：** [`docs/Escriba-Manual.zh.pdf`](../Escriba-Manual.zh.pdf)

[English](../../README.md) · [Español](README.es.md) · [Français](README.fr.md) · [Português](README.pt.md) · [Italiano](README.it.md) · **中文** · [日本語](README.ja.md)

</div>

---

## ✨ 功能

- 📄 **文档** —— PDF、Word、Excel、PowerPoint、HTML、CSV、EPUB、ZIP 等。
- 🖼️ **图片** —— 自动 OCR（Tesseract）；可选的 AI 描述。
- 🎙️🎬 **音频与视频** —— 使用 Whisper 进行本地、离线转写（mp3、wav、mp4、mov、mkv 等）。
- 🔗 **网址与 YouTube** —— 转换网页，或获取 YouTube 视频的字幕转写。
- 🔍 **智能 OCR** —— 自动识别图片中的文字；扫描版**及旋转的** PDF 会被即时检测、OCR 处理并自动纠正方向。
- 📑 **页面选择** —— 对于长篇 PDF，只转换你需要的页面：可指定范围（`5-67`）、单独页面（`1, 6, 9`）或两者混合（`1, 2, 5-67`）。每个文件单独选择，通过一个简单的选择器完成，并显示文档的总页数 —— 无需记忆任何语法。
- 🤖 **可选 AI** —— OpenAI、Google Gemini（AI Studio）或 OpenRouter，默认 **「不使用 AI」**。自动列出可用模型。
- 🛡️ **面向 LLM 的 PII 匿名化** — 完整的本地隐私引擎：NER 模型（[OpenAI Privacy Filter](https://github.com/openai/privacy-filter)）+ 基于版面的票据字段 + 校验型检测器（信用卡 **Luhn**、**IBAN**）+ 你自己的 **RE2** 规则。五种输出模式：*类型化*、*匿名*、**可还原假名化**（«PERSONA_1» → 发送给 LLM → 本地还原）、**部分掩码**（••••-3456）和**稳定哈希**（相同数据 → 跨文档相同假名）。
- ⬛ **可视化遮蔽** — 下载 PII **在页面上被涂黑**的 PDF 或扫描图片。真正的涂黑：文字与底层像素都从文件中删除，而不是覆盖 —— 文档的**元数据**（标题、作者、关键词、XMP）也会被一并清除，因此在*属性*中不会泄露任何信息。PDF 的**元数据也会被抹除**（DocInfo + XMP），因此遮蔽后的文件不会通过*属性*或 `exiftool` 泄露姓名/证件号。
- 📤 **导出为 10 种格式** — 除 Markdown 外，一个统一的下载菜单可将结果导出为 **Word（.docx）**、ODT、EPUB、HTML、LaTeX、reStructuredText 以及结构化 **XML**（DocBook、JATS、TEI、OPML）—— 由 [Pandoc](https://pandoc.org/) 提供支持。不涉及任何 LLM。
- 🔊 **文字转音频（podcast）** —— 将转换后的文档变成 **MP3**：可以是单人**旁白朗读**，也可以是由 AI 撰写脚本的**双人主持 podcast**。使用本地 [Piper](https://github.com/rhasspy/piper) 语音（离线，覆盖 es/en/pt/fr/it/de/zh 的 14 种声音），或可选的 **OpenAI** 云端语音，并支持音高 / 语速 / 音量调节。
- 🧠 **LLM 准备面板** — 每次转换都会显示 **token 数**（tiktoken）、匿名化所**节省的 token 与成本**、**按模型的实时成本估算**（定价取自 [OpenRouter](https://openrouter.ai/)）、跨数百个模型的**上下文窗口适配**情况、一键 **RAG 分块**以及一个**提示注入检测器**。全部本地运行，无任何 AI 调用。
- 🔬 **高级 PDF 提取** — 可选启用 [OpenDataLoader](https://github.com/opendataloader-project/opendataloader-pdf) 引擎，处理复杂版面：更优的阅读顺序（XY-Cut++）与标题层级，并在需要时自动回退到默认提取器。
- 🌍 **7 种界面语言** —— English、Español、Français、Português、Italiano、中文、日本語（自动检测，可切换）。
- 👑😇👤 **三种访问级别** —— DIOS / ANGEL / HUMANO，各有独立密码与限额。
- 🔒 **隐私优先** —— 上传的文件在转换后立即删除；不会存储任何内容。
- 🛡️ **安全加固** —— 防 SSRF、XSS 净化、按角色限流、非 root 容器、安全响应头。
- 🐳 **单一自包含镜像** —— 内置 ffmpeg、OCR、Whisper 和 Redis。无需额外服务。

---

## 🚀 快速开始

拉取预构建镜像，一条命令即可运行：

```bash
docker run -d --name escriba --restart unless-stopped -p 8000:8000 \
  -e SECRET_KEY="$(openssl rand -hex 32)" \
  -e GOD_PASSWORD="change-me" \
  ghcr.io/diegoparras/escriba:latest
```

打开 **http://localhost:8000**，使用你设置的 `GOD_PASSWORD` 登录。

> 镜像已内置一切（ffmpeg、Tesseract OCR、Whisper、内嵌 Redis），无需额外服务。

---

## 🛳️ 部署

选择你使用的平台。一切都基于上面的镜像运行。

> 开始前，将 `.env.example` 复制为 `.env` 并设置你的密钥
> （`SECRET_KEY`、`GOD_PASSWORD` 等）。用 `openssl rand -hex 32` 生成密钥。

<details open>
<summary><b>EasyPanel</b></summary>

1. **Project → + Service → App**，在 **Source → Docker Image** 填入 `ghcr.io/diegoparras/escriba:latest`。
2. 添加你的**环境变量**（见 [配置](#-配置)）。
3. 在 **Domains** 中设置 **Container Port `8000`**，添加你的域名并启用 HTTPS。
4. **Deploy。**
</details>

<details>
<summary><b>Docker Compose</b></summary>

```bash
git clone https://github.com/diegoparras/escriba.git
cd escriba
cp .env.example .env          # 设置你的密钥
docker compose up -d --build
```
</details>

<details>
<summary><b>Portainer</b></summary>

**Stacks → Add stack → Repository**，填入
`https://github.com/diegoparras/escriba`，compose 路径为 `docker-compose.yml`
（或在 Web 编辑器中粘贴 `docker-compose.yml`）。设置环境变量后部署；应用监听端口 `8000`。
</details>

<details>
<summary><b>Dokploy</b></summary>

**Create Application → GitHub**（仓库 `diegoparras/escriba`），**Build Type：Dockerfile**，
添加环境变量，将域名设置到 **Container Port `8000`** 并启用 HTTPS，然后部署。
</details>

<details>
<summary><b>纯 Docker / 反向代理</b></summary>

```bash
docker build -t escriba .
docker run -d --name escriba --restart unless-stopped -p 8000:8000 \
  -e SECRET_KEY="$(openssl rand -hex 32)" -e GOD_PASSWORD="change-me" escriba
```

如需 TLS，请在前面放置反向代理。`Caddyfile` 示例（自动 HTTPS）：

```caddy
example.com {
    reverse_proxy localhost:8000
}
```

使用 Nginx 时，代理到 `localhost:8000`，并为大文件上传调高 `client_max_body_size`。
</details>

---

## ⚙️ 配置

所有设置均为环境变量。最低推荐：

```env
SECRET_KEY=<openssl rand -hex 32>   # 生产环境必填（否则会话会重置）
GOD_PASSWORD=<一个强密码>
ANGEL_PASSWORD=<可选>
HUMAN_PASSWORD=<可选>
```

若未设置任何密码，启动时会生成随机的 `GOD_PASSWORD` 并打印到容器**日志**中。

| 变量 | 默认值 | 说明 |
|---|---|---|
| `SECRET_KEY` | *（随机）* | 会话签名密钥。生产环境请**务必设置**。 |
| `GOD_PASSWORD` / `ANGEL_PASSWORD` / `HUMAN_PASSWORD` | — | 各访问级别的密码。 |
| `HUMAN_OPEN` | `false` | 允许 HUMANO 级别免登录（公开转换器）。 |
| `WEB_CONCURRENCY` | `auto` | 并行 worker 数。`auto` = CPU 核心数。 |
| `MAX_UPLOAD_MB` | `100` | 上传大小上限（DIOS 除外）。 |
| `WHISPER_MODEL` | `base` | 转写模型：`tiny` · `base` · `small` · `medium` · `large-v3`。 |
| `MAX_MEDIA_MINUTES` | `120` | 可转写的音视频时长上限（`0` = 无限制；DIOS 无上限）。 |
| `OPENAI_API_KEY` / `OPENROUTER_API_KEY` / `GOOGLE_API_KEY` | — | 服务器端 AI 密钥（用户未提供时使用）。仅 DIOS 与 ANGEL。 |
| `API_TOKEN` / `API_TOKEN_ROLE` | — / `angel` | 用于自动化（n8n、脚本）的静态令牌及其映射角色。 |
| `EMBEDDED_REDIS` | `true` | 内置 Redis，用于共享限流。设为 `false` + `REDIS_URL` 使用外部 Redis。 |
| `ENABLE_DOCS` | `false` | 在 `/api/docs` 暴露 Swagger。 |
| `PORT` | `8000` | 容器端口。 |

各级别限额（`*_MAX_MB`、`*_MAX_BATCH`、`*_RATE`）与预设见
[`.env.example`](../../.env.example)。

**性能：** 默认每个 CPU 核心启动一个 worker，因此能适配任何主机（1 核 VPS → 1 worker；
24 线程服务器 → 24）。每个 worker 约占用 250 MB 内存；可将 `WEB_CONCURRENCY` 设为固定值以限制。

---

## 🔐 角色与访问级别

必须登录。每个级别都有独立的密码与限额。

| 能力 | 👤 HUMANO | 😇 ANGEL | 👑 DIOS |
|---|:---:|:---:|:---:|
| 上传并转换文件 | ✓ | ✓ | ✓ |
| 从公开网址转换 | — | ✓（防 SSRF） | ✓ |
| 内网网址 / `file://` / 本地路径 | — | — | ✓ |
| 音频 / 视频 / ZIP | — | ✓ | ✓ |
| YouTube 字幕转写 | ✓ | ✓ | ✓ |
| OCR（强制 / 自动） | — | ✓ | ✓ |
| 使用服务器端 AI 密钥 | — | ✓ | ✓ |
| 单文件大小上限 | 25 MB | 100 MB | 无限制 |
| 每批文件数 | 3 | 10 | 无限制 |
| 服务器统计（CPU/RAM） | — | 部分 | 完整 |
| 限流（次/分钟） | 15 | 60 | 无限制 |

所有限额均可通过环境变量配置。

**安全要点：** 本地文件访问与 SSRF 仅限 DIOS；URL 抓取会拦截内网 IP 与重定向；上传通过流式限制大小；
预览使用 DOMPurify 净化；设置了 CSP 与安全响应头；容器以非 root 用户运行并启用 `no-new-privileges`；
限流通过内置 Redis 在各 worker 间共享。

---

## 📤 超越 Markdown 的导出

干净的 Markdown 是核心，但结果卡片上的**单一「格式…」菜单**可将其转换为你的工作流所需的任意格式 —— 选择一种格式，然后点击 **下载**（它绝不会自动触发）。由 [Pandoc](https://pandoc.org/) 提供支持，不涉及任何 LLM：

| 类别 | 格式 |
|---|---|
| Markdown | `.md`、紧凑版（去除空白）、RAG 分块（`.jsonl`） |
| Office 与电子书 | **Word `.docx`**、ODT、EPUB |
| Web 与排版 | HTML、LaTeX、reStructuredText |
| 结构化 XML | **DocBook**、**JATS**、**TEI**、**OPML** |
| 隐私 | 遮蔽版 PDF（PII 被涂黑 —— 见上文） |

## 🧠 LLM 准备面板

每次转换都附带一个紧凑面板，将文本准备好喂给模型 —— 全部本地完成，零 AI 调用：

- 使用 `tiktoken` 的 **token 数**（`o200k_base`，已内置于镜像中 —— 可离线工作）。
- 匿名化所**节省的 token 与成本**，让你看清剥离 PII 带来的收益。
- **按模型的实时成本估算** —— 定价与上下文窗口取自 [OpenRouter](https://openrouter.ai/)（数百个模型，已缓存），因此数字永不过时。
- **上下文窗口适配** —— 一眼看出文档能装进哪些模型。
- **一键 RAG 分块** —— 切分为带重叠、有 token 上限的分块（`semchunk`），可下载为 `.jsonl`。
- **提示注入检测器** —— 标记试图劫持下游 LLM 的文本。

---

## 🔌 API

适用于自动化（n8n、脚本）。需要身份验证。

**使用 API 令牌**（设置 `API_TOKEN`）：

```bash
curl -H "X-API-Key: 你的令牌" \
     -F "file=@document.pdf" \
     https://你的域名/api/convert
# 强制 OCR / 设置语言：  -F "ocr=true"  -F "lang=zh"
```

**使用会话 Cookie：**

```bash
curl -c cookies.txt -F "password=$GOD_PASSWORD" https://你的域名/api/login
curl -b cookies.txt -F "file=@document.pdf"     https://你的域名/api/convert
```

`POST /api/convert`（multipart/form-data）：`file` *或* `url`，以及可选的 `lang`、
`ocr`、`llm_provider`、`llm_api_key`、`llm_model`。响应：

```json
{ "source": "…", "title": "…", "markdown": "…",
  "words": 1234, "chars": 5678, "elapsed_ms": 87,
  "pdf_type": "scanned", "ocr_applied": true, "note": null }
```

`POST /api/redact`（multipart/form-data）：`file`（PDF 或图片），可选 `lang`、`anon_strict`、`anon_detectors`、`anon_rules`。返回**已遮蔽 PDF**（二进制），响应头 `X-Redacted-Entities` 为涂黑条目数。

Markdown 后处理（输入 JSON，输出 JSON 或文件）：

| 端点 | 方法 | 说明 |
|---|---|---|
| `/api/export` | POST | 将 Markdown 转换为目标格式（`docx`、`odt`、`epub`、`html`、`latex`、`rst`、`docbook`、`jats`、`tei`、`opml`）。 |
| `/api/compact` | POST | 去除空白的 Markdown，节省 token。 |
| `/api/chunk` | POST | 有 token 上限的 RAG 分块（返回 `.jsonl`）。 |
| `/api/model_prices` | GET | 实时模型定价与上下文窗口（OpenRouter，已缓存）。 |

---

## 🌍 国际化

界面提供 **7 种语言** —— English、Español、Français、Português、Italiano、中文 与 日本語。
语言会根据浏览器自动检测，可随时在 ⚙️ 设置面板中切换；选择会按浏览器记住。

---

## 💻 本地开发

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

> OCR 与转写需要在系统中安装 `ffmpeg`、`tesseract-ocr` 与 `ocrmypdf`
> （Docker 镜像已内置）。其他格式无需它们即可工作。

---

## 📜 致谢与许可

**Escriba** —— 由 **Diego Parrás** 开发
CeMIACE · SEUBES · FCE‑UBA（布宜诺斯艾利斯大学经济科学学院）。

基于 [Microsoft MarkItDown](https://github.com/microsoft/markitdown)、
[FastAPI](https://fastapi.tiangolo.com/)、
[Tesseract OCR](https://github.com/tesseract-ocr/tesseract)、
[OCRmyPDF](https://github.com/ocrmypdf/OCRmyPDF) 与
[faster‑whisper](https://github.com/SYSTRAN/faster-whisper) 构建。
采用 [MIT 许可证](../../LICENSE)。
