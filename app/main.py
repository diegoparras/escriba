"""
MarkItDown Web — convierte cualquier archivo a Markdown desde el navegador.

Seguridad + roles:
- 3 roles (humano < angel < dios) con capacidades distintas (ver auth.py).
- Login por contraseña, sesión firmada con HMAC en cookie HttpOnly.
- Anti-SSRF y lectura de archivos locales restringida a DIOS (ver security.py).
- Errores genéricos al cliente (detalle solo en logs).
- Cabeceras de seguridad + CSP. La API key del LLM nunca se guarda.
"""

import asyncio
import logging
import os
import re
import subprocess
import tempfile
import time
import unicodedata
import uuid
from pathlib import Path
from types import SimpleNamespace
from typing import Optional
from urllib.parse import parse_qs, urlparse

import psutil
import requests
from fastapi import FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from markitdown import MarkItDown

from . import anon_rules as anon_rules_mod
from . import anonimal as anonimal_mod
from . import auth
from . import detectors as detectors_mod
from . import ocr as ocr_mod
from . import pdf_extract
from . import transcribe as tr_mod
from . import yt_transcript
from .security import SecurityError, assert_public_url, check_rate, ext_of, safe_fetch

IMAGE_EXTS = {"jpg", "jpeg", "png", "gif", "bmp", "tiff", "tif", "webp"}
AUDIO_EXTS = tr_mod.AUDIO_EXTS
VIDEO_EXTS = tr_mod.VIDEO_EXTS

# Si un PDF produce menos de estos caracteres de texto, lo tratamos como escaneado.
SCANNED_THRESHOLD = int(os.getenv("SCANNED_THRESHOLD", "30"))

# Tope de duración para audio/video a transcribir (minutos). 0 = sin límite. DIOS no tiene tope.
MAX_MEDIA_MINUTES = int(os.getenv("MAX_MEDIA_MINUTES", "120"))

# Versión (la inyecta el build desde el tag de git; "dev" en local).
APP_VERSION = os.getenv("APP_VERSION", "dev")

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("markitdown.web")

APP_DIR = Path(__file__).parent
STATIC_DIR = APP_DIR / "static"

# Tope absoluto de subida para todos (además del límite por rol).
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "100"))
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
ENABLE_DOCS = os.getenv("ENABLE_DOCS", "false").lower() in ("1", "true", "yes")

STATS = {"conversions": 0, "chars_out": 0, "errors": 0, "started": time.time()}

SUPPORTED_FORMATS = {
    "Documentos": ["pdf", "docx", "doc", "rtf", "odt", "epub"],
    "Hojas de cálculo": ["xlsx", "xls", "csv", "tsv"],
    "Presentaciones": ["pptx", "ppt"],
    "Web y texto": ["html", "htm", "xml", "json", "md", "txt"],
    "Imágenes (IA opcional)": ["jpg", "jpeg", "png", "gif", "bmp", "tiff", "webp"],
    "Audio (transcripción)": ["mp3", "wav", "m4a", "flac", "ogg", "aac", "opus"],
    "Video (transcripción)": ["mp4", "mov", "mkv", "webm", "avi", "m4v"],
    "Otros": ["zip", "msg", "ipynb"],
}

app = FastAPI(
    title="MarkItDown Web",
    docs_url="/api/docs" if ENABLE_DOCS else None,
    redoc_url=None,
    openapi_url="/api/openapi.json" if ENABLE_DOCS else None,
)


@app.on_event("startup")
async def _prime_cpu():
    psutil.cpu_percent(interval=None)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    resp.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    resp.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "img-src 'self' data: blob:; "
        "font-src 'self' data: https://cdn.jsdelivr.net; "
        "connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
    )
    return resp


def _require(request: Request) -> str:
    role = auth.identity(request)
    if not role:
        raise HTTPException(status_code=401, detail="Iniciá sesión para usar el conversor.")
    return role


