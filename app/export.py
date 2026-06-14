"""
Exportar el Markdown de Escriba a OTROS formatos con Pandoc (el conversor
universal). Cierra el ciclo: cualquier documento → Markdown limpio → el formato
que quieras (XML DocBook/JATS/TEI/OPML, DOCX, ODT, LaTeX, EPUB, HTML, RST…).

Pandoc es un binario único (sin modelos, RAM ~0). Lo corremos con --sandbox para
que no pueda leer archivos del sistema desde el Markdown.
"""
import logging
import os
import shutil
import subprocess
import tempfile

log = logging.getLogger("markitdown.export")

_TIMEOUT = 60  # segundos


class ExportError(Exception):
    """Falla al exportar (formato inválido, Pandoc ausente o error de conversión)."""


# id → (writer Pandoc, extensión, binario?, mime, etiqueta)
_FORMATS = [
    ("docx",    "docx",      "docx", True,  "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "Word (.docx)"),
    ("odt",     "odt",       "odt",  True,  "application/vnd.oasis.opendocument.text", "OpenDocument (.odt)"),
    ("html",    "html5",     "html", False, "text/html; charset=utf-8", "HTML"),
    ("latex",   "latex",     "tex",  False, "application/x-tex; charset=utf-8", "LaTeX"),
    ("rst",     "rst",       "rst",  False, "text/x-rst; charset=utf-8", "reStructuredText"),
    ("docbook", "docbook5",  "xml",  False, "application/xml; charset=utf-8", "DocBook XML"),
    ("jats",    "jats",      "xml",  False, "application/xml; charset=utf-8", "JATS XML"),
    ("tei",     "tei",       "xml",  False, "application/xml; charset=utf-8", "TEI XML"),
    ("opml",    "opml",      "opml", False, "application/xml; charset=utf-8", "OPML"),
    ("epub",    "epub",      "epub", True,  "application/epub+zip", "EPUB"),
]
_BY_ID = {f[0]: f for f in _FORMATS}


def available() -> bool:
    return shutil.which("pandoc") is not None


def catalog():
    return [{"id": f[0], "ext": f[2], "label": f[5]} for f in _FORMATS]


def convert(markdown: str, fmt_id: str):
    """Devuelve (bytes, extensión, mime). Lanza ExportError ante cualquier falla."""
    f = _BY_ID.get(fmt_id)
    if not f:
        raise ExportError("Formato no soportado.")
    if not available():
        raise ExportError("Pandoc no está instalado en este servidor.")
    writer, ext, is_bin, mime = f[1], f[2], f[3], f[4]
    src = (markdown or "").encode("utf-8")
    base = ["pandoc", "-f", "markdown", "-t", writer,
            "--standalone", "--metadata", "title=Documento"]
    # --sandbox da seguridad (no lee archivos del sistema desde el Markdown) pero
    # bloquea los data files internos de Pandoc que DOCX/ODT/EPUB necesitan.
    if not is_bin:
        base.insert(1, "--sandbox")
    try:
        if is_bin:
            # DOCX/ODT/EPUB no salen por stdout: a archivo temporal.
            with tempfile.NamedTemporaryFile(suffix="." + ext, delete=False) as tmp:
                out_path = tmp.name
            try:
                subprocess.run(base + ["-o", out_path], input=src, capture_output=True,
                               timeout=_TIMEOUT, check=True)
                with open(out_path, "rb") as fh:
                    data = fh.read()
            finally:
                try:
                    os.unlink(out_path)
                except OSError:
                    pass
        else:
            r = subprocess.run(base, input=src, capture_output=True,
                               timeout=_TIMEOUT, check=True)
            data = r.stdout
    except subprocess.TimeoutExpired as e:
        raise ExportError("La exportación tardó demasiado.") from e
    except subprocess.CalledProcessError as e:
        msg = (e.stderr or b"").decode("utf-8", "replace")[:200]
        log.warning("Pandoc falló (%s): %s", fmt_id, msg)
        raise ExportError("Pandoc no pudo generar el formato pedido.") from e
    if not data:
        raise ExportError("La exportación quedó vacía.")
    return data, ext, mime
