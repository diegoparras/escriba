"""
Registro de DETECTORES de PII. Cada uno tiene `id`, grupo y un on/off por
defecto. El usuario (por navegador) enciende/apaga los que quiera —distintos
usuarios, distintas configs— y eso viaja por pedido.

Grupos:
- universal: agnósticos de país. Incluye TARJETA (validada con Luhn) e IBAN
  (validado con mod-97) — checksums que una regex de plantilla NO puede hacer.
- regional: formatos argentinos (CUIT/CUIL/CBU/DNI/domicilio/razón social…).
- strict: heurísticas agresivas (números largos, secuencias en mayúscula).
  Por defecto APAGADAS; las prende el modo Estricto o el usuario.

Los patrones built-in son de confianza (los escribimos nosotros) → se usan con
el módulo `re`. Los del USUARIO van por RE2 (ver anon_rules.py).
"""
import re

PERSON = "<PRIVATE_PERSON>"
ACCOUNT = "<ACCOUNT_NUMBER>"
ADDRESS = "<PRIVATE_ADDRESS>"
EMAIL = "<PRIVATE_EMAIL>"
PHONE = "<PRIVATE_PHONE>"
URL = "<PRIVATE_URL>"


# --- validadores por checksum (lo que la plantilla de regex no puede hacer) ---
def _luhn_ok(s):
    ds = [int(c) for c in s if c.isdigit()]
    if not (13 <= len(ds) <= 19):
        return False
    tot, alt = 0, False
    for d in reversed(ds):
        if alt:
            d *= 2
            if d > 9:
                d -= 9
        tot += d
        alt = not alt
    return tot % 10 == 0


def _gen_cards(text):
    for m in re.finditer(r"\b\d(?:[ -]?\d){12,18}\b", text):
        if _luhn_ok(m.group(0)):
            yield m.span()


def _iban_ok(s):
    s = re.sub(r"\s", "", s).upper()
    if not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{10,30}", s):
        return False
    rearr = s[4:] + s[:4]
    try:
        num = "".join(str(ord(c) - 55) if c.isalpha() else c for c in rearr)
        return int(num) % 97 == 1
    except ValueError:
        return False


def _gen_iban(text):
    for m in re.finditer(r"\b[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]{2,4}){2,8}\b", text):
        if _iban_ok(m.group(0)):
            yield m.span()


# --- secuencias en mayúscula tipo nombre (con lista blanca estructural) -------
_KEEP = {
    "factura", "original", "duplicado", "triplicado", "responsable", "monotributo",
    "iva", "exento", "sujeto", "subtotal", "importe", "total", "otros", "tributos",
    "producto", "servicio", "cantidad", "precio", "unitario", "bonif", "codigo",
    "punto", "venta", "comp", "nro", "fecha", "emision", "periodo", "facturado",
    "desde", "hasta", "vto", "pago", "condicion", "frente", "transferencia",
    "bancaria", "cae", "comprobante", "autorizado", "agencia", "pesos", "argentinos",
    "moneda", "dolar", "estadounidense", "usd", "etapa", "proyecto", "web",
    "ciudad", "autonoma", "buenos", "aires", "provincia", "neuquen", "medida",
    "consejo", "profesional", "ciencias", "economicas", "anticipo", "contrato",
    "primera", "segunda", "tercera", "cuarta", "quinta", "objeto", "plazo",
    "honorarios", "confidencialidad", "domicilios", "jurisdiccion",
}


def _strip_acc(s):
    return s.lower().strip(".:,;").translate(str.maketrans("áéíóúñ", "aeioun"))


def _gen_caps(text):
    rx = re.compile(r"\b([A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ.]+(?:\s+(?:de|del|la|y|[A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ.]+)){1,5})\b")
    for m in rx.finditer(text):
        toks = [t for t in re.split(r"\s+", m.group(0)) if t.lower() not in ("de", "del", "la", "y")]
        if toks and all(_strip_acc(t) in _KEEP for t in toks):
            continue
        yield m.span()


class Det:
    def __init__(self, id, group, label, placeholder, default, regex=None, gi=0, flags=0, gen=None):
        self.id = id
        self.group = group
        self.label = label
        self.placeholder = placeholder
        self.default = default
        self.gi = gi
        self.gen = gen
        self.regex = re.compile(regex, flags) if regex else None

    def spans(self, text):
        out = []
        if self.gen:
            for a, b in self.gen(text):
                if b > a:
                    out.append({"start": a, "end": b, "placeholder": self.placeholder})
        else:
            for m in self.regex.finditer(text):
                a, b = m.span(self.gi)
                if b > a:
                    out.append({"start": a, "end": b, "placeholder": self.placeholder})
        return out


