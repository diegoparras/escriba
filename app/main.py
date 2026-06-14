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
import json
import logging
import os
import re
import subprocess
import tempfile
import time
import unicodedata
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Optional
from urllib.parse import urlparse

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
from . import export as export_mod
from . import llmprep as llmprep_mod
from . import ocr as ocr_mod
from . import odl as odl_mod
from . import pricing as pricing_mod
from . import pdf_extract
from . import redact as redact_mod
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
# Se inyecta crudo en el HTML (reemplazo de __VER__), así que validamos el
# formato (alfanumérico + .-_) para no permitir inyección si el tag viniera sucio.
APP_VERSION = os.getenv("APP_VERSION", "dev")
if not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", APP_VERSION or ""):
    log = logging.getLogger("markitdown.web")
    log.warning("APP_VERSION con formato inesperado (%r); usando 'dev'.", APP_VERSION)
    APP_VERSION = "dev"

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("markitdown.web")

APP_DIR = Path(__file__).parent
STATIC_DIR = APP_DIR / "static"

# Tope absoluto de subida para todos (además del límite por rol).
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "100"))
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
ENABLE_DOCS = os.getenv("ENABLE_DOCS", "false").lower() in ("1", "true", "yes")

# Tope de tamaño para el texto que reciben export/compact/chunk (post-conversión).
# Evita DoS por payloads enormes en esos endpoints (mismo espíritu que MAX_UPLOAD).
MAX_TEXT_BYTES = int(os.getenv("MAX_TEXT_MB", "25")) * 1024 * 1024

# Proxies de confianza: solo si el peer (request.client.host) está en esta lista
# honramos X-Forwarded-For / X-Forwarded-Proto. Coma-separada (IPs de Traefik/
# EasyPanel). Vacío = nunca confiar en headers de proxy (default seguro).
TRUSTED_PROXIES = {
    p.strip() for p in os.getenv("TRUSTED_PROXIES", "").split(",") if p.strip()
}

# Cookie de sesión Secure: por defecto se decide por esquema/proxy de confianza,
# pero COOKIE_SECURE permite forzarlo (true/false) — p.ej. false para dev en http.
_COOKIE_SECURE_ENV = os.getenv("COOKIE_SECURE", "").strip().lower()

# NOTA: STATS es estado POR PROCESO (por worker). Con WEB_CONCURRENCY>1 cada
# worker tiene su propio contador; /api/stats refleja solo el worker que atendió
# el request. Para agregados globales habría que mover esto a Redis (INCR).
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

# Extensiones conocidas (en minúscula, con punto) para sanear el suffix del temp.
KNOWN_SUFFIXES = {"." + e for exts in SUPPORTED_FORMATS.values() for e in exts}


def _safe_suffix(name: str) -> str:
    """Suffix saneado para el archivo temporal: solo si la extensión está en el
    set conocido (evita que la URL/nombre del atacante controle el suffix).
    Si no la reconocemos, devolvemos '' (NamedTemporaryFile sin sufijo)."""
    suffix = Path(name or "").suffix.lower()
    return suffix if suffix in KNOWN_SUFFIXES else ""

# Capacidades estáticas del servidor (disponibilidad de Pandoc/ODL y catálogo de
# export). Son inmutables tras el arranque: las calculamos una sola vez en el
# lifespan para no correr sondas bloqueantes en cada login()/me() (endpoints async).
_CAPS_STATIC: dict = {}


def _compute_caps_static() -> dict:
    has_export = export_mod.available()
    return {
        "anonimal": anonimal_mod.available(),
        "detectors": detectors_mod.catalog() if anonimal_mod.available() else None,
        "export": export_mod.catalog() if has_export else [],
        "advancedExtract": odl_mod.available(),
    }


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    # Primer muestreo de CPU (cpu_percent(interval=None) necesita una llamada
    # previa para tener una línea base) y cálculo único de capacidades estáticas.
    psutil.cpu_percent(interval=None)
    _CAPS_STATIC.update(await asyncio.to_thread(_compute_caps_static))
    yield


app = FastAPI(
    title="MarkItDown Web",
    docs_url="/api/docs" if ENABLE_DOCS else None,
    redoc_url=None,
    openapi_url="/api/openapi.json" if ENABLE_DOCS else None,
    lifespan=_lifespan,
)


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
        "connect-src 'self'; object-src 'none'; base-uri 'none'; "
        "frame-ancestors 'none'; frame-src 'none'; form-action 'self'"
    )
    return resp


