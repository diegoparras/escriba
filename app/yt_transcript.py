"""
Obtención de transcripciones/subtítulos de YouTube.

Método principal: yt-dlp (robusto, se actualiza rápido ante los cambios de YouTube).
Fallback: youtube-transcript-api.

Si el servidor está en una IP bloqueada por YouTube, configurá:
  - YT_PROXY    (ej: http://user:pass@host:port)  → enruta los pedidos
  - YT_COOKIES  (ruta a un cookies.txt de una sesión logueada de YouTube)
"""

import json
import os
import re
import tempfile

import requests

YT_PROXY = os.getenv("YT_PROXY")
YT_COOKIES = os.getenv("YT_COOKIES")  # ruta a cookies.txt (formato Netscape)

# Tope de tamaño para cookies pegadas por el usuario (defensa básica).
_MAX_COOKIES_CHARS = 200_000


def _write_cookiefile(cookies_text):
    """Escribe las cookies pegadas por el usuario en un cookiefile temporal.

    SEGURIDAD: archivo temporal con permisos 600, NUNCA se loguea el contenido,
    y el llamador DEBE borrarlo en un finally. No se persiste nada en el server.
    """
    txt = (cookies_text or "").strip()
    if not txt:
        return None
    txt = txt[:_MAX_COOKIES_CHARS]
    # yt-dlp exige el "magic header" de Netscape; si falta, lo anteponemos.
    head = txt.lstrip()
    if not (head.startswith("# Netscape") or head.startswith("# HTTP Cookie")):
        txt = "# Netscape HTTP Cookie File\n" + txt
    fd, path = tempfile.mkstemp(prefix="ytck_", suffix=".txt")
    try:
        os.write(fd, txt.encode("utf-8", "replace"))
    finally:
        os.close(fd)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return path


def _proxies():
    return {"http": YT_PROXY, "https": YT_PROXY} if YT_PROXY else None


def _pref_langs(lang):
    pref = []
    if lang and lang != "auto":
        pref.append(lang.split("-")[0].lower())
    for l in ("es", "en", "pt", "fr", "it", "de"):
        if l not in pref:
            pref.append(l)
    return pref


def _parse_subs(content, ext):
    """Convierte json3 / vtt / srv a texto plano."""
    txt = (content or "").lstrip()
    if ext == "json3" or txt.startswith("{"):
        try:
            data = json.loads(content)
            parts = []
            for ev in data.get("events", []) or []:
                for seg in ev.get("segs", []) or []:
                    s = seg.get("utf8")
                    if s:
                        parts.append(s)
            return re.sub(r"\s+\n", "\n", "".join(parts)).strip()
        except Exception:
            pass
    # VTT / SRV / SRT
    out = []
    for line in (content or "").splitlines():
        line = line.strip()
        if (not line or line.startswith("WEBVTT") or "-->" in line
                or line.isdigit() or line.startswith("Kind:") or line.startswith("Language:")):
            continue
        line = re.sub(r"<[^>]+>", "", line)        # quita etiquetas de timing
        line = re.sub(r"&nbsp;", " ", line)
        if line:
            out.append(line)
    # dedup de líneas consecutivas repetidas (típico en auto-subs)
    dedup = []
    for l in out:
        if not dedup or dedup[-1] != l:
            dedup.append(l)
    return " ".join(dedup).strip()


# Clientes de YouTube que prueba yt-dlp, en orden. Distintos clientes tienen
# distinto comportamiento ante el "bot-check" de YouTube: cuando una IP de
# datacenter es rechazada por el cliente web, los clientes de apps (android/ios/
# tv) suelen pasar igual. Probamos varios hasta que uno devuelva subtítulos.
_YT_CLIENTS = (None, ["android"], ["ios"], ["tv"], ["mweb"], ["web"])


