"""
Extracción AVANZADA de PDF con OpenDataLoader (Hancom): reconstruye la
estructura del documento — jerarquía de títulos, orden de lectura (multicolumna
con XY-Cut++), listas y tablas — y devuelve Markdown limpio.

Es determinístico y sin GPU, pero corre sobre una JVM (Java) y arranca el motor
por cada conversión, así que es OPT-IN (el usuario lo activa cuando lo necesita).
DESACTIVADO si no están Java + el paquete (available() = False).
"""
import glob
import logging
import os
import shutil
import tempfile

log = logging.getLogger("markitdown.odl")


class ODLError(Exception):
    """Falla en la extracción avanzada."""


def available() -> bool:
    try:
        import opendataloader_pdf  # noqa: F401
    except Exception:  # noqa: BLE001
        return False
    return shutil.which("java") is not None


def extract_markdown(pdf_path: str) -> str:
    """Markdown estructurado del PDF. Lanza ODLError si falla (el llamador puede
    caer a la extracción clásica con PyMuPDF)."""
    import opendataloader_pdf as odl
    out = tempfile.mkdtemp(prefix="odl_")
    try:
        # content_safety (anti prompt-injection) se pasa EXPLÍCITO, sin depender
        # del default de la librería, ya que el PDF es contenido no confiable.
        odl.convert(
            input_path=pdf_path,
            output_dir=out,
            format="markdown",
            quiet=True,
            content_safety=True,
        )
        mds = sorted(glob.glob(os.path.join(out, "**", "*.md"), recursive=True))
        if not mds:
            raise ODLError("OpenDataLoader no generó Markdown.")
        with open(mds[0], encoding="utf-8") as fh:
            text = fh.read()
        if not text.strip():
            raise ODLError("La extracción avanzada quedó vacía.")
        return text
    except ODLError:
        raise
    except Exception as e:  # noqa: BLE001
        log.warning("OpenDataLoader falló: %s", e)
        raise ODLError("La extracción avanzada falló.") from e
    finally:
        _cleanup_dir(out)


def _cleanup_dir(path: str) -> None:
    """Borra un tempdir de ODL; loguea (sin propagar) si la limpieza falla."""
    def _onerror(_func, errpath, exc_info):
        log.warning("No se pudo limpiar el tempdir ODL %s: %s", errpath, exc_info[1])

    try:
        shutil.rmtree(path, onerror=_onerror)
    except Exception as e:  # noqa: BLE001
        log.warning("No se pudo limpiar el tempdir ODL %s: %s", path, e)


def cleanup_orphans() -> None:
    """Borra tempdirs 'odl_*' huérfanos que hayan quedado de corridas previas
    (p.ej. tras un crash). Seguro de llamar al arranque del proceso."""
    pattern = os.path.join(tempfile.gettempdir(), "odl_*")
    for orphan in glob.glob(pattern):
        if os.path.isdir(orphan):
            _cleanup_dir(orphan)
