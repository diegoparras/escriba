"""
Cliente de Escriba hacia el microservicio Anonimal (OpenAI Privacy Filter) +
red de seguridad por regex para identificadores estructurados argentinos.

OPF detecta muy bien nombres/emails/teléfonos, pero el modelo BASE tiene recall
limitado en `account_number` sin pista fuerte (~0,80) — en la práctica deja
pasar CUIT/CUIL/DNI/CBU sueltos. Para un contrato eso es una fuga inaceptable.

Solución: combinamos los spans de OPF con un set de regex DETERMINÍSTICAS
(con contexto, para no enmascarar montos tipo $1.200.000) que garantizan el
enmascarado de CUIT, CUIL, DNI, CBU, alias bancarios y emails. Después armamos
la salida (tipada o anónima) desde el conjunto unificado de spans.

DESACTIVADO si ANONIMAL_URL no está seteado (available() = False).
"""
import hashlib
import hmac
import logging
import os
import re

import requests

from . import anon_rules
from . import detectors

log = logging.getLogger("markitdown.anonimal")

ANONIMAL_URL = (os.getenv("ANONIMAL_URL", "") or "").rstrip("/")
ANON_PLACEHOLDER = "<<ANOM_DATA>>"

# Read timeout (segundos) del pedido a Anonimal. La inferencia en CPU puede
# tardar en documentos grandes; subilo con la env ANONIMAL_TIMEOUT. 0 = sin tope.
try:
    _READ_TIMEOUT = int(os.getenv("ANONIMAL_TIMEOUT", "180"))
except ValueError:
    _READ_TIMEOUT = 180
_TIMEOUT = (5, _READ_TIMEOUT or None)   # (connect, read); None = sin límite de lectura


class AnonimalError(Exception):
    """Falla al anonimizar (servicio caído, cargando, texto muy largo, etc.)."""


def available() -> bool:
    return bool(ANONIMAL_URL)


def _normalize(text: str) -> str:
    """De-hyphenación de cortes de línea de PDF: "andes-\\ngi" -> "andes-gi",
    "27-\\n3178" -> "27-3178". Evita que un \\n parta un CUIT o un email."""
    return re.sub(r"-[ \t]*\n[ \t]*", "-", text)


# ---------------------------------------------------------------------------
# HTTP a Anonimal
# ---------------------------------------------------------------------------
def _detect(text: str) -> dict:
    if not ANONIMAL_URL:
        raise AnonimalError("La anonimización no está configurada (ANONIMAL_URL vacío).")
    try:
        r = requests.post(f"{ANONIMAL_URL}/anonymize", json={"text": text}, timeout=_TIMEOUT)
    except requests.RequestException as e:
        raise AnonimalError(f"No se pudo contactar al anonimizador: {e}") from e
    if r.status_code == 503:
        raise AnonimalError("El anonimizador se está iniciando. Probá de nuevo en unos segundos.")
    if r.status_code == 413:
        raise AnonimalError("El texto es demasiado largo para anonimizar.")
    if not r.ok:
        raise AnonimalError(f"El anonimizador respondió {r.status_code}.")
    try:
        return r.json()
    except ValueError as e:
        raise AnonimalError("Respuesta inválida del anonimizador.") from e


# ---------------------------------------------------------------------------
# Unificación de spans (OPF + regex) y armado de la salida
# ---------------------------------------------------------------------------
def _locate(text, s):
    """Resuelve (start, end) de un span de OPF; verifica offsets y cae a buscar."""
    n = len(text)
    frag = s.get("text")
    try:
        st, en = int(s["start"]), int(s["end"])
    except (KeyError, TypeError, ValueError):
        st = en = -1
    if 0 <= st < en <= n and (frag is None or text[st:en] == frag):
        return st, en
    if frag:
        i = text.find(frag)
        if i >= 0:
            return i, i + len(frag)
    return None


def _collect(text, opf_spans):
    spans = []
    for s in opf_spans or []:
        rng = _locate(text, s)
        if rng:
            spans.append({"start": rng[0], "end": rng[1],
                          "placeholder": s.get("placeholder") or "<REDACTED>"})
    return spans


