"""
Extracción de texto de PDF con PyMuPDF (fitz).

MOTIVO: MarkItDown extrae PDF con pdfminer.six, que NO normaliza la rotación de
página. En hojas apaisadas —con flag /Rotate (90/270°) o con el contenido
dibujado de costado sin flag— pdfminer devuelve el texto invertido/al revés.
PyMuPDF respeta la rotación y la orientación real de los glifos, así que extrae
esas páginas correctamente (verificado empíricamente contra ambos casos).

OCR queda para PDFs ESCANEADOS (sin capa de texto); esto es para la capa de
texto electrónica.
"""
import re

import pymupdf

# Etiquetas de campos que SIEMPRE traen PII en comprobantes AFIP/ARCA, con el
# placeholder por tipo. Se recorren de la más larga a la más corta.
_LABEL_PH = {
    "apellido y nombre / razón social": "<PRIVATE_PERSON>",
    "apellido y nombre / razon social": "<PRIVATE_PERSON>",
    "razón social": "<PRIVATE_PERSON>", "razon social": "<PRIVATE_PERSON>",
    "apellido y nombre": "<PRIVATE_PERSON>",
    "denominación": "<PRIVATE_PERSON>", "denominacion": "<PRIVATE_PERSON>",
    "domicilio comercial": "<PRIVATE_ADDRESS>", "domicilio": "<PRIVATE_ADDRESS>",
    "cuit/cuil": "<ACCOUNT_NUMBER>", "cuit": "<ACCOUNT_NUMBER>",
    "cuil": "<ACCOUNT_NUMBER>", "dni": "<ACCOUNT_NUMBER>",
    "correo electrónico": "<PRIVATE_EMAIL>", "correo electronico": "<PRIVATE_EMAIL>",
    "email": "<PRIVATE_EMAIL>", "e-mail": "<PRIVATE_EMAIL>",
    "teléfono": "<PRIVATE_PHONE>", "telefono": "<PRIVATE_PHONE>",
    "cbu": "<ACCOUNT_NUMBER>", "alias": "<ACCOUNT_NUMBER>",
    "ingresos brutos": "<ACCOUNT_NUMBER>",
}
_PII_LABELS = sorted(_LABEL_PH.keys(), key=len, reverse=True)

# Marcadores de que un PDF es una factura/comprobante AFIP.
_INVOICE_HINTS = ("punto de venta", "comp. nro", "cae n", "comprobante",
                  "condición frente al iva", "condicion frente al iva", "factura")


def is_invoice(text: str) -> bool:
    low = (text or "").lower()
    return sum(h in low for h in _INVOICE_HINTS) >= 2


_COL_GAP = 45.0   # gap de x (px) que marca un salto a otra columna/campo


def _value_after_label(words, lab):
    """Si la línea empieza con `lab`, devuelve el valor: las palabras a la derecha
    de la etiqueta, cortando en el primer salto de columna (gap de x grande)."""
    toks = [w[4] for w in words]
    for take in range(1, len(toks) + 1):
        prefix = " ".join(toks[:take]).lower().strip().rstrip(":").strip()
        if prefix == lab.rstrip(":"):
            val_words = []
            prev_x1 = words[take - 1][2]
            for w in words[take:]:
                if w[0] - prev_x1 > _COL_GAP:   # otra columna → cortar
                    break
                val_words.append(w[4])
                prev_x1 = w[2]
            return " ".join(val_words).strip()
        if len(prefix) > len(lab) + 2:
            break
    return None


def _lines_ycluster(words):
    """Renglones agrupando por y (clúster). Une etiqueta+valor de bloques
    distintos a la misma altura (caso del bloque EMISOR)."""
    recs = []
    for w in sorted(words, key=lambda w: (w[1], w[0])):
        if recs and abs(w[1] - recs[-1]["y"]) <= 1.8:
            recs[-1]["ws"].append(w)
        else:
            recs.append({"y": w[1], "ws": [w]})
    for r in recs:
        r["ws"].sort(key=lambda w: w[0])
        r["text"] = " ".join(w[4] for w in r["ws"])
    return recs