def _require(request: Request) -> str:
    role = auth.identity(request)
    if not role:
        raise HTTPException(status_code=401, detail="Iniciá sesión para usar el conversor.")
    return role


def _require_text_endpoint(request: Request, text: Optional[str]) -> str:
    """Guard común para export/compact/chunk: auth + rate-limit + tope de tamaño.
    Reusa las mismas utilidades que /api/convert (_require/check_rate y un tope de
    bytes), para no dejar estos endpoints sin protección contra DoS."""
    role = _require(request)
    caps = auth.caps_for(role)
    try:
        check_rate(role, _client_ip(request), caps["rate_per_min"])
    except SecurityError as e:
        raise HTTPException(status_code=429, detail=str(e))
    if MAX_TEXT_BYTES and len((text or "").encode("utf-8")) > MAX_TEXT_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"El texto supera el límite de {MAX_TEXT_BYTES // (1024*1024)} MB.",
        )
    return role


def _peer_ip(request: Request) -> Optional[str]:
    return request.client.host if request.client else None


def _from_trusted_proxy(request: Request) -> bool:
    """¿El peer directo es un proxy de confianza? Solo entonces honramos los
    headers X-Forwarded-* (si no, un cliente podría spoofearlos)."""
    peer = _peer_ip(request)
    return bool(peer and peer in TRUSTED_PROXIES)


def _client_ip(request: Request) -> str:
    # Solo confiamos en X-Forwarded-For si el peer directo es un proxy conocido
    # (TRUSTED_PROXIES). Si no, usamos el IP real del peer para evitar que un
    # cliente falsee su IP y burle el rate-limit.
    if _from_trusted_proxy(request):
        xff = request.headers.get("x-forwarded-for")
        if xff:
            return xff.split(",")[0].strip()
    return _peer_ip(request) or "?"


def _request_is_https(request: Request) -> bool:
    """¿El request llegó por HTTPS? Honra X-Forwarded-Proto SOLO si viene de un
    proxy de confianza (TLS terminado en el proxy); si no, mira el esquema real."""
    if _from_trusted_proxy(request):
        proto = (request.headers.get("x-forwarded-proto") or "").split(",")[0].strip().lower()
        if proto:
            return proto == "https"
    return request.url.scheme == "https"


def _cookie_secure(request: Request) -> bool:
    """Decide el flag Secure de la cookie de sesión.
    - COOKIE_SECURE=true/false fuerza el valor (escape para dev local en http).
    - Si no se fija, default seguro: Secure cuando el request es HTTPS (incluido
      el caso de TLS terminado en un proxy de confianza vía X-Forwarded-Proto)."""
    if _COOKIE_SECURE_ENV in ("1", "true", "yes"):
        return True
    if _COOKIE_SECURE_ENV in ("0", "false", "no"):
        return False
    return _request_is_https(request)


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
        return PROVIDER_BASES[provider], DEFAULT_MODELS.get(provider)
    if provider in ("custom", "personalizado") and base_url and allow_custom:
        return base_url, None
    # auto / fallback
    if base_url and allow_custom:
        return base_url, None
    p = detect_provider_from_key(key)
    return PROVIDER_BASES[p], DEFAULT_MODELS.get(p)


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
    # Capacidades estáticas (sondas calculadas una vez en el lifespan; fallback a
    # cálculo perezoso si por algún motivo el lifespan aún no corrió, p.ej. tests).
    caps_static = _CAPS_STATIC or _compute_caps_static()
    d["anonimal"] = caps_static["anonimal"]   # ¿está habilitada la anonimización de PII?
    if d["anonimal"] and caps_static["detectors"] is not None:
        d["detectors"] = caps_static["detectors"]   # catálogo para los checkboxes de la UI
    d["export"] = caps_static["export"]   # formatos de salida (Pandoc)
    d["advancedExtract"] = caps_static["advancedExtract"]   # extracción avanzada de PDF (ODL)
    return d


