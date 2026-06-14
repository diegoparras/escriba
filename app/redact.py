"""
Redacción VISUAL de PII: tacha los datos personales SOBRE el documento
(PDF o imagen escaneada) y devuelve un PDF censurado.

Usa la MISMA detección que la anonimización de texto (Anonimal/OPF +
detectores built-in + reglas RE2 del usuario) y PyMuPDF para aplicar
REDACCIÓN REAL: `apply_redactions` elimina el texto subyacente del PDF y
pinta de negro los píxeles de imagen bajo cada rectángulo. No es un dibujo
encima: el dato deja de existir en el archivo resultante.

Sin dependencias nuevas: PyMuPDF y Tesseract/ocrmypdf ya están en la imagen.
"""
import logging

import fitz  # PyMuPDF

from . import anonimal
from . import pdf_extract

log = logging.getLogger("markitdown.redact")

# Separador entre páginas: detectamos el documento ENTERO en un solo pase de
# Anonimal (una llamada HTTP) y después repartimos los spans por página.
_PAGE_SEP = "\n\f\n"


class RedactError(Exception):
    """Falla al censurar (sin texto, sin servicio, etc.)."""


def image_to_pdf(img_path: str, out_path: str) -> str:
    """Convierte una imagen a PDF de una página (sin capa de texto aún)."""
    with fitz.open(img_path) as img:
        pdf_bytes = img.convert_to_pdf()
    with open(out_path, "wb") as fh:
        fh.write(pdf_bytes)
    return out_path


def has_text(path: str) -> bool:
    """True si el PDF ya tiene capa de texto utilizable."""
    try:
        return len((pdf_extract.extract_pdf_text(path) or "").strip()) >= 30
    except Exception:  # noqa: BLE001
        return False


def _extract(path):
    """(doc, pages, full): abre el PDF y arma, por página, las palabras con su
    bounding box + el texto unido con su mapeo offset→caja. Cierra el llamador."""
    doc = fitz.open(path)
    pages = []   # (words, page_text, offsets[(start,end)])
    for page in doc:
        words = page.get_text("words")   # [x0,y0,x1,y1, palabra, ...]
        offs, parts, pos = [], [], 0
        for w in words:
            parts.append(w[4])
            offs.append((pos, pos + len(w[4])))
            pos += len(w[4]) + 1   # +1 por el espacio separador
        pages.append((words, " ".join(parts), offs))
    full = _PAGE_SEP.join(p[1] for p in pages)
    return doc, pages, full


def _detect(path, full, strict, rules, detector_ids):
    """Detección unificada (OPF + detectores + layout de comprobante + reglas)."""
    known = []
    if pdf_extract.is_invoice(full):
        known = pdf_extract.invoice_field_values(path)
    return anonimal.detect_spans(full, strict=strict, known_pii=known,
                                 rules=rules, detector_ids=detector_ids)


def entities_pdf(path: str, strict: bool = False, rules=None, detector_ids=None):
    """VISTA PREVIA: lista (deduplicada) de lo que se TACHARÍA, sin generar el
    PDF. Devuelve [{text, type, count}] ordenado por frecuencia. Falla segura."""
    doc, _pages, full = _extract(path)
    try:
        if not full.strip():
            raise RedactError("El documento no tiene texto detectable (¿escaneado sin OCR?).")
        spans = _detect(path, full, strict, rules, detector_ids)
        agg = {}
        for s in spans:
            txt = full[s["start"]:s["end"]].strip()
            if not txt:
                continue
            typ = anonimal._TYPE_NAME.get(s["placeholder"], "DATO")
            key = (txt.lower(), typ)
            if key in agg:
                agg[key]["count"] += 1
            else:
                agg[key] = {"text": txt, "type": typ, "count": 1}
        return sorted(agg.values(), key=lambda x: (-x["count"], x["text"].lower()))[:300]
    finally:
        doc.close()


def redact_pdf(path: str, strict: bool = False, rules=None, detector_ids=None, only=None):
    """
    Censura visualmente el PDF en `path`. Devuelve (pdf_bytes, entidades).
    El PDF debe tener capa de texto (electrónico u OCR aplicado antes).
    - only: si es una lista de textos, SOLO se tachan esos (los que el usuario
      dejó tildados en el modal de selección). None = tachar todo lo detectado.
    Falla SEGURA: ante cualquier error lanza RedactError; jamás devuelve el
    documento original como si estuviera censurado.
    """
    doc, pages, full = _extract(path)
    try:
        if not full.strip():
            raise RedactError("El documento no tiene texto detectable (¿escaneado sin OCR?).")
        spans = _detect(path, full, strict, rules, detector_ids)
        if only is not None:
            keep = {str(x).strip().lower() for x in only}
            spans = [s for s in spans if full[s["start"]:s["end"]].strip().lower() in keep]

        # Repartir spans por página y tachar las palabras que tocan.
        entities = 0
        base = 0
        for pi, (words, ptext, offs) in enumerate(pages):
            lo, hi = base, base + len(ptext)
            page_rects = []
            for s in spans:
                if s["end"] <= lo or s["start"] >= hi:
                    continue
                ps, pe = max(s["start"] - lo, 0), min(s["end"] - lo, len(ptext))
                hit = False
                for (ws, we), w in zip(offs, words):
                    if ws < pe and we > ps:   # la palabra solapa el span PII
                        page_rects.append(fitz.Rect(w[0], w[1], w[2], w[3]))
                        hit = True
                if hit:
                    entities += 1
            if page_rects:
                page = doc[pi]
                for r in page_rects:
                    # Margen mínimo para cubrir antialiasing del render.
                    r.x0 -= 1; r.y0 -= 1; r.x1 += 1; r.y1 += 1
                    page.add_redact_annot(r, fill=(0, 0, 0))
                # REDACCIÓN REAL: borra el texto y ennegrece los píxeles
                # de las imágenes debajo de cada rectángulo.
                page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_PIXELS)
            base = hi + len(_PAGE_SEP)

        out = doc.tobytes(garbage=3, deflate=True)
        return out, entities
    finally:
        doc.close()
