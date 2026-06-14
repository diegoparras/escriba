# NOTA (reproducibilidad): la base se referencia por tag, no por digest.
# Para builds 100% reproducibles, fijar por digest y actualizarlo conscientemente
# (Dependabot/renovate): FROM python:3.12-slim@sha256:<digest>
# Hoy se acepta el riesgo de un tag móvil a cambio de recibir parches de seguridad
# de la base automáticamente en cada rebuild.
FROM python:3.12-slim

# Versión (la inyecta el CI desde el tag de git).
ARG APP_VERSION=dev

# Dependencias del sistema:
# - ffmpeg: transcripción de audio (mp3/wav/m4a…)
# - libmagic1: detección de tipo de archivo
# - exiftool: metadatos de imágenes
# - ocrmypdf + tesseract (+ idiomas): OCR de PDFs escaneados e imágenes
#
# NOTA (reproducibilidad): los paquetes apt NO están pineados a versión exacta
# (paquete=versión). Se acepta el riesgo a cambio de recibir parches de seguridad
# del repo Debian en cada rebuild. Si se necesita un build determinístico, pinear
# las versiones críticas (ffmpeg, ocrmypdf, tesseract-ocr, pandoc,
# default-jre-headless) y/o fijar la base por digest (ver arriba).
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libmagic1 \
    libimage-exiftool-perl \
    ocrmypdf \
    tesseract-ocr \
    tesseract-ocr-spa \
    tesseract-ocr-por \
    tesseract-ocr-fra \
    tesseract-ocr-deu \
    tesseract-ocr-ita \
    redis-server \
    libgomp1 \
    pandoc \
    default-jre-headless \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instalación de dependencias Python (build-essential temporal para wheels).
COPY requirements.txt .
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
 && pip install --no-cache-dir -r requirements.txt \
 # markitdown[all] fija youtube-transcript-api~=1.0.0 (con bug); forzamos una versión nueva
 # que sí funciona. Usamos nuestro propio handler de YouTube, no el de markitdown.
 && pip install --no-cache-dir --no-deps -U "youtube-transcript-api>=1.2,<2" \
 # yt-dlp a la ÚLTIMA versión SIEMPRE: YouTube cambia muy seguido y un yt-dlp
 # viejo deja de bajar subtítulos. Esta capa se invalida en cada rebuild.
 && pip install --no-cache-dir -U yt-dlp \
 && apt-get purge -y build-essential && apt-get autoremove -y \
 && rm -rf /var/lib/apt/lists/*

# Pre-descarga del modelo Whisper "base" en una capa ESTABLE (solo depende de
# requirements). Con reintentos para tolerar 429 transitorios de HuggingFace.
ENV HF_HOME=/opt/models
RUN mkdir -p /opt/models && \
    n=0; until python -c "from faster_whisper import WhisperModel; WhisperModel('base', device='cpu', compute_type='int8')"; do \
      n=$((n+1)); if [ "$n" -ge 5 ]; then echo "Fallo la descarga del modelo Whisper"; exit 1; fi; \
      echo "Reintento $n de descarga del modelo..."; sleep 15; \
    done

# Horneamos el vocabulario BPE de tiktoken (Panel LLM) para que el conteo de
# tokens funcione OFFLINE, sin descargar nada en runtime.
ENV TIKTOKEN_CACHE_DIR=/opt/tiktoken
RUN mkdir -p /opt/tiktoken && \
    python -c "import tiktoken; tiktoken.get_encoding('o200k_base')"

COPY app ./app
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# --- Usuario NO-root (mitiga explotación de parsers — M3/M4) ---
RUN useradd -m -u 10001 appuser && chown -R appuser:appuser /app /opt/models /opt/tiktoken

# --- Configuración (todo overridable por variables de entorno) ---
ENV MAX_UPLOAD_MB=100 \
    WEB_CONCURRENCY=auto \
    HUMAN_OPEN=false \
    ENABLE_DOCS=false \
    EMBEDDED_REDIS=true \
    WHISPER_MODEL=base \
    MAX_MEDIA_MINUTES=120 \
    APP_VERSION=${APP_VERSION} \
    PORT=8000

USER appuser

EXPOSE 8000

# Healthcheck: EasyPanel/Docker reinician el contenedor si deja de responder.
HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health',timeout=4).status==200 else 1)"

ENTRYPOINT ["./entrypoint.sh"]
