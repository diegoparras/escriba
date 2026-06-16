<div align="center">

# ✍️ Escriba

**Il traduttore universale verso il linguaggio dell’IA.**

Trasforma qualsiasi documento in Markdown pulito e anonimo — pronto per qualunque LLM ed esportabile in Word, XML e altro. Uno strumento auto‑ospitabile che risolve i grattacapi di dare in pasto documenti a un LLM: input rumoroso e avido di token → Markdown pulito, fuga di dati sensibili → anonimizzazione PII integrata con pseudonimizzazione reversibile, e un pannello di preparazione per LLM integrato che conta i token, stima il costo con prezzi in tempo reale, verifica l’adattamento alla finestra di contesto e suddivide in chunk per il RAG. In locale, in 7 lingue, basato su [Microsoft MarkItDown](https://github.com/microsoft/markitdown).

[![License: MIT](https://img.shields.io/badge/License-MIT-e07f5c.svg)](../../LICENSE)
[![Immagine Docker](https://img.shields.io/badge/image-ghcr.io%2Fdiegoparras%2Fescriba-2496ED?logo=docker&logoColor=white)](https://github.com/diegoparras/escriba/pkgs/container/escriba)
[![UI: 7 lingue](https://img.shields.io/badge/UI-7%20lingue-f0a98c.svg)](#-internazionalizzazione)
![Auto-ospitato](https://img.shields.io/badge/auto--ospitato-✓-30d158.svg)

<img src="../../assets/demo.gif" alt="Demo di Escriba" width="840">

📖 **Manuale completo (PDF):** [`docs/Escriba-Manual.it.pdf`](../Escriba-Manual.it.pdf)

[English](../../README.md) · [Español](README.es.md) · [Français](README.fr.md) · [Português](README.pt.md) · **Italiano** · [中文](README.zh.md) · [日本語](README.ja.md)

</div>

---

## ✨ Funzionalità

- 📄 **Documenti** — PDF, Word, Excel, PowerPoint, HTML, CSV, EPUB, ZIP e altro.
- 🖼️ **Immagini** — OCR automatico (Tesseract); descrizione tramite IA opzionale.
- 🎙️🎬 **Audio e video** — trascrizione locale e offline con Whisper (mp3, wav, mp4, mov, mkv…).
- 🔗 **URL e YouTube** — converte una pagina web o ottiene la trascrizione di un video YouTube.
- 🔍 **OCR intelligente** — il testo nelle immagini viene riconosciuto automaticamente; i PDF scansionati **e ruotati** vengono rilevati, elaborati con OCR e raddrizzati al volo.
- 📑 **Selezione delle pagine** — per i PDF lunghi, converti solo le pagine che ti servono: un intervallo (`5–67`), pagine singole (`1, 6, 9`) o un misto (`1, 2, 5‑67`). Si sceglie per ogni file con un semplice selettore che mostra il numero di pagine del documento — nessuna sintassi da ricordare.
- 🤖 **IA opzionale** — OpenAI, Google Gemini (AI Studio) o OpenRouter, con valore predefinito **«Senza IA»**. I modelli vengono elencati automaticamente.
- 🛡️ **Anonimizzazione PII per LLM** — motore di privacy locale completo: modello NER ([OpenAI Privacy Filter](https://github.com/openai/privacy-filter)) + campi delle fatture per layout + rilevatori validati (carta **Luhn**, **IBAN**) + le tue regole **RE2**. Cinque modalità di output: *tipizzata*, *anonima*, **pseudonimizzazione reversibile** («PERSONA_1» → invia all’LLM → re-idrata in locale), **mascheramento parziale** (••••-3456) e **hash stabile** (stesso dato → stesso pseudonimo tra documenti).
- ⬛ **Censura visiva** — scarica il PDF o l’immagine scansionata con i dati **oscurati sulla pagina**. Redazione reale: il testo e i pixel sottostanti vengono rimossi dal file, non coperti — e anche i **metadati** del documento (titolo, autore, parole chiave, XMP) vengono ripuliti, così nulla trapela nelle *Proprietà*.
- 📤 **Esportazione in 10 formati** — oltre al Markdown, un unico menu di download unificato esporta il risultato in **Word (.docx)**, ODT, EPUB, HTML, LaTeX, reStructuredText e **XML** strutturato (DocBook, JATS, TEI, OPML) — grazie a [Pandoc](https://pandoc.org/). Nessun LLM coinvolto.
- 🔊 **Da testo ad audio (podcast)** — trasforma il documento convertito in un **MP3**: una **narrazione** a voce singola o un **podcast a due conduttori** sceneggiato dall’IA. Voci locali [Piper](https://github.com/rhasspy/piper) (offline, 14 voci in es/en/pt/fr/it/de/zh) oppure voci cloud opzionali di **OpenAI**, con controlli di tono / velocità / volume.
- ✏️ **Editor Markdown integrato** — apri il risultato in un **editor a schermo intero con anteprima in tempo reale** per ripulirlo prima di esportarlo o convertirlo in voce. Le tue modifiche si propagano a ogni output (Word, XML, MP3…).
- 🧠 **Pannello di preparazione per LLM** — ogni conversione mostra un **conteggio dei token** (tiktoken), i **token e il costo risparmiati** dall’anonimizzazione, una **stima del costo per modello in tempo reale** (prezzi recuperati da [OpenRouter](https://openrouter.ai/)), l’**adattamento alla finestra di contesto** su centinaia di modelli, lo **chunking per RAG** con un clic e un **rilevatore di prompt injection**. Tutto in locale, senza chiamate all’IA.
- 🔬 **Estrazione PDF avanzata** — motore [OpenDataLoader](https://github.com/opendataloader-project/opendataloader-pdf) attivabile per layout complessi: migliore ordine di lettura (XY-Cut++) e gerarchia dei titoli, con fallback automatico all’estrattore predefinito.
- 🌍 **7 lingue dell’interfaccia** — English, Español, Français, Português, Italiano, 中文, 日本語 (rilevate automaticamente, modificabili).
- 👑😇👤 **Tre livelli di accesso** — DIOS / ANGEL / HUMANO, ognuno con la propria password e i propri limiti.
- 🔒 **Privato per progettazione** — i file caricati vengono eliminati subito dopo la conversione; nulla viene memorizzato.
- 🛡️ **Rinforzato** — anti‑SSRF, sanificazione XSS, limite di richieste per ruolo, container senza root, header di sicurezza.
- 🐳 **Un’unica immagine autosufficiente** — ffmpeg, OCR, Whisper e Redis inclusi. Nessun servizio aggiuntivo.

---

## 🚀 Avvio rapido

Scarica l’immagine già pronta ed eseguila con un solo comando:

```bash
docker run -d --name escriba --restart unless-stopped -p 8000:8000 \
  -e SECRET_KEY="$(openssl rand -hex 32)" \
  -e GOD_PASSWORD="cambiami" \
  ghcr.io/diegoparras/escriba:latest
```

Apri **http://localhost:8000** e accedi con la `GOD_PASSWORD` che hai impostato.

> L’immagine include tutto (ffmpeg, Tesseract OCR, Whisper, Redis integrato). Nessun servizio aggiuntivo necessario.

---

## 🛳️ Distribuzione

Scegli la tua piattaforma. Tutto funziona a partire dall’immagine qui sopra.

> Prima di iniziare, copia `.env.example` in `.env` e imposta i tuoi segreti
> (`SECRET_KEY`, `GOD_PASSWORD`, …). Genera chiavi con `openssl rand -hex 32`.

<details open>
<summary><b>EasyPanel</b></summary>

1. **Project → + Service → App**, poi in **Source → Docker Image** metti `ghcr.io/diegoparras/escriba:latest`.
2. Aggiungi le tue **variabili d’ambiente** (vedi [Configurazione](#-configurazione)).
3. In **Domains**, imposta **Container Port `8000`**, aggiungi il dominio e attiva HTTPS.
4. **Deploy.**
</details>

<details>
<summary><b>Docker Compose</b></summary>

```bash
git clone https://github.com/diegoparras/escriba.git
cd escriba
cp .env.example .env          # imposta i tuoi segreti
docker compose up -d --build
```
</details>

<details>
<summary><b>Portainer</b></summary>

**Stacks → Add stack → Repository** con
`https://github.com/diegoparras/escriba` e percorso compose `docker-compose.yml`
(oppure incolla il `docker-compose.yml` nell’editor web). Imposta le variabili
d’ambiente e distribuisci; l’app è in ascolto sulla porta `8000`.
</details>

<details>
<summary><b>Dokploy</b></summary>

**Create Application → GitHub** (repo `diegoparras/escriba`) con **Build Type:
Dockerfile**, aggiungi le variabili d’ambiente, imposta il dominio su **Container
Port `8000`** con HTTPS, e distribuisci.
</details>

<details>
<summary><b>Docker semplice / reverse proxy</b></summary>

```bash
docker build -t escriba .
docker run -d --name escriba --restart unless-stopped -p 8000:8000 \
  -e SECRET_KEY="$(openssl rand -hex 32)" -e GOD_PASSWORD="cambiami" escriba
```

Per il TLS, metti un reverse proxy davanti. Esempio di `Caddyfile` (HTTPS automatico):

```caddy
esempio.com {
    reverse_proxy localhost:8000
}
```

Con Nginx, inoltra a `localhost:8000` e aumenta `client_max_body_size` per i caricamenti grandi.
</details>

---

## ⚙️ Configurazione

Tutte le impostazioni sono variabili d’ambiente. Minimo consigliato:

```env
SECRET_KEY=<openssl rand -hex 32>   # obbligatoria in produzione (altrimenti le sessioni si reimpostano)
GOD_PASSWORD=<una password forte>
ANGEL_PASSWORD=<opzionale>
HUMAN_PASSWORD=<opzionale>
```

Se non viene impostata alcuna password, all’avvio viene generata una `GOD_PASSWORD`
casuale e stampata nei **log** del container.

| Variabile | Predefinito | Descrizione |
|---|---|---|
| `SECRET_KEY` | *(casuale)* | Chiave di firma delle sessioni. **Impostala** in produzione. |
| `GOD_PASSWORD` / `ANGEL_PASSWORD` / `HUMAN_PASSWORD` | — | Password di ciascun livello di accesso. |
| `HUMAN_OPEN` | `false` | Consente il livello HUMANO senza login (convertitore pubblico). |
| `WEB_CONCURRENCY` | `auto` | Worker paralleli. `auto` = numero di core CPU. |
| `MAX_UPLOAD_MB` | `100` | Limite assoluto di caricamento (eccetto DIOS). |
| `WHISPER_MODEL` | `base` | Modello di trascrizione: `tiny` · `base` · `small` · `medium` · `large-v3`. |
| `MAX_MEDIA_MINUTES` | `120` | Durata max audio/video da trascrivere (`0` = illimitato; DIOS senza limite). |
| `OPENAI_API_KEY` / `OPENROUTER_API_KEY` / `GOOGLE_API_KEY` | — | Chiavi IA lato server (usate se l’utente non fornisce la propria). Solo DIOS e ANGEL. |
| `API_TOKEN` / `API_TOKEN_ROLE` | — / `angel` | Token statico per l’automazione (n8n, script) e il ruolo associato. |
| `EMBEDDED_REDIS` | `true` | Redis integrato per il limite di richieste condiviso. `false` + `REDIS_URL` per uno esterno. |
| `ENABLE_DOCS` | `false` | Esporre Swagger su `/api/docs`. |
| `PORT` | `8000` | Porta del container. |

I limiti per livello (`*_MAX_MB`, `*_MAX_BATCH`, `*_RATE`) e i preset sono documentati in
[`.env.example`](../../.env.example).

**Prestazioni:** per impostazione predefinita l’app avvia un worker per core CPU, quindi si
adatta a qualsiasi host (VPS 1 core → 1 worker; server 24 thread → 24). Ogni worker usa
~250 MB di RAM; imposta `WEB_CONCURRENCY` a un numero fisso per limitarlo.

---

## 🔐 Ruoli e livelli di accesso

Il login è obbligatorio. Ogni livello ha la propria password e i propri limiti.

| Capacità | 👤 HUMANO | 😇 ANGEL | 👑 DIOS |
|---|:---:|:---:|:---:|
| Caricare e convertire file | ✓ | ✓ | ✓ |
| Convertire da un URL pubblico | — | ✓ (anti‑SSRF) | ✓ |
| URL interno / `file://` / percorso locale | — | — | ✓ |
| Audio / video / ZIP | — | ✓ | ✓ |
| Trascrizioni di YouTube | ✓ | ✓ | ✓ |
| OCR (forzato / automatico) | — | ✓ | ✓ |
| Usare le chiavi IA del server | — | ✓ | ✓ |
| Dimensione max file | 25 MB | 100 MB | illimitata |
| File per lotto | 3 | 10 | illimitati |
| Statistiche server (CPU/RAM) | — | parziale | completo |
| Limite richieste (req/min) | 15 | 60 | illimitato |

Tutti i limiti sono configurabili tramite variabili d’ambiente.

**Punti di sicurezza:** l’accesso ai file locali e l’SSRF sono riservati a DIOS;
il recupero degli URL blocca gli IP interni e i reindirizzamenti; i caricamenti sono limitati
in streaming; l’anteprima è sanificata con DOMPurify; vengono applicati CSP e header di sicurezza;
il container gira come utente non‑root con `no-new-privileges`; il limite di richieste è
condiviso tra i worker tramite il Redis integrato.

---

## 📤 Esportazione oltre il Markdown

Il Markdown pulito è il cuore del progetto, ma l’unico **menu «Formato…»** della scheda dei risultati lo trasforma in qualunque cosa serva al tuo flusso di lavoro — scegli un formato, poi premi **Scarica** (non si attiva mai da solo). Grazie a [Pandoc](https://pandoc.org/), senza alcun LLM coinvolto:

| Famiglia | Formati |
|---|---|
| Markdown | `.md`, compatto (spazi rimossi), chunk per RAG (`.jsonl`) |
| Office ed ebook | **Word `.docx`**, ODT, EPUB |
| Web e impaginazione | HTML, LaTeX, reStructuredText |
| XML strutturato | **DocBook**, **JATS**, **TEI**, **OPML** |
| Privacy | PDF censurato (PII oscurata — vedi sopra) |

## 🧠 Pannello di preparazione per LLM

Ogni conversione è accompagnata da un pannello compatto che prepara il testo per un modello — interamente in locale, con zero chiamate all’IA:

- **Conteggio dei token** con `tiktoken` (`o200k_base`, incluso nell’immagine — funziona offline).
- **Token e costo risparmiati** dall’anonimizzazione, così puoi vedere cosa ti fa guadagnare rimuovere le PII.
- **Stima del costo per modello in tempo reale** — prezzi e finestre di contesto recuperati da [OpenRouter](https://openrouter.ai/) (centinaia di modelli, in cache) così i numeri non sono mai obsoleti.
- **Adattamento alla finestra di contesto** — a colpo d’occhio, in quali modelli rientra il documento.
- **Chunking per RAG con un clic** — suddivide in chunk sovrapposti e limitati per token (`semchunk`), scaricabili come `.jsonl`.
- **Rilevatore di prompt injection** — segnala il testo che tenta di dirottare un LLM a valle.

---

## 🔌 API

Utile per l’automazione (n8n, script). Richiede autenticazione.

**Con un token API** (imposta `API_TOKEN`):

```bash
curl -H "X-API-Key: IL_TUO_TOKEN" \
     -F "file=@documento.pdf" \
     https://il-tuo-dominio/api/convert
# Forzare OCR / lingua:  -F "ocr=true"  -F "lang=it-IT"
```

**Con un cookie di sessione:**

```bash
curl -c cookies.txt -F "password=$GOD_PASSWORD" https://il-tuo-dominio/api/login
curl -b cookies.txt -F "file=@documento.pdf"    https://il-tuo-dominio/api/convert
```

`POST /api/convert` (multipart/form-data): `file` *o* `url`, più gli opzionali `lang`,
`ocr`, `llm_provider`, `llm_api_key`, `llm_model`. Risposta:

```json
{ "source": "…", "title": "…", "markdown": "…",
  "words": 1234, "chars": 5678, "elapsed_ms": 87,
  "pdf_type": "scansionato", "ocr_applied": true, "note": null }
```

`POST /api/redact` (multipart/form-data): `file` (PDF o immagine), opzionali `lang`, `anon_strict`, `anon_detectors`, `anon_rules`. Restituisce il **PDF censurato** (binario) con l’header `X-Redacted-Entities`.

Post‑elaborazione del Markdown (JSON in ingresso, JSON o file in uscita):

| Endpoint | Metodo | Descrizione |
|---|---|---|
| `/api/export` | POST | Converte il Markdown in un formato di destinazione (`docx`, `odt`, `epub`, `html`, `latex`, `rst`, `docbook`, `jats`, `tei`, `opml`). |
| `/api/compact` | POST | Markdown con spazi rimossi per risparmiare token. |
| `/api/chunk` | POST | Chunk per RAG limitati per token (restituisce `.jsonl`). |
| `/api/model_prices` | GET | Prezzi dei modelli e finestre di contesto in tempo reale (OpenRouter, in cache). |

---

## 🌍 Internazionalizzazione

L’interfaccia è disponibile in **7 lingue** — English, Español, Français, Português,
Italiano, 中文 e 日本語. La lingua viene rilevata automaticamente dal browser e può essere
cambiata in qualsiasi momento dal pannello ⚙️; la scelta viene ricordata per browser.

---

## 💻 Sviluppo locale

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

> OCR e trascrizione richiedono `ffmpeg`, `tesseract-ocr` e `ocrmypdf` installati nel
> sistema (l’immagine Docker li include già). Gli altri formati funzionano senza di essi.

---

## 📜 Crediti e licenza

**Escriba** — sviluppato da **Diego Parrás**
CeMIACE · SEUBES · FCE‑UBA (Facultad de Ciencias Económicas, Universidad de Buenos Aires).

Costruito su [Microsoft MarkItDown](https://github.com/microsoft/markitdown),
[FastAPI](https://fastapi.tiangolo.com/),
[Tesseract OCR](https://github.com/tesseract-ocr/tesseract),
[OCRmyPDF](https://github.com/ocrmypdf/OCRmyPDF) e
[faster‑whisper](https://github.com/SYSTRAN/faster-whisper).
Sotto [Licenza MIT](../../LICENSE).