def _client_ip(request: Request) -> str:
    # Detrás de un proxy (Traefik/EasyPanel) usamos el primer X-Forwarded-For.
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "?"


# Proveedores de IA con endpoint compatible OpenAI.
PROVIDER_BASES = {
    "openai": "https://api.openai.com/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
    "openrouter": "https://openrouter.ai/api/v1",
}
DEFAULT_MODELS = {"openai": "gpt-4o", "gemini": "gemini-1.5-flash", "openrouter": "openai/gpt-4o-mini"}

# Claves de IA configuradas en el SERVIDOR (opcional). Si el usuario no pega una,
# se usa la del servidor para ese proveedor. Nunca se exponen al cliente.
SERVER_KEYS = {
    "openai": os.getenv("OPENAI_API_KEY"),
    "openrouter": os.getenv("OPENROUTER_API_KEY"),
    "gemini": os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"),
}


def resolve_key_and_provider(provider, user_key, allow_server=True):
    """Usa la key del usuario; si no hay y el rol lo permite, cae a la del servidor."""
    provider = (provider or "auto").lower()
    if provider == "none":
        return None, "none"   # el usuario eligió NO usar IA (aunque haya key)
    if user_key:
        return user_key, provider
    if not allow_server:
        return None, provider
    if provider in SERVER_KEYS and SERVER_KEYS[provider]:
        return SERVER_KEYS[provider], provider
    if provider == "auto":
        for p in ("openai", "gemini", "openrouter"):
            if SERVER_KEYS.get(p):
                return SERVER_KEYS[p], p
    return None, provider


def detect_provider_from_key(key: Optional[str]) -> str:
    if not key:
        return "openai"
    if key.startswith("AIza"):          # claves de Google AI Studio (Gemini)
        return "gemini"
    if key.startswith("sk-or-"):        # OpenRouter
        return "openrouter"
    return "openai"


def resolve_provider(provider, base_url, key, allow_custom):
    """Devuelve (base_url, modelo_por_defecto) según el proveedor elegido o detectado."""
    provider = (provider or "auto").lower()
    if provider in PROVIDER_BASES:
        return PROVIDER_BASES[provider], DEFAULT_MODELS[provider]
    if provider in ("custom", "personalizado") and base_url and allow_custom:
        return base_url, None
    # auto / fallback
    if base_url and allow_custom:
        return base_url, None
    p = detect_provider_from_key(key)
    return PROVIDER_BASES[p], DEFAULT_MODELS[p]


def build_converter(caps: dict, llm_api_key, llm_model, llm_base_url, provider=None) -> MarkItDown:
    if llm_api_key and caps["llm"]:
        try:
            from openai import OpenAI
        except ImportError:
            raise HTTPException(status_code=500, detail="Servicio de IA no disponible.")
        base, default_model = resolve_provider(provider, llm_base_url, llm_api_key, caps["llm_custom_base"])
        if base and not caps["allow_internal"]:
            assert_public_url(base)  # anti-SSRF (los proveedores conocidos son públicos)
        client = OpenAI(api_key=llm_api_key, base_url=base)
        return MarkItDown(llm_client=client, llm_model=llm_model or default_model or "gpt-4o", enable_plugins=False)
    return MarkItDown(enable_plugins=False)


YT_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be", "music.youtube.com"}


def is_youtube(url: str) -> bool:
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        return False
    return host in YT_HOSTS


def youtube_id(url: str):
    p = urlparse(url)
    host = (p.hostname or "").lower()
    if host == "youtu.be":
        return (p.path.lstrip("/").split("/") or [None])[0] or None
    if "youtube" in host:
        qs = parse_qs(p.query)
        if qs.get("v"):
            return qs["v"][0]
        parts = [x for x in p.path.split("/") if x]
        for key in ("shorts", "embed", "v", "live"):
            if key in parts:
                i = parts.index(key)
                if i + 1 < len(parts):
                    return parts[i + 1]
    return None


