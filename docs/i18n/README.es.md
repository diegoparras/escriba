<div align="center">

# ✍️ Escriba

**El traductor universal al idioma de la IA.**

Convierte cualquier documento en Markdown limpio y anónimo — listo para cualquier LLM, y exportable a Word, XML y más. Una herramienta auto‑alojable que resuelve los dolores de cabeza de darle documentos a un LLM: entrada ruidosa y devoradora de tokens → Markdown limpio, fuga de datos sensibles → anonimización de PII integrada con seudonimización reversible, y un panel de preparación para LLMs integrado que cuenta tokens, estima el costo con precios en vivo, comprueba si entra en la ventana de contexto y trocea para RAG. Local, en 7 idiomas, construido sobre [Microsoft MarkItDown](https://github.com/microsoft/markitdown).

[![License: MIT](https://img.shields.io/badge/License-MIT-e07f5c.svg)](../../LICENSE)
[![Docker image](https://img.shields.io/badge/image-ghcr.io%2Fdiegoparras%2Fescriba-2496ED?logo=docker&logoColor=white)](https://github.com/diegoparras/escriba/pkgs/container/escriba)
[![UI: 7 idiomas](https://img.shields.io/badge/UI-7%20idiomas-f0a98c.svg)](#-internacionalización)
![Auto-alojable](https://img.shields.io/badge/auto--alojable-✓-30d158.svg)

<img src="../../assets/demo.gif" alt="Demostración de Escriba" width="840">

📖 **Manual completo (PDF):** [`docs/Escriba-Manual.es.pdf`](../Escriba-Manual.es.pdf)

[English](../../README.md) · **Español** · [Français](README.fr.md) · [Português](README.pt.md) · [Italiano](README.it.md) · [中文](README.zh.md) · [日本語](README.ja.md)

</div>

---

## ✨ Características

- 📄 **Documentos** — PDF, Word, Excel, PowerPoint, HTML, CSV, EPUB, ZIP y más.
- 🖼️ **Imágenes** — OCR automático (Tesseract); descripción por IA opcional.
- 🎙️🎬 **Audio y video** — transcripción local y sin conexión con Whisper (mp3, wav, mp4, mov, mkv…).
- 🔗 **URLs y YouTube** — convierte una página web u obtiene la transcripción de un video de YouTube.
- 🔍 **OCR inteligente** — el texto de las imágenes se reconoce automáticamente; los PDF escaneados **y rotados** se detectan, procesan con OCR y enderezan al vuelo.
- 📑 **Selección de páginas** — en PDF largos, convierte solo las páginas que necesitas: un rango (`5–67`), páginas sueltas (`1, 6, 9`) o una mezcla (`1, 2, 5‑67`). Se elige por archivo con un selector simple que muestra la cantidad de páginas del documento — sin sintaxis que recordar.
- 🤖 **IA opcional** — OpenAI, Google Gemini (AI Studio) u OpenRouter, con un valor por defecto de **«Sin IA»**. Los modelos se listan automáticamente.
- 🛡️ **Anonimización de PII para LLMs** — motor de privacidad local completo: modelo NER ([OpenAI Privacy Filter](https://github.com/openai/privacy-filter)) + campos de comprobantes por layout + detectores validados (tarjeta **Luhn**, **IBAN**) + tus propias reglas **RE2**. Cinco modos de salida: *tipado*, *anónimo*, **seudonimizado reversible** («PERSONA_1» → envíalo al LLM → re-hidrátalo localmente), **enmascarado parcial** (••••-3456) y **hash estable** (mismo dato → mismo seudónimo entre documentos).
- ⬛ **Censura visual** — descarga tu PDF o imagen escaneada con el PII **tachado sobre la página**. Redacción real: el texto y los píxeles de abajo se eliminan del archivo, no se tapan — y los **metadatos** del documento (título, autor, palabras clave, XMP) también se limpian, para que nada se filtre en *Propiedades*.
- 📤 **Exporta a 10 formatos** — más allá de Markdown, un único menú de descarga unificado exporta el resultado a **Word (.docx)**, ODT, EPUB, HTML, LaTeX, reStructuredText y **XML** estructurado (DocBook, JATS, TEI, OPML) — con [Pandoc](https://pandoc.org/). Sin IA de por medio.
- 🧠 **Panel de preparación para LLMs** — cada conversión muestra un **conteo de tokens** (tiktoken), los **tokens y el costo ahorrados** por la anonimización, una **estimación de costo en vivo por modelo** (precios obtenidos de [OpenRouter](https://openrouter.ai/)), si **entra en la ventana de contexto** de cientos de modelos, **troceado para RAG** con un clic y un **detector de inyección de prompts**. Todo local, sin llamadas a IA.
- 🔬 **Extracción avanzada de PDF** — motor opcional [OpenDataLoader](https://github.com/opendataloader-project/opendataloader-pdf) para layouts complejos: mejor orden de lectura (XY‑Cut++) y jerarquía de títulos, con repliegue automático al extractor por defecto.
- 🌍 **7 idiomas en la interfaz** — English, Español, Français, Português, Italiano, 中文, 日本語 (autodetectados y cambiables).
- 👑😇👤 **Tres niveles de acceso** — DIOS / ANGEL / HUMANO, cada uno con su contraseña y límites.
- 🔒 **Privado por diseño** — los archivos subidos se eliminan justo después de convertirse; no se almacena nada.
- 🛡️ **Endurecido** — anti‑SSRF, sanitización XSS, límite de peticiones por rol, contenedor sin root, cabeceras de seguridad.
- 🐳 **Una sola imagen autosuficiente** — ffmpeg, OCR, Whisper y Redis incluidos. No requiere servicios adicionales.

---

## 🚀 Inicio rápido

Descarga la imagen ya compilada y ejecútala con un solo comando:

```bash
docker run -d --name escriba --restart unless-stopped -p 8000:8000 \
  -e SECRET_KEY="$(openssl rand -hex 32)" \
  -e GOD_PASSWORD="cambia-esto" \
  ghcr.io/diegoparras/escriba:latest
```

Abre **http://localhost:8000** e inicia sesión con la `GOD_PASSWORD` que definiste.

> La imagen incluye todo (ffmpeg, Tesseract OCR, Whisper, Redis embebido). No se necesitan servicios adicionales.

---

## 🛳️ Despliegue

Elige la plataforma que uses. Todo se ejecuta desde la imagen anterior.

> Antes de empezar, copia `.env.example` a `.env` y define tus secretos
> (`SECRET_KEY`, `GOD_PASSWORD`, …). Genera claves con `openssl rand -hex 32`.

<details open>
<summary><b>EasyPanel</b></summary>

1. **Project → + Service → App**, y en **Source → Docker Image** pon `ghcr.io/diegoparras/escriba:latest`.
2. Agrega tus **variables de entorno** (ver [Configuración](#-configuración)).
3. En **Domains**, define **Container Port `8000`**, agrega tu dominio y activa HTTPS.
4. **Deploy.**
</details>

<details>
<summary><b>Docker Compose</b></summary>

```bash
git clone https://github.com/diegoparras/escriba.git
cd escriba
cp .env.example .env          # define tus secretos
docker compose up -d --build
```
</details>

<details>
<summary><b>Portainer</b></summary>

**Stacks → Add stack → Repository** con
`https://github.com/diegoparras/escriba` y la ruta de compose `docker-compose.yml`
(o pega el `docker-compose.yml` en el editor web). Define las variables de
entorno y despliega; la app escucha en el puerto `8000`.
</details>

<details>
<summary><b>Dokploy</b></summary>

**Create Application → GitHub** (repo `diegoparras/escriba`) con **Build Type:
Dockerfile**, agrega tus variables de entorno, define el dominio con **Container
Port `8000`** y HTTPS, y despliega.
</details>

<details>
<summary><b>Docker simple / proxy inverso</b></summary>

```bash
docker build -t escriba .
docker run -d --name escriba --restart unless-stopped -p 8000:8000 \
  -e SECRET_KEY="$(openssl rand -hex 32)" -e GOD_PASSWORD="cambia-esto" escriba
```

Para TLS, coloca un proxy inverso delante. Ejemplo de `Caddyfile` (HTTPS automático):

```caddy
ejemplo.com {
    reverse_proxy localhost:8000
}
```

Con Nginx, redirige a `localhost:8000` y sube `client_max_body_size` para subidas grandes.
</details>

---

## ⚙️ Configuración

Todos los ajustes son variables de entorno. Mínimo recomendado:

```env
SECRET_KEY=<openssl rand -hex 32>   # obligatorio en producción (si no, las sesiones se reinician)
GOD_PASSWORD=<una contraseña fuerte>
ANGEL_PASSWORD=<opcional>
HUMAN_PASSWORD=<opcional>
```

Si no se define ninguna contraseña, al arrancar se genera una `GOD_PASSWORD`
aleatoria y se imprime en los **logs** del contenedor.

| Variable | Por defecto | Descripción |
|---|---|---|
| `SECRET_KEY` | *(aleatoria)* | Clave de firma de sesiones. **Defínela** en producción. |
| `GOD_PASSWORD` / `ANGEL_PASSWORD` / `HUMAN_PASSWORD` | — | Contraseña de cada nivel de acceso. |
| `HUMAN_OPEN` | `false` | Permite el nivel HUMANO sin login (conversor público). |
| `WEB_CONCURRENCY` | `auto` | Workers en paralelo. `auto` = número de núcleos de CPU. |
| `MAX_UPLOAD_MB` | `100` | Límite absoluto de subida (excepto DIOS). |
| `WHISPER_MODEL` | `base` | Modelo de transcripción: `tiny` · `base` · `small` · `medium` · `large-v3`. |
| `MAX_MEDIA_MINUTES` | `120` | Duración máxima de audio/video a transcribir (`0` = sin límite; DIOS sin tope). |
| `OPENAI_API_KEY` / `OPENROUTER_API_KEY` / `GOOGLE_API_KEY` | — | Claves de IA del servidor (se usan si el usuario no aporta la suya). Solo para DIOS y ANGEL. |
| `API_TOKEN` / `API_TOKEN_ROLE` | — / `angel` | Token estático para automatización (n8n, scripts) y el rol al que se asigna. |
| `EMBEDDED_REDIS` | `true` | Redis embebido para el límite de peticiones compartido. Pon `false` + `REDIS_URL` para uno externo. |
| `ENABLE_DOCS` | `false` | Exponer Swagger en `/api/docs`. |
| `PORT` | `8000` | Puerto del contenedor. |

Los límites por nivel (`*_MAX_MB`, `*_MAX_BATCH`, `*_RATE`) y los presets están documentados en
[`.env.example`](../../.env.example).

**Rendimiento:** por defecto la app crea un worker por núcleo de CPU, así que se adapta a
cualquier servidor (VPS de 1 núcleo → 1 worker; servidor de 24 hilos → 24). Cada worker usa
~250 MB de RAM; define `WEB_CONCURRENCY` con un número fijo para limitarlo.

---

## 🔐 Roles y niveles de acceso

Es obligatorio iniciar sesión. Cada nivel tiene su propia contraseña y límites.

| Capacidad | 👤 HUMANO | 😇 ANGEL | 👑 DIOS |
|---|:---:|:---:|:---:|
| Subir y convertir archivos | ✓ | ✓ | ✓ |
| Convertir desde una URL pública | — | ✓ (anti‑SSRF) | ✓ |
| URL interna / `file://` / ruta local | — | — | ✓ |
| Audio / video / ZIP | — | ✓ | ✓ |
| Transcripciones de YouTube | ✓ | ✓ | ✓ |
| OCR (forzado / automático) | — | ✓ | ✓ |
| Usar las claves de IA del servidor | — | ✓ | ✓ |
| Tamaño máximo de archivo | 25 MB | 100 MB | sin límite |
| Archivos por lote | 3 | 10 | sin límite |
| Estadísticas del servidor (CPU/RAM) | — | parcial | completo |
| Límite de peticiones (req/min) | 15 | 60 | sin límite |

Todos los límites son configurables mediante variables de entorno.

**Aspectos de seguridad:** el acceso a archivos locales y el SSRF están restringidos a DIOS;
la descarga de URLs bloquea IPs internas y redirecciones; las subidas se limitan por streaming;
la vista previa se sanitiza con DOMPurify; se aplican CSP y cabeceras de seguridad; el
contenedor corre como usuario sin privilegios con `no-new-privileges`; el límite de peticiones
se comparte entre workers mediante el Redis embebido.

---

## 📤 Exportar más allá de Markdown

El Markdown limpio es el núcleo, pero el **menú único «Formato…»** de la tarjeta de resultado lo convierte en lo que tu flujo de trabajo necesite — elige un formato y luego pulsa **Descargar** (nunca se dispara solo). Con [Pandoc](https://pandoc.org/), sin IA de por medio:

| Familia | Formatos |
|---|---|
| Markdown | `.md`, compacto (sin espacios sobrantes), trozos para RAG (`.jsonl`) |
| Ofimática y ebook | **Word `.docx`**, ODT, EPUB |
| Web y composición | HTML, LaTeX, reStructuredText |
| XML estructurado | **DocBook**, **JATS**, **TEI**, **OPML** |
| Privacidad | PDF censurado (PII tachado — ver arriba) |

## 🧠 Panel de preparación para LLMs

Cada conversión viene con un panel compacto que deja el texto listo para un modelo — íntegramente en local, con cero llamadas a IA:

- **Conteo de tokens** con `tiktoken` (`o200k_base`, incluido en la imagen — funciona sin conexión).
- **Tokens y costo ahorrados** por la anonimización, para que veas qué te aporta quitar el PII.
- **Estimación de costo en vivo por modelo** — precios y ventanas de contexto obtenidos de [OpenRouter](https://openrouter.ai/) (cientos de modelos, en caché) para que los números nunca queden desactualizados.
- **Ajuste a la ventana de contexto** — de un vistazo, en qué modelos entra el documento.
- **Troceado para RAG con un clic** — divide en trozos solapados y acotados por tokens (`semchunk`), descargables como `.jsonl`.
- **Detector de inyección de prompts** — marca el texto que intenta secuestrar a un LLM posterior.

---

## 🔌 API

Útil para automatización (n8n, scripts). Requiere autenticación.

**Con un token de API** (define `API_TOKEN`):

```bash
curl -H "X-API-Key: TU_TOKEN" \
     -F "file=@documento.pdf" \
     https://tu-dominio/api/convert
# Forzar OCR / idioma:  -F "ocr=true"  -F "lang=es-ES"
```

**Con una cookie de sesión:**

```bash
curl -c cookies.txt -F "password=$GOD_PASSWORD" https://tu-dominio/api/login
curl -b cookies.txt -F "file=@documento.pdf"    https://tu-dominio/api/convert
```

`POST /api/convert` (multipart/form-data): `file` *o* `url`, más los opcionales `lang`,
`ocr`, `llm_provider`, `llm_api_key`, `llm_model`. Respuesta:

```json
{ "source": "…", "title": "…", "markdown": "…",
  "words": 1234, "chars": 5678, "elapsed_ms": 87,
  "pdf_type": "escaneado", "ocr_applied": true, "note": null }
```

`POST /api/redact` (multipart/form-data): `file` (PDF o imagen), opcionales `lang`, `anon_strict`, `anon_detectors`, `anon_rules`. Devuelve el **PDF censurado** (binario) con la cabecera `X-Redacted-Entities` (cantidad de datos tachados). Los **metadatos del PDF también se borran** (DocInfo + XMP), para que un archivo censurado no pueda filtrar el nombre/ID vía *Propiedades* o `exiftool`.

Posprocesamiento de Markdown (JSON de entrada, JSON o archivo de salida):

| Endpoint | Método | Descripción |
|---|---|---|
| `/api/export` | POST | Convierte Markdown a un formato de destino (`docx`, `odt`, `epub`, `html`, `latex`, `rst`, `docbook`, `jats`, `tei`, `opml`). |
| `/api/compact` | POST | Markdown sin espacios sobrantes para ahorrar tokens. |
| `/api/chunk` | POST | Trozos para RAG acotados por tokens (devuelve `.jsonl`). |
| `/api/model_prices` | GET | Precios y ventanas de contexto de modelos en vivo (OpenRouter, en caché). |

---

## 🌍 Internacionalización

La interfaz viene en **7 idiomas** — English, Español, Français, Português, Italiano,
中文 y 日本語. El idioma se autodetecta desde el navegador y puede cambiarse en cualquier
momento desde el panel ⚙️ de configuración; la elección se recuerda por navegador.

---

## 💻 Desarrollo local

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

> El OCR y la transcripción necesitan `ffmpeg`, `tesseract-ocr` y `ocrmypdf` instalados en el
> sistema (la imagen de Docker ya los incluye). El resto de formatos funciona sin ellos.

---

## 📜 Créditos y licencia

**Escriba** — desarrollado por **Diego Parrás**
CeMIACE · SEUBES · FCE‑UBA (Facultad de Ciencias Económicas, Universidad de Buenos Aires).

Construido sobre [Microsoft MarkItDown](https://github.com/microsoft/markitdown),
[FastAPI](https://fastapi.tiangolo.com/),
[Tesseract OCR](https://github.com/tesseract-ocr/tesseract),
[OCRmyPDF](https://github.com/ocrmypdf/OCRmyPDF) y
[faster‑whisper](https://github.com/SYSTRAN/faster-whisper).
Bajo la [Licencia MIT](../../LICENSE).