@app.post("/api/login")
async def login(request: Request, password: str = Form(...)):
    role = auth.role_for_password(password)
    if not role:
        await asyncio.sleep(0.5)  # pequeño retardo anti fuerza bruta
        raise HTTPException(status_code=401, detail="Contraseña incorrecta.")
    token = auth.make_token(role)
    resp = JSONResponse(_caps_payload(role))
    secure = _cookie_secure(request)
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
def _effective_max(caps: dict) -> int:
    """Tope de tamaño efectivo (bytes) para un rol. 0 = sin límite.
    DIOS (allow_internal) solo está limitado por su propio rol; el resto toma el
    menor entre el tope global y el del rol, ignorando los que sean 0 (ilimitado)."""
    role_max = caps["max_file_mb"] * 1024 * 1024
    if caps["allow_internal"]:
        return role_max
    candidates = [v for v in (MAX_UPLOAD_BYTES, role_max) if v]
    return min(candidates) if candidates else 0


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
    advanced: Optional[str] = Form(default=None),
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
    eff_max = _effective_max(caps)

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
    source_name = None
    file_basename = file.filename if file else None   # nombre ORIGINAL (para aviso PII)
    invoice_pii = []   # campos PII de un comprobante (layout); se calcula con el PDF a mano
    want_anon = (anonymize or "").strip().lower() in anonimal_mod.MODES

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
                # Suffix saneado a partir del path de la URL; si la URL no trae
                # extensión reconocible pero el contenido empieza con %PDF, lo
                # tratamos como PDF (si no, _do_convert no detectaría el tipo).
                suffix = _safe_suffix(urlsplit_path(url))
                if not suffix and data[:5] == b"%PDF-":
                    suffix = ".pdf"
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
            tmp_path = _write_temp(data, _safe_suffix(file.filename or ""))
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
                    note = "noVoice"   # clave i18n (note.noVoice); la UI traduce
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
                # PDF: extracción AVANZADA opt-in (OpenDataLoader: títulos + orden
                # de lectura + tablas) o la clásica con PyMuPDF (respeta rotación).
                use_adv = str(advanced).lower() in ("1", "true", "yes", "on") and odl_mod.available()
                if use_adv:
                    try:
                        out_md = await asyncio.to_thread(odl_mod.extract_markdown, tmp_path)
                    except odl_mod.ODLError:
                        out_md = await asyncio.to_thread(pdf_extract.extract_pdf_text, tmp_path)
                else:
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
                        note = "scanned"   # clave i18n (note.scanned); la UI traduce
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
    #   "anon"  → un único placeholder (ver ANON_PLACEHOLDER en anonimal.py)
    anon_mode = (anonymize or "").strip().lower()
    anon_is_strict = str(anon_strict).lower() in ("1", "true", "yes", "on", "estricto", "strict")
    anonymized = None
    pii_count = None
    pseudo_map = {}
    if anon_mode in anonimal_mod.MODES and markdown.strip():
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
        # Scrub de metadata: el título y el source (basename/URL) pueden contener
        # un nombre u otro PII. En vez de descartarlos, los pasamos por el MISMO
        # modo de anonimización para conservar lo legítimo y enmascarar lo sensible.
        def _anon_field(val):
            if not val or not str(val).strip():
                return val
            try:
                out, _n, _m = anonimal_mod.anonymize(
                    str(val), anon_mode, anon_is_strict, None, user_rules, det_ids)
                return out
            except anonimal_mod.AnonimalError:
                # Falla SEGURA para metadata: si no podemos anonimizar, la omitimos.
                return None
        title = await asyncio.to_thread(_anon_field, title)
        source_name = await asyncio.to_thread(_anon_field, source_name)
        # Aviso si el nombre del archivo (original) contiene un CUIT/CUIL/DNI.
        if file_basename and re.search(r"\b\d{8,11}\b", file_basename) and not note:
            note = "filenamePii"   # clave i18n (note.filenamePii); la UI traduce

    STATS["conversions"] += 1
    STATS["chars_out"] += len(markdown)
    # Panel LLM (tokens / ahorro / costo / contexto / inyección). Nunca debe
    # romper la conversión: si algo falla, va None y la UI no muestra el panel.
    llm_panel = None
    try:
        if markdown.strip():
            llm_panel = await asyncio.to_thread(llmprep_mod.analyze, markdown, pii_count or 0)
    except Exception:  # noqa: BLE001
        log.exception("Panel LLM falló (no crítico)")
    # note es una CLAVE i18n estable ("noVoice"|"scanned"|"filenamePii") o null;
    # la UI la traduce client-side (no devolvemos texto en español).
    resp = JSONResponse({
        "source": source_name,
        "title": title,
        "markdown": markdown,
        "llm": llm_panel,
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
    if pseudo_map:
        # El mapa contiene PII en claro (token→original): que no quede en cachés.
        resp.headers["Cache-Control"] = "no-store"
    return resp


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


@app.post("/api/redact")
async def redact_endpoint(
    request: Request,
    file: UploadFile = File(...),
    lang: Optional[str] = Form(default=None),
    anon_strict: Optional[str] = Form(default=None),
    anon_rules: Optional[str] = Form(default=None),
    anon_detectors: Optional[str] = Form(default=None),
    preview: Optional[str] = Form(default=None),
    only: Optional[str] = Form(default=None),
):
    """Censura VISUAL: devuelve el PDF con el PII tachado (redacción real:
    el texto y los píxeles debajo de cada caja se eliminan del archivo).
    Con preview=1 devuelve JSON con la LISTA de lo que se tacharía (sin generar
    el PDF), para confirmar antes de descargar."""
    is_preview = str(preview).lower() in ("1", "true", "yes", "on")
    role = _require(request)
    caps = auth.caps_for(role)
    if not anonimal_mod.available():
        raise HTTPException(status_code=400, detail="La anonimización no está disponible en este servidor.")
    try:
        check_rate(role, _client_ip(request), caps["rate_per_min"])
    except SecurityError as e:
        raise HTTPException(status_code=429, detail=str(e))

    ext = ext_of(file.filename)
    if ext != "pdf" and ext not in IMAGE_EXTS:
        raise HTTPException(status_code=415, detail="La censura visual acepta PDFs e imágenes.")
    try:
        user_rules = anon_rules_mod.parse_rules(anon_rules)
    except anon_rules_mod.AnonRulesError as e:
        raise HTTPException(status_code=400, detail="Reglas de anonimización inválidas: %s" % e)
    det_ids = None if anon_detectors is None else [x.strip() for x in anon_detectors.split(",") if x.strip()]
    strict = str(anon_strict).lower() in ("1", "true", "yes", "on", "estricto", "strict")

    eff_max = _effective_max(caps)
    data = await _read_capped(file, eff_max)
    tmp_path = _write_temp(data, _safe_suffix(file.filename or ""))
    extra_tmp = []
    try:
        pdf_path = tmp_path
        if ext != "pdf":
            # Imagen → PDF de una página (después se le agrega capa de texto por OCR).
            pdf_path = tmp_path + ".pdf"
            extra_tmp.append(pdf_path)
            await asyncio.to_thread(redact_mod.image_to_pdf, tmp_path, pdf_path)
        # Sin capa de texto (escaneado / imagen) → OCR primero, si el rol puede.
        if not redact_mod.has_text(pdf_path):
            if not caps["ocr"]:
                raise HTTPException(status_code=403, detail="Este documento necesita OCR y tu rol no puede usarlo.")
            tess = ocr_mod.resolve_tess_langs(lang)
            ocr_out = await asyncio.to_thread(ocr_mod.ocr_pdf, pdf_path, tess)
            extra_tmp.append(ocr_out)
            pdf_path = ocr_out
        if is_preview:
            ents = await asyncio.to_thread(
                redact_mod.entities_pdf, pdf_path, strict, user_rules, det_ids)
            return JSONResponse({
                "entities": ents,
                "count": sum(e["count"] for e in ents),
                "unique": len(ents),
                "strict": strict,
                "detectors": (len(det_ids) if det_ids is not None else None),
            })
        only_list = None
        if only:
            try:
                parsed = json.loads(only)
                if isinstance(parsed, list):
                    only_list = [str(x) for x in parsed]
            except (ValueError, TypeError):
                only_list = None
        pdf_bytes, entities = await asyncio.to_thread(
            redact_mod.redact_pdf, pdf_path, strict, user_rules, det_ids, only_list)
    except HTTPException:
        STATS["errors"] += 1
        raise
    except (redact_mod.RedactError, anonimal_mod.AnonimalError) as e:
        # Falla SEGURA: nunca devolvemos el documento sin censurar.
        STATS["errors"] += 1
        raise HTTPException(status_code=503, detail=str(e))
    except subprocess.TimeoutExpired:
        STATS["errors"] += 1
        raise HTTPException(status_code=504, detail="El OCR tardó demasiado y se canceló.")
    except Exception as exc:  # noqa: BLE001
        STATS["errors"] += 1
        err_id = uuid.uuid4().hex[:8]
        log.exception("Redacción visual falló [%s] rol=%s", err_id, role)
        raise HTTPException(status_code=422, detail=f"No se pudo censurar el documento (ref {err_id}).") from exc
    finally:
        for p in [tmp_path] + extra_tmp:
            try:
                os.unlink(p)
            except OSError:
                pass

    base = re.sub(r"[^\w\-. ]", "_", Path(file.filename or "documento").stem) or "documento"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{base}-censurado.pdf"',
            "X-Redacted-Entities": str(entities),
        },
    )


