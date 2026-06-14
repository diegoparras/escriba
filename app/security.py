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
from requests.adapters import HTTPAdapter
from urllib3.util import connection as _urllib3_connection

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


def assert_public_url(url: str) -> list:
    """
    Valida que la URL sea http/https y que el host NO resuelva a una red interna.
    Lanza SecurityError si algo no cumple. (Anti-SSRF — C2/M5).

    Devuelve la lista de IPs (str) a las que resolvió el host, ya validadas como
    públicas. El llamador debe usar SOLO estas IPs para conectar (pinning),
    evitando una segunda resolución DNS que habilitaría DNS rebinding / TOCTOU.
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
    validated_ips = []
    for info in infos:
        ip_str = info[4][0]
        if _ip_is_blocked(ip_str):
            raise SecurityError("La URL apunta a una dirección interna o no permitida.")
        if ip_str not in validated_ips:
            validated_ips.append(ip_str)
    if not validated_ips:
        raise SecurityError("No se pudo resolver el dominio.")
    return validated_ips


class _PinnedIPAdapter(HTTPAdapter):
    """
    HTTPAdapter que fuerza la conexión a una IP previamente validada (pinning),
    preservando el hostname original para Host header / SNI / verificación TLS.

    Cierra la ventana de DNS rebinding / TOCTOU: la IP que se valida en
    assert_public_url() es EXACTAMENTE la IP a la que se conecta, sin re-resolver.
    """

    def __init__(self, *args, pinned_ip: str = None, **kwargs):
        self._pinned_ip = pinned_ip
        super().__init__(*args, **kwargs)

    def send(self, request, **kwargs):
        # urllib3 resuelve el hostname vía socket.getaddrinfo. Lo monkeypatcheamos
        # SOLO durante este send para devolver la IP pinneada, manteniendo el
        # hostname original en la URL (así Host header y SNI no cambian).
        if not self._pinned_ip:
            return super().send(request, **kwargs)

        pinned = self._pinned_ip
        orig_create_connection = _urllib3_connection.create_connection

        def _pinned_create_connection(address, *a, **kw):
            host, port = address[0], address[1]
            return orig_create_connection((pinned, port), *a, **kw)

        _urllib3_connection.create_connection = _pinned_create_connection
        try:
            return super().send(request, **kwargs)
        finally:
            _urllib3_connection.create_connection = orig_create_connection


def safe_fetch(url: str, max_bytes: int, max_redirects: int = 3, timeout: int = 15) -> bytes:
    """
    Descarga una URL de forma segura: solo http/https público, sin seguir
    redirecciones hacia IPs internas, con tope de tamaño y timeout.
    Devuelve los bytes. (Cierra el SSRF también ante redirecciones — C2).
    """
    current = url
    for _ in range(max_redirects + 1):
        # Validamos y PINNEAMOS: la IP que validamos es la única a la que
        # conectaremos. Sin segunda resolución DNS => sin ventana de rebinding.
        validated_ips = assert_public_url(current)
        pinned_ip = validated_ips[0]
        p = urlparse(current)
        scheme = (p.scheme or "").lower()

        session = requests.Session()
        adapter = _PinnedIPAdapter(pinned_ip=pinned_ip)
        # Montamos el adapter sobre el esquema concreto para que toda conexión
        # de este request use la IP pinneada.
        session.mount(scheme + "://", adapter)
        try:
            resp = session.get(
                current, stream=True, timeout=timeout, allow_redirects=False,
                headers={"User-Agent": "MarkItDown-Web/1.0"},
            )
        except requests.RequestException as e:
            session.close()
            raise SecurityError("No se pudo descargar la URL remota.") from e

        if resp.is_redirect or resp.is_permanent_redirect:
            loc = resp.headers.get("location")
            resp.close()
            session.close()
            if not loc:
                raise SecurityError("Redirección inválida.")
            current = requests.compat.urljoin(current, loc)
            continue
        # Respuesta final: leer con tope de tamaño.
        try:
            total = 0
            chunks = []
            for chunk in resp.iter_content(64 * 1024):
                total += len(chunk)
                if max_bytes and total > max_bytes:
                    raise SecurityError(f"El contenido remoto supera el límite de {max_bytes // (1024*1024)} MB.")
                chunks.append(chunk)
            return b"".join(chunks)
        finally:
            resp.close()
            session.close()
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
