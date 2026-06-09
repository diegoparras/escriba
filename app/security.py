"""
Utilidades de seguridad: anti-SSRF, descarga segura de URLs y rate limiting.
"""

import ipaddress
import logging
import os
import socket
import time
from collections import defaultdict
from threading import Lock
from urllib.parse import urlparse

import requests

log = logging.getLogger("markitdown.security")

# Extensiones consideradas "pesadas/riesgosas" para roles bajos.
HEAVY_EXTS = {"mp3", "wav", "m4a", "flac", "ogg", "zip"}

# --- Redis opcional para rate-limit compartido entre workers/instancias ------
REDIS_URL = os.getenv("REDIS_URL")
_redis = None
if REDIS_URL:
    try:
        import redis as _redis_lib
        _redis = _redis_lib.from_url(REDIS_URL, socket_timeout=1, socket_connect_timeout=1)
        _redis.ping()
        log.info("Rate-limit usando Redis (%s)", REDIS_URL)
    except Exception as e:  # noqa: BLE001
        _redis = None
        log.warning("No se pudo conectar a Redis (%s): rate-limit en memoria por proceso.", e)


class SecurityError(Exception):
    """Error de validación de seguridad (se traduce a 4xx en la API)."""


def ext_of(filename: str) -> str:
    return (filename or "").rsplit(".", 1)[-1].lower() if "." in (filename or "") else ""


def _ip_is_blocked(ip_str: str) -> bool:
    ip = ipaddress.ip_address(ip_str)
    return (
        ip.is_private or ip.is_loopback or ip.is_link_local
        or ip.is_reserved or ip.is_multicast or ip.is_unspecified
    )


def assert_public_url(url: str) -> None:
    """
    Valida que la URL sea http/https y que el host NO resuelva a una red interna.
    Lanza SecurityError si algo no cumple. (Anti-SSRF — C2/M5).
    """
    p = urlparse(url)
    if p.scheme not in ("http", "https"):
        raise SecurityError("Solo se permiten URLs http:// o https://.")
    host = p.hostname
    if not host:
        raise SecurityError("URL inválida.")
    try:
        infos = socket.getaddrinfo(host, p.port or (443 if p.scheme == "https" else 80))
    except socket.gaierror:
        raise SecurityError("No se pudo resolver el dominio.")
    for info in infos:
        ip_str = info[4][0]
        if _ip_is_blocked(ip_str):
            raise SecurityError("La URL apunta a una dirección interna o no permitida.")


def safe_fetch(url: str, max_bytes: int, max_redirects: int = 3, timeout: int = 15) -> bytes:
    """
    Descarga una URL de forma segura: solo http/https público, sin seguir
    redirecciones hacia IPs internas, con tope de tamaño y timeout.
    Devuelve los bytes. (Cierra el SSRF también ante redirecciones — C2).
    """
    current = url
    for _ in range(max_redirects + 1):
        assert_public_url(current)
        resp = requests.get(
            current, stream=True, timeout=timeout, allow_redirects=False,
            headers={"User-Agent": "MarkItDown-Web/1.0"},
        )
        if resp.is_redirect or resp.is_permanent_redirect:
            loc = resp.headers.get("location")
            resp.close()
            if not loc:
                raise SecurityError("Redirección inválida.")
            current = requests.compat.urljoin(current, loc)
            continue
        # Respuesta final: leer con tope de tamaño.
        total = 0
        chunks = []
        for chunk in resp.iter_content(64 * 1024):
            total += len(chunk)
            if max_bytes and total > max_bytes:
                resp.close()
                raise SecurityError(f"El contenido remoto supera el límite de {max_bytes // (1024*1024)} MB.")
            chunks.append(chunk)
        resp.close()
        return b"".join(chunks)
    raise SecurityError("Demasiadas redirecciones.")


# --- Rate limiting simple en memoria (por worker; aproximado) ----------------
_buckets: dict = defaultdict(list)
_rl_lock = Lock()


def check_rate(role: str, client_ip: str, limit_per_min: int) -> None:
    """Rate-limit por (rol, IP). limit==0 => sin límite. Usa Redis si está disponible."""
    if not limit_per_min:
        return

    # 1) Redis (compartido entre todos los workers/instancias) — ventana fija de 60s.
    if _redis is not None:
        try:
            window = int(time.time() // 60)
            key = f"rl:{role}:{client_ip}:{window}"
            n = _redis.incr(key)
            if n == 1:
                _redis.expire(key, 70)
            if n > limit_per_min:
                raise SecurityError("Demasiadas solicitudes. Esperá un momento e intentá de nuevo.")
            return
        except SecurityError:
            raise
        except Exception as e:  # noqa: BLE001 — si Redis se cae en runtime, caemos a memoria
            log.warning("Redis falló en runtime (%s): uso memoria para este request.", e)

    # 2) Fallback en memoria (por proceso) — ventana deslizante de 60s.
    now = time.time()
    cutoff = now - 60
    key = f"{role}:{client_ip}"
    with _rl_lock:
        bucket = _buckets[key]
        while bucket and bucket[0] < cutoff:
            bucket.pop(0)
        if len(bucket) >= limit_per_min:
            raise SecurityError("Demasiadas solicitudes. Esperá un momento e intentá de nuevo.")
        bucket.append(now)