def _yt_title(url: str):
    try:
        r = requests.get("https://www.youtube.com/oembed", params={"url": url, "format": "json"}, timeout=8)
        if r.ok:
            return r.json().get("title")
    except Exception:
        pass
    return None


def youtube_transcript_md(url: str, lang: Optional[str]) -> str:
    """Obtiene la transcripción de un video de YouTube en Markdown."""
    vid = youtube_id(url)
    if not vid:
        raise ValueError("No pude identificar el video de YouTube.")
    from youtube_transcript_api import YouTubeTranscriptApi
    langs = []
    if lang and lang != "auto":
        langs.append(lang.split("-")[0])
    langs += ["es", "en", "pt", "fr", "de", "it"]
    api = YouTubeTranscriptApi()
    fetched = api.fetch(vid, languages=langs)
    data = fetched.to_raw_data() if hasattr(fetched, "to_raw_data") else list(fetched)
    parts = []
    for s in data:
        t = s.get("text") if isinstance(s, dict) else getattr(s, "text", "")
        if t:
            parts.append(t)
    text = " ".join(parts).strip()
    if not text:
        raise ValueError("El video no tiene transcripción disponible.")
    title = _yt_title(url) or "Transcripción de YouTube"
    return f"# {title}\n\n[{url}]({url})\n\n{text}"


def _do_convert(md: MarkItDown, source, lang: Optional[str] = None):
    # PDFs locales: los extraemos con PyMuPDF (respeta /Rotate y contenido
    # girado). Cubre PDFs traídos por URL (ANGEL) y rutas locales (DIOS); pdfminer
    # los devolvía al revés en hojas apaisadas.
    if isinstance(source, str) and source.lower().endswith(".pdf") and os.path.isfile(source):
        text = pdf_extract.extract_pdf_text(source)
        return SimpleNamespace(text_content=text, title=pdf_extract.pdf_title(source))
    # lang se usa para la transcripción de audio si el conversor lo soporta.
    if lang and lang != "auto":
        try:
            return md.convert(source, language=lang)
        except Exception:
            pass  # si no lo soporta, convertimos normal
    return md.convert(source)


# --- Auth endpoints ----------------------------------------------------------
def _caps_payload(role: str) -> dict:
    d = auth.public_caps(role)
    allowed = auth.caps_for(role).get("server_keys", False)
    d["serverProviders"] = [p for p, k in SERVER_KEYS.items() if k] if allowed else []
    d["version"] = APP_VERSION
    d["anonimal"] = anonimal_mod.available()   # ¿está habilitada la anonimización de PII?
    if d["anonimal"]:
        d["detectors"] = detectors_mod.catalog()   # catálogo para los checkboxes de la UI
    return d


@app.post("/api/login")
async def login(request: Request, password: str = Form(...)):
    role = auth.role_for_password(password)
    if not role:
        await asyncio.sleep(0.5)  # pequeño retardo anti fuerza bruta
        raise HTTPException(status_code=401, detail="Contraseña incorrecta.")
    token = auth.make_token(role)
    resp = JSONResponse(_caps_payload(role))
    secure = request.url.scheme == "https" or os.getenv("COOKIE_SECURE", "").lower() in ("1", "true")
    resp.set_cookie(
        auth.COOKIE_NAME, token, max_age=auth.SESSION_TTL,
        httponly=True, samesite="lax", secure=secure, path="/",
    )
    log.info("Login OK rol=%s ip=%s", role, _client_ip(request))
    return resp


@app.post("/api/logout")
async def logout():
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(auth.COOKIE_NAME, path="/")
    return resp


@app.get("/api/me")
async def me(request: Request):
    role = auth.identity(request)
    if not role:
        return JSONResponse({"authenticated": False, "humanOpen": auth.HUMAN_OPEN}, status_code=200)
    return {"authenticated": True, **_caps_payload(role)}


# --- Info endpoints ----------------------------------------------------------
@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/formats")
def formats(request: Request):
    _require(request)
    return {"formats": SUPPORTED_FORMATS}


