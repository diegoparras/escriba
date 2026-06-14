"""
Catálogo de modelos + precios EN VIVO desde OpenRouter (gratis, sin API key).

Se cachea unas horas en memoria. El frontend lo usa para calcular el costo y el
"¿entra en contexto?" del Panel LLM con datos actuales, y para que el usuario
elija qué modelos mostrar. Si OpenRouter no responde, cae a un fallback mínimo.
"""
import logging
import threading
import time

import requests

log = logging.getLogger("markitdown.pricing")

_URL = "https://openrouter.ai/api/v1/models"
_TTL = 6 * 3600  # 6 h
_cache = {"t": 0.0, "data": None}
_lock = threading.Lock()

# Modelos mostrados por defecto (ids de OpenRouter; se filtran a los que existan).
DEFAULTS = [
    "openai/gpt-4o-mini",
    "anthropic/claude-sonnet-4.6",
    "google/gemini-2.5-pro",
]

# Fallback si la API no responde (precios input USD/1M, estimados).
_FALLBACK = [
    {"id": "openai/gpt-4o-mini", "name": "GPT-4o mini", "in": 0.15, "ctx": 128000},
    {"id": "anthropic/claude-sonnet-4.6", "name": "Claude Sonnet 4.6", "in": 3.0, "ctx": 1000000},
    {"id": "google/gemini-2.5-pro", "name": "Gemini 2.5 Pro", "in": 1.25, "ctx": 1048576},
]


def _fetch():
    r = requests.get(_URL, timeout=12, headers={"User-Agent": "escriba"})
    r.raise_for_status()
    out = []
    for m in r.json().get("data", []):
        mid = m.get("id")
        if not mid or "embed" in mid:        # fuera embeddings
            continue
        p = m.get("pricing") or {}
        try:
            inp = float(p.get("prompt", -1)) * 1e6
        except (TypeError, ValueError):
            continue
        ctx = m.get("context_length") or 0
        if inp < 0 or ctx <= 0:              # precio variable / sin contexto → fuera
            continue
        out.append({"id": mid, "name": (m.get("name") or mid), "in": round(inp, 4), "ctx": ctx})
    out.sort(key=lambda x: x["id"])
    return out


def catalog():
    """Devuelve (lista_modelos, live).

    live=True significa "caché vigente dentro del TTL", no necesariamente un
    fetch recién hecho: la caché puede tener hasta `_TTL` segundos de antigüedad.
    live=False indica que se sirve el fallback (o caché viejo) porque el fetch
    falló o nunca hubo datos.
    """
    now = time.time()
    if _cache["data"] and (now - _cache["t"] < _TTL):
        return _cache["data"], True
    # Double-checked locking: un solo hilo refresca mientras el resto espera y
    # luego ve la caché ya recargada (evita fetches duplicados concurrentes).
    with _lock:
        now = time.time()
        if _cache["data"] and (now - _cache["t"] < _TTL):
            return _cache["data"], True
        try:
            data = _fetch()
            if data:
                _cache["data"], _cache["t"] = data, now
                return data, True
        except Exception as e:  # noqa: BLE001
            log.warning("Precios de OpenRouter no disponibles (%s); uso fallback", e)
    return (_cache["data"] or _FALLBACK), False
