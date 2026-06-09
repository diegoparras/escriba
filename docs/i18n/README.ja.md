<div align="center">

# ✍️ Escriba

**あらゆる文書を、きれいで匿名化された Markdown に —— LLM 対応。**

[Microsoft MarkItDown](https://github.com/microsoft/markitdown) をベースにした、セルフホスト可能な Web アプリです。

[![License: MIT](https://img.shields.io/badge/License-MIT-e07f5c.svg)](../../LICENSE)
[![Docker イメージ](https://img.shields.io/badge/image-ghcr.io%2Fdiegoparras%2Fescriba-2496ED?logo=docker&logoColor=white)](https://github.com/diegoparras/escriba/pkgs/container/escriba)
[![UI: 7 言語](https://img.shields.io/badge/UI-7%20languages-f0a98c.svg)](#-国際化)
![セルフホスト](https://img.shields.io/badge/self--hosted-✓-30d158.svg)

<img src="../../assets/demo.gif" alt="Escriba のデモ" width="840">

📖 **完全マニュアル（PDF）：** [`docs/Escriba-Manual.ja.pdf`](../Escriba-Manual.ja.pdf)

[English](../../README.md) · [Español](README.es.md) · [Français](README.fr.md) · [Português](README.pt.md) · [Italiano](README.it.md) · [中文](README.zh.md) · **日本語**

</div>

---

## ✨ 機能

- 📄 **ドキュメント** —— PDF、Word、Excel、PowerPoint、HTML、CSV、EPUB、ZIP など。
- 🖼️ **画像** —— 自動 OCR（Tesseract）、任意で AI による説明。
- 🎙️🎬 **音声・動画** —— Whisper によるローカル・オフラインの文字起こし（mp3、wav、mp4、mov、mkv など）。
- 🔗 **URL と YouTube** —— Web ページを変換、または YouTube 動画の文字起こしを取得。
- 🔍 **スマート OCR** —— 画像内の文字を自動認識し、スキャン・**回転した** PDF を検出してその場で OCR 処理・自動回転補正。
- 🤖 **任意の AI** —— OpenAI、Google Gemini（AI Studio）、OpenRouter。既定は **「AI を使わない」**。モデルは自動で一覧表示。
- 🕵️ **PII 匿名化（任意）** —— 連携サービス **Anonimal**（[OpenAI Privacy Filter](https://github.com/openai/privacy-filter)）で個人データ（氏名・メール・各種ID…）を**ローカル**で検出・マスク。*型付き*（`<PRIVATE_PERSON>`）または*匿名*（`<<ANOM_DATA>>`）出力。
- 🌍 **7 言語の UI** —— English、Español、Français、Português、Italiano、中文、日本語（自動検出、切替可能）。
- 👑😇👤 **3 つのアクセスレベル** —— DIOS / ANGEL / HUMANO。それぞれ独自のパスワードと制限。
- 🔒 **設計からプライベート** —— アップロードしたファイルは変換後すぐに削除。何も保存しません。
- 🛡️ **堅牢化** —— SSRF 対策、XSS サニタイズ、ロール別レート制限、非 root コンテナ、セキュリティヘッダー。
- 🐳 **単一の自己完結イメージ** —— ffmpeg、OCR、Whisper、Redis を同梱。追加サービス不要。

---

## 🚀 クイックスタート

ビルド済みイメージを取得し、1 つのコマンドで実行：

```bash
docker run -d --name escriba --restart unless-stopped -p 8000:8000 \
  -e SECRET_KEY="$(openssl rand -hex 32)" \
  -e GOD_PASSWORD="change-me" \
  ghcr.io/diegoparras/escriba:latest
```

**http://localhost:8000** を開き、設定した `GOD_PASSWORD` でサインインします。

> イメージにはすべて同梱（ffmpeg、Tesseract OCR、Whisper、組み込み Redis）。追加サービスは不要です。

---

## 🛳️ デプロイ

お使いのプラットフォームを選択してください。すべて上記のイメージから動作します。

> 開始前に `.env.example` を `.env` にコピーし、シークレット（`SECRET_KEY`、`GOD_PASSWORD` など）を
> 設定します。鍵は `openssl rand -hex 32` で生成できます。

<details open>
<summary><b>EasyPanel</b></summary>

1. **Project → + Service → App** で、**Source → Docker Image** に `ghcr.io/diegoparras/escriba:latest` を指定。
2. **環境変数**を追加（[設定](#-設定) を参照）。
3. **Domains** で **Container Port `8000`** を設定し、ドメインを追加して HTTPS を有効化。
4. **Deploy。**
</details>

<details>
<summary><b>Docker Compose</b></summary>

```bash
git clone https://github.com/diegoparras/escriba.git
cd escriba
cp .env.example .env          # シークレットを設定
docker compose up -d --build
```
</details>

<details>
<summary><b>Portainer</b></summary>

**Stacks → Add stack → Repository** に
`https://github.com/diegoparras/escriba`、compose パス `docker-compose.yml` を指定
（または Web エディタに `docker-compose.yml` を貼り付け）。環境変数を設定してデプロイ。
アプリはポート `8000` で待ち受けます。
</details>

<details>
<summary><b>Dokploy</b></summary>

**Create Application → GitHub**（リポジトリ `diegoparras/escriba`）で **Build Type: Dockerfile**、
環境変数を追加し、ドメインを **Container Port `8000`** と HTTPS で設定してデプロイします。
</details>

<details>
<summary><b>素の Docker / リバースプロキシ</b></summary>

```bash
docker build -t escriba .
docker run -d --name escriba --restart unless-stopped -p 8000:8000 \
  -e SECRET_KEY="$(openssl rand -hex 32)" -e GOD_PASSWORD="change-me" escriba
```

TLS には前段にリバースプロキシを置きます。`Caddyfile` の例（自動 HTTPS）：

```caddy
example.com {
    reverse_proxy localhost:8000
}
```

Nginx では `localhost:8000` にプロキシし、大きなアップロード向けに `client_max_body_size` を上げます。
</details>

---

## ⚙️ 設定

すべての設定は環境変数です。最低限の推奨：

```env
SECRET_KEY=<openssl rand -hex 32>   # 本番では必須（未設定だとセッションがリセット）
GOD_PASSWORD=<強いパスワード>
ANGEL_PASSWORD=<任意>
HUMAN_PASSWORD=<任意>
```

パスワードを 1 つも設定しない場合、起動時にランダムな `GOD_PASSWORD` が生成され、
コンテナの**ログ**に表示されます。

| 変数 | 既定値 | 説明 |
|---|---|---|
| `SECRET_KEY` | *(ランダム)* | セッション署名鍵。本番では**必ず設定**。 |
| `GOD_PASSWORD` / `ANGEL_PASSWORD` / `HUMAN_PASSWORD` | — | 各アクセスレベルのパスワード。 |
| `HUMAN_OPEN` | `false` | HUMANO レベルをログインなしで許可（公開コンバーター）。 |
| `WEB_CONCURRENCY` | `auto` | 並列ワーカー数。`auto` = CPU コア数。 |
| `MAX_UPLOAD_MB` | `100` | アップロードの絶対上限（DIOS を除く）。 |
| `WHISPER_MODEL` | `base` | 文字起こしモデル：`tiny` · `base` · `small` · `medium` · `large-v3`。 |
| `MAX_MEDIA_MINUTES` | `120` | 文字起こしする音声/動画の最大長（`0` = 無制限、DIOS は上限なし）。 |
| `OPENAI_API_KEY` / `OPENROUTER_API_KEY` / `GOOGLE_API_KEY` | — | サーバー側 AI キー（ユーザーが指定しない場合に使用）。DIOS と ANGEL のみ。 |
| `API_TOKEN` / `API_TOKEN_ROLE` | — / `angel` | 自動化（n8n、スクリプト）用の固定トークンと割り当てロール。 |
| `EMBEDDED_REDIS` | `true` | 共有レート制限用の組み込み Redis。外部にする場合は `false` + `REDIS_URL`。 |
| `ENABLE_DOCS` | `false` | `/api/docs` に Swagger を公開。 |
| `PORT` | `8000` | コンテナのポート。 |

レベル別の制限（`*_MAX_MB`、`*_MAX_BATCH`、`*_RATE`）とプリセットは
[`.env.example`](../../.env.example) を参照。

**パフォーマンス：** 既定では CPU コアごとに 1 ワーカーを起動するため、あらゆるホストに適応します
（1 コア VPS → 1 ワーカー、24 スレッドサーバー → 24）。各ワーカーは約 250 MB の RAM を使用。
上限を設けるには `WEB_CONCURRENCY` を固定値にします。

---

## 🔐 ロールとアクセスレベル

ログインが必須です。各レベルに独自のパスワードと制限があります。

| 機能 | 👤 HUMANO | 😇 ANGEL | 👑 DIOS |
|---|:---:|:---:|:---:|
| ファイルのアップロードと変換 | ✓ | ✓ | ✓ |
| 公開 URL から変換 | — | ✓（SSRF 対策） | ✓ |
| 内部 URL / `file://` / ローカルパス | — | — | ✓ |
| 音声 / 動画 / ZIP | — | ✓ | ✓ |
| YouTube の文字起こし | ✓ | ✓ | ✓ |
| OCR（強制 / 自動） | — | ✓ | ✓ |
| サーバー側 AI キーの使用 | — | ✓ | ✓ |
| 最大ファイルサイズ | 25 MB | 100 MB | 無制限 |
| 1 バッチあたりのファイル数 | 3 | 10 | 無制限 |
| サーバー統計（CPU/RAM） | — | 一部 | 完全 |
| レート制限（req/分） | 15 | 60 | 無制限 |

すべての制限は環境変数で設定できます。

**セキュリティの要点：** ローカルファイルアクセスと SSRF は DIOS のみ。URL 取得は内部 IP と
リダイレクトをブロック。アップロードはストリーミングでサイズ制限。プレビューは DOMPurify で
サニタイズ。CSP とセキュリティヘッダーを適用。コンテナは非 root ユーザーで `no-new-privileges`
付き。レート制限は組み込み Redis でワーカー間共有。

---

## 🔌 API

自動化（n8n、スクリプト）に便利。認証が必要です。

**API トークンを使う場合**（`API_TOKEN` を設定）：

```bash
curl -H "X-API-Key: あなたのトークン" \
     -F "file=@document.pdf" \
     https://あなたのドメイン/api/convert
# OCR / 言語を強制：  -F "ocr=true"  -F "lang=ja"
```

**セッション Cookie を使う場合：**

```bash
curl -c cookies.txt -F "password=$GOD_PASSWORD" https://あなたのドメイン/api/login
curl -b cookies.txt -F "file=@document.pdf"     https://あなたのドメイン/api/convert
```

`POST /api/convert`（multipart/form-data）：`file` *または* `url`、加えて任意の `lang`、
`ocr`、`llm_provider`、`llm_api_key`、`llm_model`。レスポンス：

```json
{ "source": "…", "title": "…", "markdown": "…",
  "words": 1234, "chars": 5678, "elapsed_ms": 87,
  "pdf_type": "scanned", "ocr_applied": true, "note": null }
```

---

## 🌍 国際化

UI は **7 言語** で提供 —— English、Español、Français、Português、Italiano、中文、日本語。
言語はブラウザから自動検出され、⚙️ 設定パネルでいつでも変更できます。選択はブラウザごとに記憶されます。

---

## 💻 ローカル開発

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

> OCR と文字起こしには、システムに `ffmpeg`、`tesseract-ocr`、`ocrmypdf` が必要です
> （Docker イメージには同梱済み）。その他の形式はこれらがなくても動作します。

---

## 📜 クレジットとライセンス

**Escriba** —— 開発者 **Diego Parrás**
CeMIACE · SEUBES · FCE‑UBA（ブエノスアイレス大学 経済科学部）。

[Microsoft MarkItDown](https://github.com/microsoft/markitdown)、
[FastAPI](https://fastapi.tiangolo.com/)、
[Tesseract OCR](https://github.com/tesseract-ocr/tesseract)、
[OCRmyPDF](https://github.com/ocrmypdf/OCRmyPDF)、
[faster‑whisper](https://github.com/SYSTRAN/faster-whisper) を基に構築。
[MIT ライセンス](../../LICENSE)。