@app.get("/api/stats")
def stats(request: Request):
    role = _require(request)
    level = auth.caps_for(role)["stats"]
    if level == "none":
        raise HTTPException(status_code=403, detail="Tu rol no tiene acceso a las estadísticas.")
    base = {
        "conversions": STATS["conversions"],
        "errors": STATS["errors"],
        "uptime_s": int(time.time() - STATS["started"]),
    }
    if level == "full":
        vm = psutil.virtual_memory()
        base.update({
            "cpu_percent": psutil.cpu_percent(interval=None),
            "cores": psutil.cpu_count(logical=True),
            "ram_used_gb": round(vm.used / 1024**3, 1),
            "ram_total_gb": round(vm.total / 1024**3, 1),
            "ram_percent": vm.percent,
            "chars_out": STATS["chars_out"],
            "workers": int(os.getenv("WEB_CONCURRENCY", "1")),
        })
    return base


# --- Conversión --------------------------------------------------------------
async def _read_capped(file: UploadFile, max_bytes: int) -> bytes:
    """Lee en bloques abortando si supera el tope (evita OOM — A3)."""
    total = 0
    chunks = []
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if max_bytes and total > max_bytes:
            raise HTTPException(status_code=413, detail=f"El archivo supera el límite de {max_bytes // (1024*1024)} MB.")
        chunks.append(chunk)
    return b"".join(chunks)


@app.post("/api/models")
async def list_models(
    request: Request,
    llm_api_key: Optional[str] = Form(default=None),
    llm_provider: Optional[str] = Form(default=None),
    llm_base_url: Optional[str] = Form(default=None),
):
    """Trae los modelos disponibles del proveedor (OpenAI, Gemini, OpenRouter…)."""
    role = _require(request)
    caps = auth.caps_for(role)
    eff_key, eff_provider = resolve_key_and_provider(llm_provider, llm_api_key, caps["server_keys"])
    if not eff_key:
        raise HTTPException(status_code=400, detail="Falta una API key (ni del usuario ni del servidor).")
    base, _ = resolve_provider(eff_provider, llm_base_url, eff_key, caps["llm_custom_base"])
    try:
        if not caps["allow_internal"]:
            assert_public_url(base)
    except SecurityError as e:
        raise HTTPException(status_code=400, detail=str(e))

    def _fetch():
        # allow_redirects=False: evita SSRF por redirección a una IP interna
        # cuando el rol usa una Base URL personalizada.
        r = requests.get(
            base.rstrip("/") + "/models",
            headers={"Authorization": f"Bearer {eff_key}"},
            timeout=15,
            allow_redirects=False,
        )
        r.raise_for_status()
        return r.json()

    try:
        j = await asyncio.to_thread(_fetch)
        items = j.get("data") or j.get("models") or []
        ids = sorted({(m.get("id") or m.get("name") or "").split("/")[-1] for m in items if (m.get("id") or m.get("name"))})
        if not ids:
            raise ValueError("vacío")
        return {"models": ids}
    except Exception:
        raise HTTPException(status_code=400, detail="No se pudieron obtener los modelos. Revisá la API key o el proveedor.")


