"""
Panel LLM: métricas y utilidades para preparar el Markdown de cara a un LLM.

Todo es DETERMINÍSTICO y liviano (un tokenizer BPE + regex + conteo) — no corre
ningún modelo de lenguaje. Responde a los dos problemas del pitch de Escriba:
TOKENS (cuántos, cuánto cuestan, cuántos ahorrás, si entra en el contexto) y
PRIVACIDAD (cuánto PII se enmascaró, y si el documento trae prompt-injection).
"""
import logging
import re

log = logging.getLogger("markitdown.llmprep")

# ---------------------------------------------------------------------------
# Tokenización (tiktoken o200k_base; fallback ~4 chars/token si no está)
# ---------------------------------------------------------------------------
_ENC = None


def _enc():
    global _ENC
    if _ENC is None:
        try:
            import tiktoken
            _ENC = tiktoken.get_encoding("o200k_base")
        except Exception as e:  # noqa: BLE001
            log.warning("tiktoken no disponible (%s); uso estimación por caracteres", e)
            _ENC = False
    return _ENC


def count_tokens(text: str) -> int:
    e = _enc()
    if e:
        try:
            return len(e.encode(text or "", disallowed_special=()))
        except Exception:  # noqa: BLE001
            pass
    return max(1, len(text or "") // 4)


# ---------------------------------------------------------------------------
# Compactador "ahorro de tokens": saca ruido sin perder sentido
# ---------------------------------------------------------------------------
_PAGE_NUM = re.compile(
    r"^\s*(?:p[áa]g(?:ina)?\.?\s*|page\s*)?[-–—]?\s*\d{1,4}\s*[-–—]?\s*"
    r"(?:(?:de|of|/)\s*\d{1,4})?\s*$", re.I)


def compact(md: str) -> str:
    """Reduce tokens: colapsa espacios/blancos, saca líneas de número de página
    y deduplica líneas consecutivas (headers/footers repetidos). Respeta los
    bloques de código (``` ... ```) para no romperlos."""
    if not md:
        return md or ""
    out, in_code, blank = [], False, 0
    for line in md.split("\n"):
        s = line.rstrip()
        if s.lstrip().startswith("```"):
            in_code = not in_code
            out.append(s)
            blank = 0
            continue
        if in_code:
            out.append(s)
            continue
        if not s.strip():
            blank += 1
            if blank <= 1:
                out.append("")
            continue
        blank = 0
        if _PAGE_NUM.match(s):
            continue
        s = re.sub(r"[ \t]{2,}", " ", s)
        if out and s.strip() and s == out[-1]:   # duplicado consecutivo
            continue
        out.append(s)
    text = "\n".join(out).strip()
    text = re.sub(r"\n{3,}", "\n\n", text)   # blancos sobrantes (p.ej. al sacar nº de página)
    return (text + "\n") if text else ""


# ---------------------------------------------------------------------------
# Detector de prompt-injection (heurístico, multilingüe, bajo falso-positivo)
# ---------------------------------------------------------------------------
_INJ = [
    (r"ignore (all |the )?(previous|above|prior) (instructions?|prompts?)", "Pide ignorar las instrucciones anteriores"),
    (r"disregard (all |the )?(previous|above|prior)", "Pide descartar lo anterior"),
    (r"ignor[áa] (las |todas las )?(instrucciones|indicaciones)", "Pide ignorar instrucciones"),
    (r"olvid[áa]\w* (las |todas )?(tus )?instrucciones", "Pide olvidar instrucciones"),
    (r"(system prompt|prompt del sistema|system message)", "Referencia al system prompt"),
    (r"(you are now|from now on you are|a partir de ahora (sos|eres))", "Intenta reasignar el rol del modelo"),
    (r"(do not (tell|inform|reveal)[^.\n]{0,25}user|no le (digas|informes|reveles) al usuario)", "Pide ocultarle algo al usuario"),
    (r"(jailbreak|\bDAN\b mode|developer mode)", "Patrón de jailbreak"),
]
_ZW = re.compile(r"[​‌‍⁠﻿]")


def detect_injection(text: str):
    if not text:
        return []
    found, seen = [], set()
    for pat, why in _INJ:
        m = re.search(pat, text, re.I)
        if m and why not in seen:
            seen.add(why)
            i, j = max(0, m.start() - 25), min(len(text), m.end() + 25)
            snip = re.sub(r"\s+", " ", text[i:j]).strip()
            found.append({"why": why, "snippet": ("…" + snip + "…")})
    if _ZW.search(text) and "zw" not in seen:
        found.append({"why": "Caracteres invisibles (zero-width) ocultos en el texto", "snippet": ""})
    return found[:5]


# ---------------------------------------------------------------------------
# Chunking para RAG (por presupuesto de tokens, con solapamiento)
# ---------------------------------------------------------------------------
def chunk(md: str, size: int = 1024, overlap: int = 64):
    if not md:
        return []
    e = _enc()
    if e:
        try:
            import semchunk
            counter = lambda t: len(e.encode(t, disallowed_special=()))  # noqa: E731
            chunker = semchunk.chunkerify(counter, size)
            return chunker(md, overlap=overlap)
        except Exception as ex:  # noqa: BLE001
            log.warning("semchunk falló (%s); uso corte por caracteres", ex)
    step = max(1, (size - overlap) * 4)
    return [md[i:i + size * 4] for i in range(0, len(md), step)] or [md]


def chunk_count(md: str, size: int = 1024) -> int:
    try:
        return len(chunk(md, size))
    except Exception:  # noqa: BLE001
        return 0


# ---------------------------------------------------------------------------
# Análisis completo para el panel (se adjunta a la respuesta de /api/convert)
# ---------------------------------------------------------------------------
def analyze(markdown: str, pii_count: int = 0) -> dict:
    md = markdown or ""
    toks = count_tokens(md)
    comp_toks = count_tokens(compact(md))
    saved = max(0, toks - comp_toks)
    # Costo y "¿entra en contexto?" los calcula el FRONTEND con precios EN VIVO
    # (ver pricing.py / /api/model_prices). Acá solo el conteo de tokens.
    return {
        "tokens": toks,
        "tokens_compact": comp_toks,
        "saved": saved,
        "saved_pct": round(100 * saved / toks) if toks else 0,
        "injection": detect_injection(md),
        "pii_count": int(pii_count or 0),
        "chunks": chunk_count(md),
    }