def _ydl_opts(client, cookiefile=None):
    # ignore_no_formats_error: solo queremos los subtítulos, no el video; sin
    # esto algunos clientes fallan con "Requested format is not available" /
    # "DRM protected" y perderíamos su lista de subtítulos.
    opts = {"skip_download": True, "quiet": True, "no_warnings": True,
            "ignore_no_formats_error": True}
    if YT_PROXY:
        opts["proxy"] = YT_PROXY
    # Cookies del usuario (pegadas en la UI) tienen prioridad sobre las del server.
    ck = cookiefile or (YT_COOKIES if YT_COOKIES and os.path.exists(YT_COOKIES) else None)
    if ck:
        opts["cookiefile"] = ck
    if client:
        opts["extractor_args"] = {"youtube": {"player_client": client}}
    return opts


def _extract_info(url, cookiefile=None):
    """Prueba varios clientes de YouTube hasta obtener info con subtítulos."""
    import yt_dlp
    last_err = None
    best = None
    for client in _YT_CLIENTS:
        try:
            with yt_dlp.YoutubeDL(_ydl_opts(client, cookiefile)) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception as e:  # noqa: BLE001
            last_err = e
            continue
        if info.get("subtitles") or info.get("automatic_captions"):
            return info               # este cliente trajo subtítulos: listo
        best = best or info           # guardamos el primero por si ninguno trae
    if best is not None:
        return best
    raise last_err or ValueError("no info from any client")


def _via_ytdlp(url, lang, cookiefile=None):
    info = _extract_info(url, cookiefile)
    title = info.get("title") or "YouTube"
    subs = info.get("subtitles") or {}
    auto = info.get("automatic_captions") or {}
    prefs = _pref_langs(lang)

    def pick(d):
        for want in prefs:
            for code, tracks in d.items():
                if code.split("-")[0].lower() == want and tracks:
                    return tracks
        for code, tracks in d.items():     # cualquiera
            if tracks:
                return tracks
        return None

    tracks = pick(subs) or pick(auto)      # manuales primero, luego automáticos
    if not tracks:
        raise ValueError("no subtitles in info")
    chosen = None
    for ext in ("json3", "srv3", "vtt", "srv1"):
        for tk in tracks:
            if tk.get("ext") == ext and tk.get("url"):
                chosen = tk
                break
        if chosen:
            break
    chosen = chosen or tracks[-1]
    r = requests.get(chosen["url"], timeout=25, proxies=_proxies(),
                     headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    text = _parse_subs(r.text, chosen.get("ext"))
    if not text:
        raise ValueError("empty subtitle content")
    return title, text


def _via_api(url, lang, cookiefile=None):
    from youtube_transcript_api import YouTubeTranscriptApi
    vid = _video_id(url)
    if not vid:
        raise ValueError("no video id")
    api = YouTubeTranscriptApi()  # nota: el fallback va sin cookies (best-effort)
    fetched = api.fetch(vid, languages=_pref_langs(lang))
    data = fetched.to_raw_data() if hasattr(fetched, "to_raw_data") else list(fetched)
    parts = [(s.get("text") if isinstance(s, dict) else getattr(s, "text", "")) for s in data]
    text = " ".join(p for p in parts if p).strip()
    if not text:
        raise ValueError("empty transcript")
    return None, text


def _video_id(url):
    from urllib.parse import urlparse, parse_qs
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
            if key in parts and parts.index(key) + 1 < len(parts):
                return parts[parts.index(key) + 1]
    return None


def youtube_markdown(url, lang, cookies=None):
    """Devuelve Markdown con la transcripción. Lanza Exception si no se pudo.

    cookies: contenido (texto) de un cookies.txt pegado por el usuario en la UI.
    Se usa SOLO para este pedido y el archivo temporal se borra al terminar.
    """
    cookiefile = _write_cookiefile(cookies)
    try:
        title, text = None, None
        errs = []
        for fn in (_via_ytdlp, _via_api):
            try:
                title, text = fn(url, lang, cookiefile)
                if text:
                    break
            except Exception as e:  # noqa: BLE001
                errs.append("%s: %s" % (fn.__name__, e))
                text = None
        if not text:
            raise RuntimeError(" | ".join(errs) or "no transcript")
        head = title or "YouTube"
        return "# %s\n\n[%s](%s)\n\n%s" % (head, url, url, text)
    finally:
        if cookiefile:
            try:
                os.unlink(cookiefile)   # nunca dejamos cookies en disco
            except OSError:
                pass