@app.post("/api/convert")
async def convert(
    request: Request,
    file: Optional[UploadFile] = File(default=None),
    url: Optional[str] = Form(default=None),
    llm_api_key: Optional[str] = Form(default=None),
    llm_model: Optional[str] = Form(default=None),
    llm_base_url: Optional[str] = Form(default=None),
    llm_provider: Optional[str] = Form(default=None),
    lang: Optional[str] = Form(default=None),
    ocr: Optional[str] = Form(default=None),
    yt_cookies: Optional[str] = Form(default=None),
    anonymize: Optional[str] = Form(default=None),
    anon_strict: Optional[str] = Form(default=None),
    anon_rules: Optional[str] = Form(default=None),
    anon_detectors: Optional[str] = Form(default=None),
):
    role = _require(request)
    caps = auth.caps_for(role)
    use_ocr = str(ocr).lower() in ("1", "true", "yes", "on")
    if use_ocr and not caps["ocr"]:
        raise HTTPException(status_code=403, detail="Tu rol no puede usar OCR.")

    try:
        check_rate(role, _client_ip(request), caps["rate_per_min"])
    except SecurityError as e:
        raise HTTPException(status_code=429, detail=str(e))

    if not file and not url:
        raise HTTPException(status_code=400, detail="Subí un archivo o pasá una URL.")

    # Límite efectivo de tamaño (0 = sin límite).
    role_max = caps["max_file_mb"] * 1024 * 1024  # 0 = sin límite para el rol
    if caps["allow_internal"]:
        # DIOS: solo lo limita su propio rol (puede ser ilimitado), ignora el tope global.
        eff_max = role_max
    else:
        # Otros: el menor de (tope global, tope del rol), ignorando los que sean 0.
        candidates = [v for v in (MAX_UPLOAD_BYTES, role_max) if v]
        eff_max = min(candidates) if candidates else 0

    eff_key, eff_provider = resolve_key_and_provider(llm_provider, llm_api_key, caps["server_keys"])
    try:
        md = build_converter(caps, eff_key, llm_model, llm_base_url, eff_provider)
    except SecurityError as e:
        raise HTTPException(status_code=400, detail=str(e))
    t0 = time.time()
    tmp_path = None
    ocr_out = None
    out_md = ""
    title = None
    pdf_type = None
    ocr_applied = False
    note = None
    invoice_pii = []   # campos PII de un comprobante (layout); se calcula con el PDF a mano
    want_anon = (anonymize or "").strip().lower() in ("typed", "anon")

    try:
        if url:
            url = url.strip()
            yt = is_youtube(url)
            # YouTube se permite a TODOS los roles (transcripción, sin SSRF).
            if not caps["convert_url"] and not yt:
                raise HTTPException(status_code=403, detail="Tu rol no puede convertir desde URLs (pero sí links de YouTube).")
            if yt:
                # YouTube → yt-dlp (principal) + youtube-transcript-api (fallback).
                try:
                    out_md = await asyncio.to_thread(
                        yt_transcript.youtube_markdown, url, lang, yt_cookies)
                except HTTPException:
                    raise
                except Exception as exc:  # noqa: BLE001
                    log.warning("YouTube transcript falló: %s", exc)
                    raise HTTPException(
                        status_code=422,
                        detail="No se pudo obtener la transcripción. El video puede no tener subtítulos, "
                               "o YouTube bloqueó el pedido desde el servidor. Probá pegar tus cookies de "
                               "YouTube en ⚙ Configuración → Cookies de YouTube.",
                    )
            elif caps["allow_internal"]:
                # DIOS → poder total (incluye rutas locales / file:// / red interna).
                result = await asyncio.to_thread(_do_convert, md, url, lang)
                out_md = result.text_content or ""
                title = getattr(result, "title", None)
            else:
                # ANGEL: solo http/https público, descarga segura anti-SSRF.
                try:
                    data = await asyncio.to_thread(safe_fetch, url, eff_max)
                except SecurityError as e:
                    raise HTTPException(status_code=400, detail=str(e))
                suffix = Path(urlsplit_path(url)).suffix
                tmp_path = _write_temp(data, suffix)
                result = await asyncio.to_thread(_do_convert, md, tmp_path, lang)
                out_md = result.text_content or ""
                title = getattr(result, "title", None)
            source_name = url
        else:
            ext = ext_of(file.filename)
            is_media = ext in AUDIO_EXTS or ext in VIDEO_EXTS
            if not caps["audio_zip"] and (is_media or ext == "zip"):
                raise HTTPException(status_code=415, detail="Tu rol no puede convertir audio, video ni archivos comprimidos.")
            data = await _read_capped(file, eff_max)
            tmp_path = _write_temp(data, Path(file.filename or "").suffix)
            tess = ocr_mod.resolve_tess_langs(lang)
            if is_media:
                # Tope de duración (salvo DIOS). 0 = sin límite.
                if not caps["allow_internal"] and MAX_MEDIA_MINUTES:
                    dur = await asyncio.to_thread(tr_mod.probe_duration, tmp_path)
                    if dur and dur > MAX_MEDIA_MINUTES * 60:
                        raise HTTPException(
                            status_code=413,
                            detail=f"El audio/video dura {int(dur//60)} min y supera el límite de {MAX_MEDIA_MINUTES} min.",
                        )
                # Audio/Video → transcripción con Whisper (usa el idioma elegido).
                text, detected = await asyncio.to_thread(tr_mod.transcribe_media, tmp_path, lang)
                out_md = f"# Transcripción\n\n{text}" if text else ""
                title = f"Transcripción ({detected})" if detected else "Transcripción"
                if not text:
                    note = "No se detectó voz en el archivo."
            elif use_ocr and ext == "pdf":
                ocr_out = await asyncio.to_thread(ocr_mod.ocr_pdf, tmp_path, tess)
                # Extraemos con PyMuPDF (respeta rotación) en vez de pdfminer.
                out_md = await asyncio.to_thread(pdf_extract.extract_pdf_text, ocr_out)
                pdf_type, ocr_applied = "escaneado (OCR forzado)", True
            elif ext in IMAGE_EXTS and (use_ocr or (caps["ocr"] and not eff_key)):
                # OCR de imagen: forzado, o automático cuando no hay IA (key) en juego.
                out_md = await asyncio.to_thread(ocr_mod.ocr_image, tmp_path, tess)
                ocr_applied = True
            elif ext == "pdf":
                # PDF: extraemos con PyMuPDF (respeta /Rotate y contenido girado;
                # pdfminer devolvía las hojas apaisadas al revés).
                out_md = await asyncio.to_thread(pdf_extract.extract_pdf_text, tmp_path)
                title = pdf_extract.pdf_title(tmp_path)
                # Si se va a anonimizar y es un comprobante, capturamos los campos
                # PII por layout (etiqueta→valor) AHORA, con el PDF todavía en disco.
                if want_anon and pdf_extract.is_invoice(out_md):
                    invoice_pii = await asyncio.to_thread(pdf_extract.invoice_field_values, tmp_path)
                # Detección automática: si casi no hay texto, es escaneado.
                if len(out_md.strip()) < SCANNED_THRESHOLD:
                    pdf_type = "escaneado"
                    if caps["ocr"]:
                        # Auto-OCR: lo aplicamos solo, sin que el usuario tilde nada.
                        ocr_out = await asyncio.to_thread(ocr_mod.ocr_pdf, tmp_path, tess)
                        out_md = await asyncio.to_thread(pdf_extract.extract_pdf_text, ocr_out)
                        ocr_applied = True
                    else:
                        note = "Este PDF parece escaneado. Pedí a un nivel con OCR que lo procese."
                else:
                    pdf_type = "electrónico"
            else:
                result = await asyncio.to_thread(_do_convert, md, tmp_path, lang)
                out_md = result.text_content or ""
                title = getattr(result, "title", None)
            source_name = file.filename
    except HTTPException:
        STATS["errors"] += 1
        raise
    except subprocess.TimeoutExpired:
        STATS["errors"] += 1
        raise HTTPException(status_code=504, detail="El OCR tardó demasiado y se canceló.")
    except Exception as exc:  # noqa: BLE001
        STATS["errors"] += 1
        err_id = uuid.uuid4().hex[:8]
        log.exception("Conversión falló [%s] rol=%s", err_id, role)
        raise HTTPException(status_code=422, detail=f"No se pudo convertir el archivo (ref {err_id}).") from exc
    finally:
        for p in (tmp_path, ocr_out):
            if p:
                try:
                    os.unlink(p)
                except OSError:
                    pass

    # Normalización Unicode NFC: recombina acentos descompuestos (mejora "á é í").
    markdown = unicodedata.normalize("NFC", out_md or "")

    # Anonimización de PII (opcional) vía el microservicio Anonimal.
    #   "typed" → placeholders por categoría (<PRIVATE_PERSON>…)
    #   "anon"  → un único placeholder <<ANOM_DATA>>
    anon_mode = (anonymize or "").strip().lower()
    anon_is_strict = str(anon_strict).lower() in ("1", "true", "yes", "on", "estricto", "strict")
    anonymized = None
    pii_count = None
    pseudo_map = {}
    if anon_mode in ("typed", "anon", "seudo") and markdown.strip():
        if not anonimal_mod.available():
            raise HTTPException(status_code=400, detail="La anonimización no está disponible en este servidor.")
        try:
            user_rules = anon_rules_mod.parse_rules(anon_rules)   # reglas del usuario (RE2)
        except anon_rules_mod.AnonRulesError as e:
            raise HTTPException(status_code=400, detail="Reglas de anonimización inválidas: %s" % e)
        # Detectores built-in activos (None = defaults; "" = ninguno).
        det_ids = None if anon_detectors is None else [x.strip() for x in anon_detectors.split(",") if x.strip()]
        try:
            markdown, pii_count, pseudo_map = await asyncio.to_thread(
                anonimal_mod.anonymize, markdown, anon_mode, anon_is_strict, invoice_pii, user_rules, det_ids)
            anonymized = anon_mode
        except anonimal_mod.AnonimalError as e:
            # Falla SEGURA: no devolvemos el texto sin anonimizar (sería fuga de PII).
            STATS["errors"] += 1
            raise HTTPException(status_code=503, detail=str(e))
        # Scrub de metadata: el título del PDF puede contener un nombre.
        title = None
        # Aviso si el nombre del archivo contiene un CUIT/CUIL/DNI.
        if source_name and re.search(r"\b\d{8,11}\b", source_name):
            note = (note + " · " if note else "") + \
                "⚠️ El nombre del archivo contiene un número tipo CUIT/DNI; renombralo antes de compartir."

    STATS["conversions"] += 1
    STATS["chars_out"] += len(markdown)
    return JSONResponse({
        "source": source_name,
        "title": title,
        "markdown": markdown,
        "chars": len(markdown),
        "words": len(markdown.split()),
        "elapsed_ms": int((time.time() - t0) * 1000),
        "pdf_type": pdf_type,
        "ocr_applied": ocr_applied,
        "anonymized": anonymized,
        "pii_count": pii_count,
        "pseudonym_map": pseudo_map,   # token→original (solo modo seudo) para re-hidratar
        "note": note,
    })


@app.post("/api/anon_rules/validate")
async def validate_anon_rules(request: Request, anon_rules: Optional[str] = Form(default=None)):
    """Valida (con RE2) las reglas personalizadas del usuario. Para feedback en la UI."""
    _require(request)
    try:
        r = anon_rules_mod.parse_rules(anon_rules)
    except anon_rules_mod.AnonRulesError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not r:
        return {"ok": True, "empty": True, "patterns": 0, "labels": 0, "keep": 0}
    return {"ok": True, "patterns": len(r["patterns"]), "labels": len(r["labels"]), "keep": len(r["keep"])}


def _write_temp(data: bytes, suffix: str) -> str:
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix or "") as tmp:
        tmp.write(data)
        return tmp.name


def urlsplit_path(url: str) -> str:
    from urllib.parse import urlparse
    return urlparse(url).path or "x"


@app.get("/", response_class=HTMLResponse)
def index():
    # Inyecta la versión en las URLs de los assets (?v=) para invalidar la caché
    # del navegador en cada deploy: así nadie necesita hard refresh para ver el
    # JS/CSS nuevo.
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    return html.replace("__VER__", APP_VERSION)


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