@app.post("/api/export")
async def export_endpoint(request: Request, text: str = Form(...), fmt: str = Form(...)):
    """Exporta el Markdown a otro formato (DOCX, ODT, XML DocBook/JATS/TEI, etc.) vía Pandoc."""
    _require_text_endpoint(request, text)
    try:
        data, ext, mime = await asyncio.to_thread(export_mod.convert, text or "", fmt)
    except export_mod.ExportError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return Response(content=data, media_type=mime,
                    headers={"Content-Disposition": f'attachment; filename="documento.{ext}"',
                             "X-Export-Ext": ext})


@app.get("/api/model_prices")
async def model_prices(request: Request):
    """Catálogo de modelos + precios EN VIVO (OpenRouter, cacheado) para el Panel LLM."""
    _require(request)
    data, live = await asyncio.to_thread(pricing_mod.catalog)
    return {"models": data, "defaults": pricing_mod.DEFAULTS, "live": live}


@app.post("/api/compact")
async def compact_endpoint(request: Request, text: str = Form(...)):
    """Devuelve el Markdown compactado (menos tokens, mismo sentido) para descargar."""
    _require_text_endpoint(request, text)
    out = await asyncio.to_thread(llmprep_mod.compact, text or "")
    return Response(out, media_type="text/markdown; charset=utf-8",
                    headers={"X-Tokens-Before": str(llmprep_mod.count_tokens(text or "")),
                             "X-Tokens-After": str(llmprep_mod.count_tokens(out))})


