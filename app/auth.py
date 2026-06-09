"""
Autenticación y roles para MarkItDown Web.

Tres roles con privilegios crecientes: humano < angel < dios.
- Login por contraseña (una por rol, vía variables de entorno).
- Sesión firmada con HMAC-SHA256 (sin dependencias externas).
- Token en cookie HttpOnly (web) o header Authorization: Bearer (API).

IMPORTANTE (multi-worker): SECRET_KEY y las contraseñas deben venir del entorno
para ser iguales en todos los workers. El entrypoint.sh las genera una sola vez
si no están definidas y las exporta. En dev (1 worker) hay fallback local.
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import time

log = logging.getLogger("markitdown.auth")

SESSION_TTL = int(os.getenv("SESSION_TTL_HOURS", "12")) * 3600
COOKIE_NAME = "mid_session"

# Clave de firma. En prod la fija el entrypoint; en dev se genera (1 worker).
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    SECRET_KEY = secrets.token_hex(32)
    log.warning("SECRET_KEY no definida: usando una temporal (las sesiones se "
                "reinician al reiniciar y NO sirve con varios workers).")
SECRET_BYTES = SECRET_KEY.encode()


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


# --- Capacidades por rol (overridables por env) ------------------------------
ROLE_CAPS = {
    "dios": {
        "label": "DIOS",
        "convert_url": True,
        "allow_internal": True,          # rutas locales, file://, IPs privadas
        "max_file_mb": _env_int("GOD_MAX_MB", 0),     # 0 = sin límite
        "max_batch": _env_int("GOD_MAX_BATCH", 0),    # 0 = sin límite
        "audio_zip": True,
        "ocr": True,
        "llm": True,
        "llm_custom_base": True,
        "server_keys": True,
        "stats": "full",
        "rate_per_min": _env_int("GOD_RATE", 0),       # 0 = sin límite
    },
    "angel": {
        "label": "ANGEL",
        "convert_url": True,
        "allow_internal": False,
        "max_file_mb": _env_int("ANGEL_MAX_MB", 100),
        "max_batch": _env_int("ANGEL_MAX_BATCH", 10),
        "audio_zip": True,
        "ocr": True,
        "llm": True,
        "llm_custom_base": True,
        "server_keys": True,
        "stats": "basic",
        "rate_per_min": _env_int("ANGEL_RATE", 60),
    },
    "humano": {
        "label": "HUMANO",
        "convert_url": False,
        "allow_internal": False,
        "max_file_mb": _env_int("HUMAN_MAX_MB", 25),
        "max_batch": _env_int("HUMAN_MAX_BATCH", 3),
        "audio_zip": False,
        "ocr": False,
        "llm": True,
        "llm_custom_base": False,
        "server_keys": False,
        "stats": "none",
        "rate_per_min": _env_int("HUMAN_RATE", 15),
    },
}

# Token de API estático para automatización (n8n, scripts). Mapea a un rol.
API_TOKEN = os.getenv("API_TOKEN")
API_TOKEN_ROLE = os.getenv("API_TOKEN_ROLE", "angel")
if API_TOKEN_ROLE not in ROLE_CAPS:
    API_TOKEN_ROLE = "angel"

# Permitir nivel HUMANO sin login (para un conversor público).
HUMAN_OPEN = os.getenv("HUMAN_OPEN", "false").lower() in ("1", "true", "yes")

# Contraseñas por rol. Si no se define, ese rol queda deshabilitado para login.
_PASSWORDS = {
    "dios": os.getenv("GOD_PASSWORD"),
    "angel": os.getenv("ANGEL_PASSWORD"),
    "humano": os.getenv("HUMAN_PASSWORD"),
}


def _b64e(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def make_token(role: str) -> str:
    payload = {"role": role, "exp": int(time.time()) + SESSION_TTL}
    body = _b64e(json.dumps(payload, separators=(",", ":")).encode())
    sig = _b64e(hmac.new(SECRET_BYTES, body.encode(), hashlib.sha256).digest())
    return f"{body}.{sig}"


def verify_token(token: str):
    """Devuelve el rol si el token es válido y no expiró, si no None."""
    try:
        body, sig = token.split(".", 1)
        expected = _b64e(hmac.new(SECRET_BYTES, body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(_b64d(body))
        if payload.get("exp", 0) < time.time():
            return None
        role = payload.get("role")
        return role if role in ROLE_CAPS else None
    except Exception:
        return None


def role_for_password(password: str):
    """Compara la contraseña (en tiempo constante) contra cada rol configurado."""
    match = None
    for role, real in _PASSWORDS.items():
        if real and hmac.compare_digest(password, real):
            match = role
    return match


def _api_token_role(request):
    """Si el request trae el API token estático válido, devuelve su rol."""
    if not API_TOKEN:
        return None
    xkey = request.headers.get("x-api-key")
    if xkey and hmac.compare_digest(xkey, API_TOKEN):
        return API_TOKEN_ROLE
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        if hmac.compare_digest(auth[7:].strip(), API_TOKEN):
            return API_TOKEN_ROLE
    return None


def role_from_request(request):
    """Extrae el rol desde el API token, la cookie o el header Authorization."""
    # 1) Token de API estático (automatización)
    api_role = _api_token_role(request)
    if api_role:
        return api_role
    # 2) Sesión firmada (cookie o Bearer)
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            token = auth[7:].strip()
    if not token:
        return None
    return verify_token(token)


def identity(request):
    """Rol efectivo del request: sesión válida, o 'humano' si HUMAN_OPEN, o None."""
    role = role_from_request(request)
    if role:
        return role
    if HUMAN_OPEN:
        return "humano"
    return None


def caps_for(role: str) -> dict:
    return ROLE_CAPS[role]


def public_caps(role: str) -> dict:
    """Versión de las capacidades para enviar al frontend."""
    c = ROLE_CAPS[role]
    return {
        "role": role,
        "label": c["label"],
        "convertUrl": c["convert_url"],
        "allowInternal": c["allow_internal"],
        "maxFileMb": c["max_file_mb"],
        "maxBatch": c["max_batch"],
        "audioZip": c["audio_zip"],
        "ocr": c["ocr"],
        "llm": c["llm"],
        "llmCustomBase": c["llm_custom_base"],
        "stats": c["stats"],
        "ratePerMin": c["rate_per_min"],
    }