def _propagate(text, spans):
    """Si un string ya fue marcado como PII, enmascararlo en TODAS sus apariciones.

    OPF a veces detecta un nombre/dirección en un contexto pero lo deja pasar en
    otro (p. ej. el mismo nombre en el encabezado y en "Razón Social:"). Como ya
    está CONFIRMADO como PII, lo replicamos en todo el documento. Guard de
    longitud para no propagar fragmentos triviales.
    """
    extra = []
    seen = set()
    for s in spans:
        frag = text[s["start"]:s["end"]]
        key = frag.strip()
        if len(key) < 4 or key in seen:
            continue
        seen.add(key)
        i = text.find(frag)
        while i >= 0:
            extra.append({"start": i, "end": i + len(frag), "placeholder": s["placeholder"]})
            i = text.find(frag, i + len(frag))
    return extra


def _merge(spans):
    """Ordena y fusiona spans que se solapan (conserva el 1er placeholder)."""
    spans = sorted(spans, key=lambda s: (s["start"], s["end"]))
    merged = []
    for s in spans:
        if merged and s["start"] < merged[-1]["end"]:
            if s["end"] > merged[-1]["end"]:
                merged[-1]["end"] = s["end"]
        else:
            merged.append(dict(s))
    return merged


# Nombre de tipo por placeholder, para los tokens de seudonimización.
_TYPE_NAME = {
    "<PRIVATE_PERSON>": "PERSONA", "<PRIVATE_ADDRESS>": "DOMICILIO",
    "<PRIVATE_EMAIL>": "EMAIL", "<PRIVATE_PHONE>": "TEL",
    "<ACCOUNT_NUMBER>": "ID", "<PRIVATE_DATE>": "FECHA",
    "<PRIVATE_URL>": "URL", "<SECRET>": "SECRETO", "<REDACTED>": "DATO",
}


def type_name(placeholder):
    """Nombre legible del tipo para un placeholder (público; ver _TYPE_NAME)."""
    return _TYPE_NAME.get(placeholder, "DATO")


def _pseudonymize(text, merged):
    """Reemplaza cada entidad por un token ESTABLE y tipado («PERSONA_1»…).
    Mismo valor → mismo token (consistencia). Devuelve (texto, cantidad, mapa
    token→original) para poder RE-HIDRATAR la respuesta del LLM después."""
    counters, token_for = {}, {}

    def tok(ph, frag):
        if frag in token_for:
            return token_for[frag]
        typ = _TYPE_NAME.get(ph, "DATO")
        counters[typ] = counters.get(typ, 0) + 1
        t = "«%s_%d»" % (typ, counters[typ])
        token_for[frag] = t
        return t

    parts, cur = [], 0
    for s in merged:
        st, en = s["start"], s["end"]
        if en <= cur:
            continue
        if st < cur:
            st = cur
        parts.append(text[cur:st])
        parts.append(tok(s["placeholder"], text[st:en]))
        cur = en
    parts.append(text[cur:])
    mapping = {t: orig for orig, t in token_for.items()}   # token → original
    return "".join(parts), len(token_for), mapping


def restore(text: str, mapping: dict) -> str:
    """Re-hidrata: reemplaza los tokens por sus valores originales. Lo usa el
    usuario sobre la respuesta del LLM. Tokens más largos primero (evita choques)."""
    for token in sorted(mapping or {}, key=len, reverse=True):
        text = text.replace(token, mapping[token])
    return text


def _build(text, merged, anon):
    parts, cur = [], 0
    for s in merged:
        st, en = s["start"], s["end"]
        if en <= cur:
            continue
        if st < cur:
            st = cur
        parts.append(text[cur:st])
        parts.append(ANON_PLACEHOLDER if anon else s["placeholder"])
        cur = en
    parts.append(text[cur:])
    return "".join(parts)


# ---------------------------------------------------------------------------
# Operadores extra (estilo Presidio): enmascarado parcial y hash estable
# ---------------------------------------------------------------------------
# Clave para el hash estable. Fijala con ANON_HASH_KEY para que el MISMO dato
# produzca el MISMO seudónimo entre ejecuciones y entre documentos (linkage).
_HASH_KEY = (os.getenv("ANON_HASH_KEY", "") or "escriba-pseudonym-v1").encode("utf-8")


def _apply(text, merged, render):
    """Reconstruye el texto aplicando render(fragmento, placeholder) a cada span."""
    parts, cur = [], 0
    for s in merged:
        st, en = s["start"], s["end"]
        if en <= cur:
            continue
        if st < cur:
            st = cur
        parts.append(text[cur:st])
        parts.append(render(text[st:en], s["placeholder"]))
        cur = en
    parts.append(text[cur:])
    return "".join(parts)


