"""
Exportar el Markdown de Escriba a OTROS formatos con Pandoc (el conversor
universal). Cierra el ciclo: cualquier documento → Markdown limpio → el formato
que quieras (XML DocBook/JATS/TEI/OPML, DOCX, ODT, LaTeX, EPUB, HTML, RST…).

Pandoc es un binario único (sin modelos, RAM ~0).

Seguridad / lectura de archivos locales:
  - Formatos de texto (HTML, LaTeX, RST, DocBook, JATS, TEI, OPML): corren con
    --sandbox, así Pandoc no puede leer archivos del sistema desde el Markdown.
    Además se endurece el reader a 'markdown-raw_html-raw_tex' para que el
    artefacto exportado NO arrastre HTML/LaTeX crudo del insumo (p. ej.
    <script>/<iframe file://>/\\input/\\write18) que podría dispararse en la
    máquina de quien abra el HTML o compile el .tex.
  - Formatos binarios (DOCX, ODT, EPUB): NO usan --sandbox. Este Pandoc trae los
    data files embebidos en el binario (build --embed-data-files, sin data dir en
    disco), y en modo sandbox los busca en ./data y falla con error 97 / HTTP 400.
    Para no re-romper la exportación binaria, en vez de --sandbox endurecemos el
    reader a 'markdown-raw_html-raw_tex' (descarta raw HTML y raw TeX, p. ej.
    \\input/\\include/<object>) y NO habilitamos --extract-media, evitando includes
    y resolución de rutas locales arbitrarias desde el Markdown.
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


# id → (id, writer Pandoc, extensión, binario?, mime, etiqueta)
# índices: f[0]=id  f[1]=writer  f[2]=ext  f[3]=bin?  f[4]=mime  f[5]=label
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


def convert(markdown: str, fmt_id: str, title: str | None = None):
    """Devuelve (bytes, extensión, mime). Lanza ExportError ante cualquier falla.

    ``title`` setea el metadata 'title' del documento; si es None/vacío se usa
    "Documento" (mismo comportamiento histórico).
    """
    f = _BY_ID.get(fmt_id)
    if not f:
        raise ExportError("Formato no soportado.")
    if not available():
        raise ExportError("Pandoc no está instalado en este servidor.")
    writer, ext, is_bin, mime = f[1], f[2], f[3], f[4]
    src = (markdown or "").encode("utf-8")
    doc_title = (title or "").strip() or "Documento"
    if is_bin:
        # Binarios sin --sandbox (rompería los data files embebidos del binario,
        # error 97 / HTTP 400). Mitigamos el vector de lectura de archivos locales
        # endureciendo el reader (sin raw HTML ni raw TeX) y sin --extract-media.
        reader = "markdown-raw_html-raw_tex"
    else:
        # Writers de texto: además de --sandbox, endurecemos el reader para que el
        # HTML/LaTeX exportado NO arrastre <script>/<iframe>/\input/\write18 crudos
        # del insumo (passthrough raw_html/raw_tex). Defensa para quien abra/compile
        # el artefacto, sin afectar la conversión normal de Markdown.
        reader = "markdown-raw_html-raw_tex"
    base = ["pandoc", "-f", reader, "-t", writer,
            "--standalone", "--metadata", "title=" + doc_title]
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
