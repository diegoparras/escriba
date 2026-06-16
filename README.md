<div align="center">

# ✍️ Escriba

**The universal translator into the language of AI.**

Turn any document into clean, anonymized Markdown — ready for any LLM, and exportable
to Word, XML and more. The headaches of feeding documents to an LLM, solved in one
self‑hostable tool: **noisy, token‑hungry input** → clean Markdown, **sensitive‑data
leakage** → built‑in PII anonymization with reversible pseudonymization, and a built‑in
**LLM prep panel** that counts tokens, estimates cost with live pricing, checks
context‑window fit and chunks for RAG. Local, in 7 languages, built on
[Microsoft MarkItDown](https://github.com/microsoft/markitdown).

[![License: MIT](https://img.shields.io/badge/License-MIT-e07f5c.svg)](LICENSE)
[![Docker image](https://img.shields.io/badge/image-ghcr.io%2Fdiegoparras%2Fescriba-2496ED?logo=docker&logoColor=white)](https://github.com/diegoparras/escriba/pkgs/container/escriba)
[![UI: 7 languages](https://img.shields.io/badge/UI-7%20languages-f0a98c.svg)](#-internationalization)
![Self-hosted](https://img.shields.io/badge/self--hosted-✓-30d158.svg)

<img src="assets/demo.gif" alt="Escriba demo" width="840">

📖 **Full manual (PDF):** [`docs/Escriba-Manual.pdf`](docs/Escriba-Manual.pdf)

**English** · [Español](docs/i18n/README.es.md) · [Français](docs/i18n/README.fr.md) · [Português](docs/i18n/README.pt.md) · [Italiano](docs/i18n/README.it.md) · [中文](docs/i18n/README.zh.md) · [日本語](docs/i18n/README.ja.md)

</div>

---

## ✨ Features

- 📄 **Documents** — PDF, Word, Excel, PowerPoint, HTML, CSV, EPUB, ZIP and more.
- 🖼️ **Images** — automatic OCR (Tesseract); optional AI description.
- 🎙️🎬 **Audio & video** — local, offline transcription with Whisper (mp3, wav, mp4, mov, mkv…).
- 🔗 **URLs & YouTube** — convert a web page or fetch a YouTube transcript.
- 🔍 **Smart OCR** — text in images is recognized automatically; scanned **and rotated** PDFs are detected, OCR’d and auto‑straightened on the fly.
- 📑 **Page selection** — for long PDFs, convert only the pages you need: a range (`5–67`), individual pages (`1, 6, 9`) or a mix (`1, 2, 5‑67`). Chosen per file with a simple picker that shows the document’s page count — no syntax to remember.
- 🤖 **Optional AI** — OpenAI, Google Gemini (AI Studio) or OpenRouter, with a **“No AI”** default. Models are listed automatically.
- 🛡️ **PII anonymization for LLMs** — a full local privacy engine ([see below](#-anonymization-for-llms)): NER model ([OpenAI Privacy Filter](https://github.com/openai/privacy-filter)) + layout‑aware invoice fields + validated detectors (credit‑card **Luhn**, **IBAN**) + your own **RE2** rules. Five output modes: *typed*, *anonymous*, **reversibly pseudonymized** (`«PERSONA_1»` → send to the LLM → re‑hydrate locally), **partial masking** (`••••‑3456`) and **stable hashing** (same data → same pseudonym across documents).
- ⬛ **Visual redaction** — download your PDF or scanned image with the PII **blacked out on the page**. True redaction: the text and the pixels underneath are removed from the file, not covered — and the document’s **metadata** (title, author, keywords, XMP) is scrubbed too, so nothing leaks in *Properties*.
- 📤 **Export to 13 formats** — beyond Markdown, one unified menu exports the result to **Word (.docx)**, ODT, EPUB, HTML, LaTeX, reStructuredText and structured **XML** (DocBook, JATS, TEI, OPML) via [Pandoc](https://pandoc.org/), plus data formats **JSON**, **YAML** and **[TOON](https://github.com/toon-format/toon)** (compact & token‑efficient for LLMs). No LLM involved.
- 🔊 **Text to audio (podcast)** — turn the converted document into an **MP3**: a single‑voice **narration** or an AI‑scripted **two‑host podcast**. Local [Piper](https://github.com/rhasspy/piper) voices (offline, 14 voices across es/en/pt/fr/it/de/zh) or optional **OpenAI** cloud voices, with pitch / speed / volume controls.
- ✏️ **Built‑in Markdown editor** — open the result in a **full‑screen editor with live preview** to clean it up before exporting or voicing it. Your edits flow through to every output (Word, XML, MP3…).
- 🧠 **LLM prep panel** — every conversion shows a **token count** (tiktoken), the **tokens & cost saved** by anonymization, a **live per‑model cost estimate** (pricing pulled from [OpenRouter](https://openrouter.ai/)), **context‑window fit** across hundreds of models, one‑click **RAG chunking**, and a **prompt‑injection detector**. All local, no AI calls.
- 🔬 **Advanced PDF extraction** — opt‑in [OpenDataLoader](https://github.com/opendataloader-project/opendataloader-pdf) engine for complex layouts: better reading order (XY‑Cut++) and heading hierarchy, with automatic fallback to the default extractor.
- 🌍 **7 UI languages** — English, Español, Français, Português, Italiano, 中文, 日本語 (auto‑detected, switchable).
- 👑😇👤 **Three access levels** — DIOS / ANGEL / HUMANO, each with its own password and limits.
- 🔒 **Private by design** — uploaded files are deleted right after conversion; nothing is stored.
- 🛡️ **Hardened** — anti‑SSRF, XSS sanitization, per‑role rate limiting, non‑root container, security headers.
- 🐳 **One self‑contained image** — ffmpeg, OCR, Whisper and Redis are bundled. No extra services required.

---

## 🚀 Quick start

Pull the prebuilt image and run it with a single command:

```bash
docker run -d --name escriba --restart unless-stopped -p 8000:8000 \
  -e SECRET_KEY="$(openssl rand -hex 32)" \
  -e GOD_PASSWORD="change-me" \
  ghcr.io/diegoparras/escriba:latest
```

Open **http://localhost:8000** and sign in with the `GOD_PASSWORD` you set.

> The image bundles everything (ffmpeg, Tesseract OCR, Whisper, embedded Redis). No additional services are needed.

---

## 🛳️ Deployment

Pick the platform you use. Everything runs from the single image above.

> Before you start, copy `.env.example` to `.env` and set your secrets
> (`SECRET_KEY`, `GOD_PASSWORD`, …). Generate keys with `openssl rand -hex 32`.

<details open>
<summary><b>EasyPanel</b></summary>

1. **Project → + Service → App**, then set **Source → Docker Image** to `ghcr.io/diegoparras/escriba:latest`.
2. Add your **environment variables** (see [Configuration](#-configuration)).
3. Under **Domains**, set **Container Port `8000`**, add your domain and enable HTTPS.
4. **Deploy.**
</details>

<details>
<summary><b>Docker Compose</b></summary>

```bash
git clone https://github.com/diegoparras/escriba.git
cd escriba
cp .env.example .env          # set your secrets
docker compose up -d --build
```
</details>

<details>
<summary><b>Portainer</b></summary>

**Stacks → Add stack → Repository** using
`https://github.com/diegoparras/escriba` and compose path `docker-compose.yml`
(or paste the `docker-compose.yml` in the web editor). Set the environment
variables and deploy; the app listens on port `8000`.
</details>

<details>
<summary><b>Dokploy</b></summary>

**Create Application → GitHub** (repo `diegoparras/escriba`) with **Build Type:
Dockerfile**, add your environment variables, set the domain to **Container Port
`8000`** with HTTPS, and deploy.
</details>

<details>
<summary><b>Plain Docker / reverse proxy</b></summary>

```bash
docker build -t escriba .
docker run -d --name escriba --restart unless-stopped -p 8000:8000 \
  -e SECRET_KEY="$(openssl rand -hex 32)" -e GOD_PASSWORD="change-me" escriba
```

For TLS, put a reverse proxy in front. Example `Caddyfile` (automatic HTTPS):

```caddy
example.com {
    reverse_proxy localhost:8000
}
```

With Nginx, proxy to `localhost:8000` and raise `client_max_body_size` for large uploads.
</details>

---

## ⚙️ Configuration

All settings are environment variables. Minimum recommended:

```env
SECRET_KEY=<openssl rand -hex 32>   # required in production (sessions reset otherwise)
GOD_PASSWORD=<a strong password>
ANGEL_PASSWORD=<optional>
HUMAN_PASSWORD=<optional>
```

If no password is set, a random `GOD_PASSWORD` is generated and printed to the
container **logs** on startup.

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | *(random)* | Session signing key. **Set it** in production. |
| `GOD_PASSWORD` / `ANGEL_PASSWORD` / `HUMAN_PASSWORD` | — | Password for each access level. |
| `HUMAN_OPEN` | `false` | Allow the HUMANO level without login (public converter). |
| `WEB_CONCURRENCY` | `auto` | Parallel workers. `auto` = number of CPU cores. |
| `MAX_UPLOAD_MB` | `100` | Absolute upload size cap (except DIOS). |
| `WHISPER_MODEL` | `base` | Transcription model: `tiny` · `base` · `small` · `medium` · `large-v3`. |
| `MAX_MEDIA_MINUTES` | `120` | Max audio/video duration to transcribe (`0` = unlimited; DIOS has no cap). |
| `OPENAI_API_KEY` / `OPENROUTER_API_KEY` / `GOOGLE_API_KEY` | — | Server‑side AI keys (fallback when the user provides none). Used by DIOS and ANGEL only. |
| `API_TOKEN` / `API_TOKEN_ROLE` | — / `angel` | Static token for automation (n8n, scripts) and the role it maps to. |
| `EMBEDDED_REDIS` | `true` | Built‑in Redis for shared rate limiting. Set `false` + `REDIS_URL` for an external one. |
| `YT_PROXY` / `YT_COOKIES` | — | Optional proxy / cookies.txt for YouTube if its transcripts are blocked from your server IP. Users can also paste their own cookies in **⚙ Settings → YouTube cookies** (no file or restart needed). |
| `ANONIMAL_URL` | — | Enables PII anonymization. Point it at the internal **Anonimal** service (e.g. `http://anonimal:8000`). Leave empty to hide the feature. See [`anonimal/`](anonimal/). |
| `ENABLE_DOCS` | `false` | Expose Swagger at `/api/docs`. |
| `PORT` | `8000` | Container port. |

Per‑level limits (`*_MAX_MB`, `*_MAX_BATCH`, `*_RATE`) and presets are documented in
[`.env.example`](.env.example).

**Performance:** by default the app spawns one worker per CPU core, so it adapts to
any host (1‑core VPS → 1 worker; 24‑thread server → 24). Each worker uses ~250 MB of
RAM; set `WEB_CONCURRENCY` to a fixed number to cap it.

---

## 🔐 Roles & access levels

Login is required. Each level has its own password and limits.

| Capability | 👤 HUMANO | 😇 ANGEL | 👑 DIOS |
|---|:---:|:---:|:---:|
| Upload & convert files | ✓ | ✓ | ✓ |
| Convert from a public URL | — | ✓ (anti‑SSRF) | ✓ |
| Internal URL / `file://` / local path | — | — | ✓ |
| Audio / video / ZIP | — | ✓ | ✓ |
| YouTube transcripts | ✓ | ✓ | ✓ |
| OCR (forced / automatic) | — | ✓ | ✓ |
| Use server‑side AI keys | — | ✓ | ✓ |
| Max file size | 25 MB | 100 MB | unlimited |
| Files per batch | 3 | 10 | unlimited |
| Server stats (CPU/RAM) | — | partial | full |
| Rate limit (req/min) | 15 | 60 | unlimited |

All limits are configurable via environment variables.

**Security highlights:** local‑file access and SSRF are restricted to DIOS; URL
fetching blocks internal IPs and redirects; uploads are size‑capped via streaming;
the preview is sanitized with DOMPurify; CSP and security headers are set; the
container runs as a non‑root user with `no-new-privileges`; rate limiting is shared
across workers via the embedded Redis.

---

## 🛡️ Anonymization for LLMs

Escriba can strip or replace personal data **before** the text reaches an LLM — and
put it back afterwards. The heavy model runs in a separate, internal‑only service
(**Anonimal**, bundling [OpenAI Privacy Filter](https://github.com/openai/privacy-filter)),
enabled by pointing `ANONIMAL_URL` at it (see [`anonimal/`](anonimal/)).

**Layered detection (high recall by design):**
- **NER model** — names, organizations, locations, dates.
- **Layout‑aware invoice fields** — reads *label → value* by PDF coordinates (Razón Social, CUIT, Domicilio…), masking structured documents field by field.
- **20 toggleable detectors**, per user — *universal* (email, URL, IP, MAC, credit‑card **Luhn‑validated**, **IBAN mod‑97**), *regional* (Argentine CUIT/CUIL/CBU/DNI/addresses) and *aggressive* (long numbers, name sequences).
- **Bring Your Own Rules** — upload a JSON of your own patterns/labels/keep‑list. User regex runs on **RE2** (linear time → **ReDoS‑proof**); strict JSON parsing, hard limits, closed placeholder allowlist.
- **Entity propagation** — anything detected once is masked in every occurrence.

**Five output modes:**

| Mode | Output | Use |
|---|---|---|
| Typed | `<PRIVATE_PERSON>`, `<ACCOUNT_NUMBER>`… | keep the category visible |
| Anonymous | `<<ANOM_DATA>>` | flatten everything |
| **Pseudonymize** | `«PERSONA_1»` + a token→original map | **the LLM gateway** — anonymize → send to the LLM → **re‑hydrate** the reply locally |
| Partial mask | `••••‑3456`, `j•••@domain.com` | keep a usable hint (last digits, email domain) — irreversible |
| Stable hash | `«PERSONA_7590fc»` | same data → **same pseudonym in every document** (anonymized cross‑doc linkage) — irreversible |

Two intensities (**Balanced** / **Strict**), all configurable **per browser**. The
restore map and your custom rules never leave your machine.

**⬛ Visual redaction.** For PDFs and scanned images, the result card offers a
**“Redacted PDF”** download: every detected entity is **blacked out on the page**
using true redaction — `apply_redactions` removes the underlying text *and* the
image pixels beneath each box, so the data no longer exists in the output file.
The PDF’s **metadata is wiped** too (DocInfo + XMP), so a redacted file can’t leak
the name/ID via *Properties* or `exiftool`. Scanned documents are OCR’d automatically
first. Same detection stack (NER + detectors + invoice layout + your RE2 rules), zero extra RAM.

---

## 📤 Export beyond Markdown

Clean Markdown is the core, but the result card’s **single “Format…” menu** turns it
into whatever your workflow needs — pick a format, then hit **Download** (it never
fires on its own). Powered by [Pandoc](https://pandoc.org/), with no LLM involved:

| Family | Formats |
|---|---|
| Markdown | `.md`, compact (whitespace‑stripped), RAG chunks (`.jsonl`) |
| Office & ebook | **Word `.docx`**, ODT, EPUB |
| Web & typesetting | HTML, LaTeX, reStructuredText |
| Structured XML | **DocBook**, **JATS**, **TEI**, **OPML** |
| Privacy | redacted PDF (PII blacked out — see above) |

---

## 🧠 LLM prep panel

Every conversion comes with a compact panel that gets the text ready for a model —
**entirely locally, with zero AI calls:**

- **Token count** with `tiktoken` (`o200k_base`, baked into the image — works offline).
- **Tokens & cost saved** by anonymization, so you can see what stripping PII buys you.
- **Live per‑model cost estimate** — pricing and context windows pulled from
  [OpenRouter](https://openrouter.ai/) (hundreds of models, cached) so the numbers
  are never stale.
- **Context‑window fit** — at a glance, which models the document fits into.
- **One‑click RAG chunking** — split into overlapping, token‑bounded chunks (`semchunk`),
  downloadable as `.jsonl`.
- **Prompt‑injection detector** — flags text that tries to hijack a downstream LLM.

---

## 🔌 API

Useful for automation (n8n, scripts). Authentication is required.

**With an API token** (define `API_TOKEN`):

```bash
curl -H "X-API-Key: YOUR_TOKEN" \
     -F "file=@document.pdf" \
     https://your-domain/api/convert
# Force OCR / set language:  -F "ocr=true"  -F "lang=es-ES"
```

**With a session cookie:**

```bash
curl -c cookies.txt -F "password=$GOD_PASSWORD" https://your-domain/api/login
curl -b cookies.txt -F "file=@document.pdf"     https://your-domain/api/convert
```

`POST /api/convert` (multipart/form-data): `file` *or* `url`, plus optional `lang`,
`ocr`, `llm_provider`, `llm_api_key`, `llm_model`. Response:

```json
{ "source": "…", "title": "…", "markdown": "…",
  "words": 1234, "chars": 5678, "elapsed_ms": 87,
  "pdf_type": "scanned", "ocr_applied": true, "note": null }
```

`POST /api/redact` (multipart/form-data): `file` (PDF or image), optional `lang`,
`anon_strict`, `anon_detectors`, `anon_rules`. Returns the **redacted PDF**
(binary) with the `X-Redacted-Entities` header counting what was blacked out.

Markdown post‑processing (JSON in, JSON or file out):

| Endpoint | Method | Description |
|---|---|---|
| `/api/export` | POST | Convert Markdown to a target format (`docx`, `odt`, `epub`, `html`, `latex`, `rst`, `docbook`, `jats`, `tei`, `opml`). |
| `/api/compact` | POST | Whitespace‑stripped Markdown to save tokens. |
| `/api/chunk` | POST | Token‑bounded RAG chunks (returns `.jsonl`). |
| `/api/model_prices` | GET | Live model pricing & context windows (OpenRouter, cached). |

---

## 🌍 Internationalization

The interface ships in **7 languages** — English, Español, Français, Português,
Italiano, 中文 and 日本語. The language is auto‑detected from the browser and can be
changed anytime from the ⚙️ settings panel; the choice is remembered per browser.

---

## 💻 Local development

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

> OCR and transcription need `ffmpeg`, `tesseract-ocr` and `ocrmypdf` installed on
> the host (the Docker image already includes them). Other formats work without them.

---

## 📜 Credits & license

**Escriba** — developed by **Diego Parrás**
CeMIACE · SEUBES · FCE‑UBA (Facultad de Ciencias Económicas, Universidad de Buenos Aires).

Built on [Microsoft MarkItDown](https://github.com/microsoft/markitdown),
[FastAPI](https://fastapi.tiangolo.com/),
[Tesseract OCR](https://github.com/tesseract-ocr/tesseract),
[OCRmyPDF](https://github.com/ocrmypdf/OCRmyPDF) and
[faster‑whisper](https://github.com/SYSTRAN/faster-whisper).
Licensed under the [MIT License](LICENSE).
