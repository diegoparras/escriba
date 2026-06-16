<div align="center">

# ✍️ Escriba

**AI の言語への、ユニバーサル翻訳機。**

あらゆる文書を、きれいで匿名化された Markdown に —— あらゆる LLM 対応、さらに Word、XML などへエクスポート可能。LLM に文書を読み込ませる際の頭痛を解決する、セルフホスト可能なツールです：ノイズが多くトークンを浪費する入力 → きれいな Markdown、機微データの漏えい → 可逆仮名化による組み込み PII 匿名化、そしてトークン数を数え、ライブ価格でコストを見積もり、コンテキストウィンドウへの収まりを確認し、RAG 向けにチャンク分割する組み込みの LLM 準備パネル。ローカルで動作、7 言語対応、[Microsoft MarkItDown](https://github.com/microsoft/markitdown) をベースに構築。

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
- 📑 **ページ選択** —— 長い PDF では必要なページだけを変換：範囲（`5-67`）、個別ページ（`1, 6, 9`）、またはその組み合わせ（`1, 2, 5-67`）。ファイルごとに、文書のページ数を表示するシンプルなピッカーで選択 —— 覚えるべき構文はありません。
- 🤖 **任意の AI** —— OpenAI、Google Gemini（AI Studio）、OpenRouter。既定は **「AI を使わない」**。モデルは自動で一覧表示。
- 🛡️ **LLM 向け PII 匿名化** — 完全ローカルのプライバシーエンジン：NER モデル（[OpenAI Privacy Filter](https://github.com/openai/privacy-filter)）+ レイアウト解析による請求書フィールド + 検証付き検出器（クレジットカード **Luhn**、**IBAN**）+ 独自の **RE2** ルール。出力は 5 モード：*型付き*、*匿名*、**可逆仮名化**（«PERSONA_1» → LLM に送信 → ローカルで復元）、**部分マスク**（••••-3456）、**安定ハッシュ**（同じデータ → 文書をまたいで同じ仮名）。
- ⬛ **ビジュアル墨消し** — PII を**ページ上で黒塗り**した PDF・スキャン画像をダウンロード。本物の墨消し：テキストと下のピクセルはファイルから削除されます（上に被せるだけではありません） —— さらに文書の**メタデータ**（タイトル、作成者、キーワード、XMP）も消去されるため、*プロパティ* から何も漏れません。
- 📤 **13 形式へエクスポート** — Markdown だけでなく、統一されたメニュー 1 つで結果を **Word (.docx)**、ODT、EPUB、HTML、LaTeX、reStructuredText、構造化 **XML**（DocBook、JATS、TEI、OPML）へ [Pandoc](https://pandoc.org/) 経由でエクスポートし、さらにデータ形式の **JSON**、**YAML**、**[TOON](https://github.com/toon-format/toon)**（コンパクトで LLM 向けにトークン効率が高い）にも対応。LLM は一切関与しません。
- 🔊 **テキストを音声に（Podcast）** —— 変換した文書を **MP3** に：単一の声による**ナレーション**、または AI が台本を作成する**2 人ホストの Podcast**。ローカルの [Piper](https://github.com/rhasspy/piper) ボイス（オフライン、es/en/pt/fr/it/de/zh の 14 種）または任意の **OpenAI** クラウドボイスを使用し、ピッチ・速度・音量を調整可能。
- ✏️ **組み込みの Markdown エディタ** — 変換結果を**ライブプレビュー付きの全画面エディタ**で開き、エクスポートや音声化の前に整えられます。編集内容はすべての出力（Word、XML、MP3…）に反映されます。
- 🧠 **LLM 準備パネル** — 変換ごとに **トークン数**（tiktoken）、匿名化による **節約トークン数とコスト**、**モデル別のライブコスト見積もり**（価格は [OpenRouter](https://openrouter.ai/) から取得）、数百モデルにわたる **コンテキストウィンドウへの収まり**、ワンクリックの **RAG チャンク分割**、そして **プロンプトインジェクション検出器** を表示。すべてローカルで、AI 呼び出しはありません。
- 🔬 **高度な PDF 抽出** — 複雑なレイアウト向けにオプトインの [OpenDataLoader](https://github.com/opendataloader-project/opendataloader-pdf) エンジン：より優れた読み順（XY-Cut++）と見出し階層を実現し、既定の抽出器へ自動フォールバックします。
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

## 📤 Markdown を超えるエクスポート

きれいな Markdown が中核ですが、結果カードの **単一の「形式…」メニュー** が、それをワークフローに必要なものへ変えます —— 形式を選んで **ダウンロード** を押すだけ（勝手に実行されることはありません）。[Pandoc](https://pandoc.org/) を使用し、LLM は一切関与しません：

| ファミリー | 形式 |
|---|---|
| Markdown | `.md`、コンパクト（空白除去）、RAG チャンク（`.jsonl`） |
| Office・電子書籍 | **Word `.docx`**、ODT、EPUB |
| Web・組版 | HTML、LaTeX、reStructuredText |
| 構造化 XML | **DocBook**、**JATS**、**TEI**、**OPML** |
| プライバシー | 墨消し済み PDF（PII を黒塗り —— 上記参照） |

## 🧠 LLM 準備パネル

変換ごとに、テキストをモデル向けに整えるコンパクトなパネルが付きます —— すべて完全にローカルで、AI 呼び出しはゼロ：

- `tiktoken` による **トークン数**（`o200k_base`、イメージに同梱 —— オフラインで動作）。
- 匿名化による **節約トークン数とコスト**。PII を取り除くことで何が得られるかが分かります。
- **モデル別のライブコスト見積もり** —— 価格とコンテキストウィンドウは [OpenRouter](https://openrouter.ai/) から取得（数百モデル、キャッシュ済み）なので、数値が古くなりません。
- **コンテキストウィンドウへの収まり** —— どのモデルに文書が収まるか一目で分かります。
- **ワンクリックの RAG チャンク分割** —— 重複ありでトークン上限付きのチャンク（`semchunk`）に分割し、`.jsonl` としてダウンロード可能。
- **プロンプトインジェクション検出器** —— 下流の LLM を乗っ取ろうとするテキストを検出します。

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

`POST /api/redact`（multipart/form-data）：`file`（PDF または画像）、任意で `lang`、`anon_strict`、`anon_detectors`、`anon_rules`。**墨消し済み PDF**（バイナリ）を返し、ヘッダー `X-Redacted-Entities` に黒塗り件数が入ります。PDF の**メタデータも消去**されるため（DocInfo + XMP）、墨消し済みファイルが *プロパティ* や `exiftool` 経由で名前/ID を漏らすことはありません。

Markdown の後処理（JSON 入力、JSON またはファイル出力）：

| エンドポイント | メソッド | 説明 |
|---|---|---|
| `/api/export` | POST | Markdown を対象形式へ変換（`docx`、`odt`、`epub`、`html`、`latex`、`rst`、`docbook`、`jats`、`tei`、`opml`）。 |
| `/api/compact` | POST | トークンを節約するため空白を除去した Markdown。 |
| `/api/chunk` | POST | トークン上限付きの RAG チャンク（`.jsonl` を返す）。 |
| `/api/model_prices` | GET | モデルのライブ価格とコンテキストウィンドウ（OpenRouter、キャッシュ済み）。 |

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