@app.post("/api/chunk")
async def chunk_endpoint(request: Request, text: str = Form(...),
                         size: Optional[str] = Form(default=None)):
    """Parte el Markdown en chunks por presupuesto de tokens. Devuelve JSONL
    (una línea por chunk) listo para embeddings / vector DB."""
    _require_text_endpoint(request, text)
    if size:
        try:
            # int(float(...)) tolera "1024.0"; un valor no numérico es un 422 claro.
            n = max(128, min(8192, int(float(size))))
        except (ValueError, TypeError):
            raise HTTPException(status_code=422, detail="El parámetro 'size' debe ser un número.")
    else:
        n = 1024
    chunks = await asyncio.to_thread(llmprep_mod.chunk, text or "", n)
    lines = []
    for i, c in enumerate(chunks):
        lines.append(json.dumps(
            {"id": i, "tokens": llmprep_mod.count_tokens(c), "text": c}, ensure_ascii=False))
    body = "\n".join(lines) + ("\n" if lines else "")
    return Response(body, media_type="application/x-ndjson; charset=utf-8",
                    headers={"X-Chunk-Count": str(len(chunks))})


def _write_temp(data: bytes, suffix: str) -> str:
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix or "") as tmp:
        tmp.write(data)
        return tmp.name


def urlsplit_path(url: str) -> str:
    return urlparse(url).path or "x"


# index.html con la versión ya inyectada en las URLs de los assets (?v=) para
# invalidar la caché del navegador en cada deploy. Se calcula UNA vez al import
# (el archivo no cambia en runtime) en vez de leer disco + .replace por request.
_INDEX_HTML = (STATIC_DIR / "index.html").read_text(encoding="utf-8").replace("__VER__", APP_VERSION)


@app.get("/", response_class=HTMLResponse)
def index():
    return _INDEX_HTML


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