DETECTORS = [
    # ── universales ──────────────────────────────────────────────────────────
    Det("email", "universal", "Email", EMAIL, True, regex=r"[\w.+\-]+@[\w\-]+\.[\w.\-]+"),
    Det("credit_card", "universal", "Credit card (Luhn)", ACCOUNT, True, gen=_gen_cards),
    Det("iban", "universal", "IBAN (mod-97)", ACCOUNT, True, gen=_gen_iban),
    Det("phone_intl", "universal", "Phone number", PHONE, False, regex=r"(?<![\d.])\+?\d[\d\s().\-]{7,}\d(?![\d.])"),
    Det("url", "universal", "URL", URL, False, regex=r"https?://[^\s)>\]\"']+"),
    Det("ipv4", "universal", "IPv4 address", ACCOUNT, False, regex=r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    Det("ipv6", "universal", "IPv6 address", ACCOUNT, False, regex=r"\b(?:[A-Fa-f0-9]{1,4}:){4,7}[A-Fa-f0-9]{1,4}\b"),
    Det("mac", "universal", "MAC address", ACCOUNT, False, regex=r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b"),
    # ── regionales (Argentina) ───────────────────────────────────────────────
    Det("cuit", "regional", "CUIT/CUIL (con guiones)", ACCOUNT, True, regex=r"\b\d{2}-\s*\d{8}-\s*\d\b"),
    Det("cuit_plain", "regional", "CUIT/CUIL (11 dígitos)", ACCOUNT, True, regex=r"\b\d{11}\b"),
    Det("cbu", "regional", "CBU (22 dígitos)", ACCOUNT, True, regex=r"\b\d{22}\b"),
    Det("cuit_label", "regional", "CUIT/CUIL tras etiqueta", ACCOUNT, True,
        regex=r"(?i)\b(?:CUIT|CUIL)\b[\s:.\-N°/]*?(\d{2}[-\s]*\d{8}[-\s]*\d)", gi=1),
    Det("dni_label", "regional", "DNI tras etiqueta", ACCOUNT, True,
        regex=r"(?i)\bDNI\b[\s:.\-N°/]*?(\d{1,3}(?:\.\d{3})+|\d{7,8})\b", gi=1),
    Det("account_label", "regional", "Cuenta / Caja de ahorro", ACCOUNT, True,
        regex=r"(?i)\b(?:caja de ahorro|cuenta(?: corriente)?)\b[\s:.\-]*N?[°ºo.]*\s*(\d[\d.\-/]*(?:\s+[\d.\-/]+)*)", gi=1),
    Det("alias", "regional", "Alias bancario", ACCOUNT, True,
        regex=r"(?i)\balias\b[\s:.\-]*([A-Z0-9][A-Z0-9.\-_]{3,})", gi=1),
    Det("address_ar", "regional", "Domicilio (Av./Calle/Pasaje)", ADDRESS, True,
        regex=r"(?i)\b(?:av|avda|avenida|calle|pasaje|diag|diagonal|ruta|bv|boulevard|bulevar)\b\.?[ \t]+[^,;]{1,40}?\d{1,5}\b"),
    Det("address_piso", "regional", "Domicilio (Piso/Dpto)", ADDRESS, True,
        regex=r"(?i)\b([A-Za-zÁÉÍÓÚáéíóúÑñ][^\n]{1,38}?\d{1,4}\s+Piso:?\s*\d+(?:\s+Dpto:?\s*\w+)?)", gi=1),
    Det("razon_social", "regional", "Nombre tras 'Razón Social'", PERSON, True,
        regex=r"[Rr]az[oó]n [Ss]ocial\s*:?\s*\n\s*([A-ZÁÉÍÓÚÑ]{2,}(?:\s+[A-ZÁÉÍÓÚÑ.]+)+)", gi=1),
    # ── estructurales / agresivos (default OFF; los prende Estricto) ──────────
    Det("long_id", "strict", "Números largos (7+ dígitos)", ACCOUNT, False, regex=r"\b\d{7,}\b"),
    Det("caps_names", "strict", "Secuencias en mayúscula (nombres)", PERSON, False, gen=_gen_caps),
]


def catalog():
    """Lista de detectores para que la UI dibuje los checkboxes."""
    return [{"id": d.id, "group": d.group, "label": d.label, "default": d.default} for d in DETECTORS]


def run(text, enabled_ids=None, strict=False):
    """Spans de los detectores ACTIVOS. Si enabled_ids es None, usa los defaults
    (+ los 'strict' si strict=True)."""
    if enabled_ids is None:
        active = [d for d in DETECTORS if d.default or (strict and d.group == "strict")]
    else:
        ids = set(enabled_ids)
        active = [d for d in DETECTORS if d.id in ids]
    spans = []
    for d in active:
        spans += d.spans(text)
    return spans