def _mask_value(frag, typ):
    """Enmascarado PARCIAL type-aware: conserva una pista mínima de utilidad sin
    exponer el dato (últimos 4 de un ID, dominio del email, iniciales de nombres)."""
    s = frag.strip()
    if not s:
        return frag
    if typ == "EMAIL" and "@" in s:
        local, _, dom = s.partition("@")
        return "%s•••@%s" % (local[:1] or "•", dom)
    if typ == "URL":
        return "•••"
    digits = re.sub(r"\D", "", s)
    if typ in ("ID", "TEL") or len(digits) >= 6:    # numérico/identificador → últimos 4
        last = s[-4:]
        head = re.sub(r"[0-9A-Za-z]", "•", s[:-4])
        return (head + last) if head else ("••••" + last)
    # nombres / domicilios / texto libre → inicial de cada palabra
    return " ".join((w[0] + "•" * max(1, len(w) - 1)) if w else w for w in s.split())


def _hash_token(frag, typ):
    """Seudónimo ESTABLE por HMAC: mismo dato (normalizado) → mismo token, acá y
    en otros documentos. Irreversible y sin mapa (sirve para linkage anonimizado)."""
    h = hmac.new(_HASH_KEY, frag.strip().lower().encode("utf-8"), hashlib.sha256).hexdigest()[:6]
    return "«%s_%s»" % (typ, h)


def _known_spans(text, known_pii):
    """Localiza en el texto los valores de campos detectados por layout (factura)
    y los marca en TODAS sus apariciones, con el placeholder de su tipo."""
    out = []
    for val, ph in (known_pii or []):
        frag = _normalize(val).strip()
        if len(frag) < 2:
            continue
        i = text.find(frag)
        while i >= 0:
            out.append({"start": i, "end": i + len(frag), "placeholder": ph})
            i = text.find(frag, i + len(frag))
    return out


def detect_spans(text, strict=False, known_pii=None, rules=None, detector_ids=None):
    """Detecta PII y devuelve los spans FUSIONADOS sobre `text` tal cual
    (los offsets valen sobre el texto recibido; acá NO se normaliza).
    Lo usa anonymize() y también la redacción visual (redact.py)."""
    data = _detect(text)
    spans = _collect(text, data.get("detected_spans") or [])     # OPF (NER)
    spans += detectors.run(text, detector_ids, strict)           # detectores built-in
    spans += _known_spans(text, known_pii)    # campos del comprobante (layout)
    spans += anon_rules.custom_spans(text, rules)   # reglas del usuario (RE2)
    spans += _propagate(text, spans)          # mismo dato PII → tapado en todo el doc
    merged = _merge(spans)
    keep = anon_rules.keep_set(rules)         # lista blanca del usuario: nunca enmascarar
    if keep:
        merged = [s for s in merged if text[s["start"]:s["end"]].strip() not in keep]
    return merged


def anonymize(text: str, mode: str, strict: bool = False, known_pii=None,
              rules=None, detector_ids=None):
    """
    Anonimiza `text`. mode ∈ {"typed","anon","seudo","mask","hash"}.
      - typed  → placeholders por categoría (<PRIVATE_PERSON>…)
      - anon   → un único placeholder <<ANOM_DATA>>
      - seudo  → token reversible «PERSONA_1» + mapa (re-hidratable)
      - mask   → enmascarado parcial type-aware (••••3456) — irreversible
      - hash   → seudónimo estable por HMAC (mismo dato → mismo token) — irreversible
    - strict: si no se especifican detectores, prende también los 'strict'.
    - known_pii: campos detectados por layout (comprobantes); se enmascaran sí o sí.
    - rules: reglas del usuario (RE2).
    - detector_ids: lista de ids de detectores built-in activos (None = defaults).
    Devuelve (texto, cantidad, mapa). Lanza AnonimalError si falla (el llamador
    NO debe devolver el texto original: sería fuga de PII).
    """
    if mode not in ("typed", "anon", "seudo", "mask", "hash"):
        raise AnonimalError(f"Modo de anonimización inválido: {mode!r}.")
    if not text:
        return text, 0, {}
    text = _normalize(text)   # une cortes de línea de PDF antes de detectar
    merged = detect_spans(text, strict, known_pii, rules, detector_ids)
    if mode == "seudo":
        return _pseudonymize(text, merged)    # (texto, cantidad, mapa token→original)
    if mode == "mask":
        return _apply(text, merged, lambda f, ph: _mask_value(f, _TYPE_NAME.get(ph, "DATO"))), len(merged), {}
    if mode == "hash":
        return _apply(text, merged, lambda f, ph: _hash_token(f, _TYPE_NAME.get(ph, "DATO"))), len(merged), {}
    return _build(text, merged, anon=(mode == "anon")), len(merged), {}