def _lines_block(words):
    """Renglones agrupando por (bloque, línea) de PyMuPDF (caso del bloque
    RECEPTOR, donde etiqueta y valor caen en el mismo bloque)."""
    groups = {}
    for w in words:
        groups.setdefault((w[5], w[6]), []).append(w)
    recs = []
    for ws in groups.values():
        ws = sorted(ws, key=lambda w: w[0])
        recs.append({"y": sum(w[1] for w in ws) / len(ws), "ws": ws,
                     "text": " ".join(w[4] for w in ws)})
    recs.sort(key=lambda r: r["y"])
    return recs


def _scan_labels(recs):
    out = []
    for idx, rec in enumerate(recs):
        low = rec["text"].lower().strip()
        for lab in _PII_LABELS:
            if low.startswith(lab):
                val = _value_after_label(rec["ws"], lab)
                if not val and idx + 1 < len(recs):
                    nxt = recs[idx + 1]["text"].strip()
                    if not any(nxt.lower().startswith(l) for l in _PII_LABELS):
                        val = nxt
                if val and len(val.strip()) >= 2:
                    out.append((val.strip(), _LABEL_PH[lab]))
                break
    return out


def invoice_field_values(path: str):
    """Valores de los campos PII de un comprobante (emisor y receptor), por
    asociación etiqueta→valor con coordenadas. Corre DOS estrategias de armado
    de renglón (clúster por y y por bloque) y une, porque emisor y receptor
    suelen tener layouts distintos. Devuelve strings a enmascarar."""
    doc = pymupdf.open(path)
    out = []
    try:
        for page in doc:
            words = page.get_text("words")  # (x0,y0,x1,y1,word,block,line,wordno)
            out += _scan_labels(_lines_ycluster(words))
            out += _scan_labels(_lines_block(words))
        seen, uniq = set(), []
        for val, ph in out:
            if val not in seen:
                seen.add(val); uniq.append((val, ph))
        return uniq   # lista de (valor, placeholder)
    finally:
        doc.close()


def page_marker(n: int, label: str = "Página") -> str:
    """Marcador de página: ancla máquina-legible (para RAG/citas del LLM) + línea
    visible para el humano. NO usa encabezado Markdown (`##`) a propósito, para no
    contaminar la jerarquía de títulos real del documento. El ancla `page:N` es
    única para PDF y PPTX, así un solo regex `<!-- page:(\\d+) -->` las cita a todas."""
    return f"<!-- page:{n} -->\n**{label} {n}**"


def extract_pdf_text(path: str, mark_pages: bool = False, page_numbers=None) -> str:
    """Devuelve el texto del PDF respetando la rotación de cada página.

    Si `mark_pages` es True, antepone a cada página su marcador (ancla + `**Página N**`).
    `page_numbers` permite pasar la numeración ORIGINAL del PDF (1-based) cuando el
    documento fue recortado a un subconjunto: así el marcador cita la página real del
    archivo, no la posición dentro del recorte. Si no viene, se numera 1..N."""
    doc = pymupdf.open(path)
    try:
        parts = []
        for idx, page in enumerate(doc):
            txt = page.get_text("text").strip()
            if not txt:
                continue
            if mark_pages:
                num = page_numbers[idx] if page_numbers and idx < len(page_numbers) else idx + 1
                parts.append(f"{page_marker(num)}\n\n{txt}")
            else:
                parts.append(txt)
        return "\n\n".join(parts).strip()
    finally:
        doc.close()


def pdf_title(path: str):
    """Título de la metadata del PDF, si tiene. None si no."""
    try:
        doc = pymupdf.open(path)
        try:
            t = (doc.metadata or {}).get("title")
            t = (t or "").strip()
            return t or None
        finally:
            doc.close()
    except Exception:
        return None
