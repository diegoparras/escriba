<div align="center">

# ✍️ Escriba

**Cualquier documento a Markdown limpio y anónimo — listo para LLMs.**

Una aplicación web auto‑alojable construida sobre [Microsoft MarkItDown](https://github.com/microsoft/markitdown).

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
- 🤖 **IA opcional** — OpenAI, Google Gemini (AI Studio) u OpenRouter, con un valor por defecto de **«Sin IA»**. Los modelos se listan automáticamente.
- 🕵️ **Anonimización de PII (opcional)** — detecta y enmascara datos personales (nombres, emails, DNI/CUIT/CBU…) de forma **local**, vía el servicio **Anonimal** ([OpenAI Privacy Filter](https://github.com/openai/privacy-filter)). Salida *tipada* (`<PRIVATE_PERSON>`) o *anónima* (`<<ANOM_DATA>>`).
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
