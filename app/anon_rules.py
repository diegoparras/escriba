"""
Reglas de anonimización PERSONALIZADAS por el usuario (Bring Your Own Rules).

El usuario sube un JSON con sus propios patrones / etiquetas / lista blanca. Es
uno de los vectores más peligrosos (regex arbitrario), así que está blindado:

- Motor **RE2** (tiempo LINEAL garantizado) → el ReDoS es imposible por diseño.
- **JSON estricto** (json.loads), nunca YAML/eval/pickle → sin RCE por deserialización.
- Topes duros: tamaño, cantidad de patrones, longitud de cada regex.
- `placeholder` validado contra una **allowlist cerrada**.
- Reglas POR USUARIO (viajan por pedido) → sin estado compartido envenenable.
- Cada patrón se compila y se valida ANTES de aplicar; si falla, se rechaza.
"""
import json

import re2

MAX_BYTES = 64 * 1024
MAX_PATTERNS = 50
MAX_REGEX_LEN = 200
MAX_LABELS = 50
MAX_KEEP = 300

# Nombre de tipo (lo que pone el usuario) → placeholder interno. Lista CERRADA:
# nada arbitrario del usuario llega a la salida.
_PH_MAP = {
    "PERSONA": "<PRIVATE_PERSON>", "ORG": "<PRIVATE_PERSON>",
    "ID": "<ACCOUNT_NUMBER>", "DOMICILIO": "<PRIVATE_ADDRESS>",
    "EMAIL": "<PRIVATE_EMAIL>", "TEL": "<PRIVATE_PHONE>",
    "FECHA": "<PRIVATE_DATE>", "SECRETO": "<SECRET>", "DATO": "<REDACTED>",
}


class AnonRulesError(Exception):
    """Reglas inválidas (se traduce a 400 en la API)."""


def parse_rules(raw):
    """Valida y compila el JSON de reglas del usuario. Devuelve dict con
    patrones RE2 compilados, etiquetas y lista blanca; o None si no hay reglas.
    Lanza AnonRulesError con un mensaje claro si algo no cumple."""
    if not raw or not str(raw).strip():
        return None
    if len(str(raw).encode("utf-8", "replace")) > MAX_BYTES:
        raise AnonRulesError("Las reglas superan el límite de 64 KB.")
    try:
        data = json.loads(raw)
    except Exception as e:  # noqa: BLE001
        raise AnonRulesError("JSON inválido: %s" % e)
    if not isinstance(data, dict):
        raise AnonRulesError("La raíz del JSON debe ser un objeto.")

    raw_patterns = data.get("patterns") or []
    if not isinstance(raw_patterns, list):
        raise AnonRulesError("'patterns' debe ser una lista.")
    if len(raw_patterns) > MAX_PATTERNS:
        raise AnonRulesError("Demasiados patrones (máx %d)." % MAX_PATTERNS)
    patterns = []
    for i, p in enumerate(raw_patterns):
        if not isinstance(p, dict):
            raise AnonRulesError("Patrón %d: debe ser un objeto." % (i + 1))
        rx = p.get("regex")
        ph = str(p.get("placeholder") or "DATO").upper()
        if not isinstance(rx, str) or not (1 <= len(rx) <= MAX_REGEX_LEN):
            raise AnonRulesError("Patrón %d: 'regex' inválido o > %d caracteres." % (i + 1, MAX_REGEX_LEN))
        if ph not in _PH_MAP:
            raise AnonRulesError("Patrón %d: placeholder '%s' no permitido." % (i + 1, ph))
        try:
            comp = re2.compile(rx)
        except Exception as e:  # noqa: BLE001 — re2 no soporta backrefs/lookbehind
            raise AnonRulesError("Patrón %d: regex no válida en RE2 (%s)." % (i + 1, e))
        patterns.append((comp, _PH_MAP[ph]))

    labels = []
    for l in (data.get("labels") or [])[:MAX_LABELS]:
        if not isinstance(l, dict):
            continue
        lab = str(l.get("label") or "").strip()
        ph = str(l.get("placeholder") or "DATO").upper()
        if lab and len(lab) <= 80 and ph in _PH_MAP:
            labels.append((lab, _PH_MAP[ph]))

    keep = []
    for k in (data.get("keep") or [])[:MAX_KEEP]:
        s = str(k).strip()
        if s:
            keep.append(s)

    if not patterns and not labels and not keep:
        raise AnonRulesError("Las reglas no tienen patrones, etiquetas ni lista blanca.")
    return {"patterns": patterns, "labels": labels, "keep": keep}


def custom_spans(text, rules):
    """Spans (start, end, placeholder) de los patrones y etiquetas del usuario.
    Todo con RE2 → lineal, sin ReDoS."""
    out = []
    if not rules:
        return out
    for comp, ph in rules["patterns"]:
        for m in comp.finditer(text):
            st, en = m.start(), m.end()
            if en > st:
                out.append({"start": st, "end": en, "placeholder": ph})
    for lab, ph in rules["labels"]:
        # "Etiqueta: valor" → enmascara el valor (hasta fin de línea), con RE2.
        try:
            lrx = re2.compile(re2.escape(lab) + r"\s*:?\s*([^\n]{1,80})")
        except Exception:  # noqa: BLE001
            continue
        for m in lrx.finditer(text):
            st, en = m.start(1), m.end(1)
            if en > st:
                out.append({"start": st, "end": en, "placeholder": ph})
    return out


def keep_set(rules):
    """Conjunto de strings que el usuario marcó como NUNCA enmascarar."""
    return set(rules["keep"]) if rules else set()
