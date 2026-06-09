"""
OCR para PDFs escaneados / con capa de texto rota (acentos LaTeX, etc.) e imágenes.

- PDFs: ocrmypdf --force-ocr (rasteriza y re-OCR) -> PDF con texto limpio.
- Imágenes: tesseract directo -> texto.

SEGURIDAD:
- Siempre se invoca con LISTA de argumentos (sin shell) => no hay inyección.
- El idioma se valida contra una allowlist (nunca se pasa texto del usuario crudo).
- Timeouts para evitar cuelgues / DoS.
"""

import os
import re
import subprocess
import tempfile

# Idiomas de tesseract instalados (allowlist). Mapea desde el código de la UI.
TESS_INSTALLED = {"spa", "eng", "por", "fra", "deu", "ita"}
_UI_TO_TESS = {
    "es-ES": "spa", "en-US": "eng", "pt-BR": "por",
    "fr-FR": "fra", "it-IT": "ita", "de-DE": "deu",
}
DEFAULT_TESS = "spa+eng"

OCR_TIMEOUT = 600  # segundos


def resolve_tess_langs(ui_lang: str | None) -> str:
    """Convierte el código de la UI (es-ES…) a códigos tesseract validados."""
    if not ui_lang or ui_lang == "auto":
        return DEFAULT_TESS
    tess = _UI_TO_TESS.get(ui_lang)
    if tess and tess in TESS_INSTALLED:
        return tess
    return DEFAULT_TESS


def _validate_langs(langs: str) -> str:
    parts = [p for p in langs.split("+") if p]
    if not parts or any(p not in TESS_INSTALLED for p in parts):
        return DEFAULT_TESS
    return "+".join(parts)


def ocr_pdf(in_path: str, langs: str) -> str:
    """OCR de un PDF -> ruta de un PDF nuevo con texto. El llamador debe borrarlo."""
    langs = _validate_langs(langs)
    out_path = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf").name
    try:
        subprocess.run(
            # --rotate-pages: detecta y corrige páginas rotadas (90/180/270) con OSD.
            #   El umbral por defecto (14) es muy conservador y deja pasar páginas
            #   claramente rotadas; 2 corrige las 4 orientaciones sin rotar de más
            #   las que ya están derechas (validado empíricamente).
            # --deskew: endereza inclinaciones leves del escaneo.
            ["ocrmypdf", "--force-ocr",
             "--rotate-pages", "--rotate-pages-threshold", "2", "--deskew",
             "--output-type", "pdf", "--optimize", "0", "-l", langs, in_path, out_path],
            check=True, capture_output=True, timeout=OCR_TIMEOUT,
        )
    except BaseException:
        # Si ocrmypdf falla o se pasa del timeout, no dejamos el temporal huérfano.
        try:
            os.unlink(out_path)
        except OSError:
            pass
        raise
    return out_path


def _detect_rotation(in_path: str) -> int:
    """Devuelve los grados (horario) a rotar la imagen para enderezarla (0/90/180/270)."""
    try:
        proc = subprocess.run(
            ["tesseract", in_path, "stdout", "--psm", "0", "-l", "osd"],
            capture_output=True, timeout=120,
        )
        out = proc.stdout.decode("utf-8", "replace") + proc.stderr.decode("utf-8", "replace")
        m = re.search(r"Rotate:\s*(\d+)", out)
        return int(m.group(1)) % 360 if m else 0
    except Exception:
        return 0


def ocr_image(in_path: str, langs: str) -> str:
    """OCR de una imagen -> texto plano. Autocorrige la orientación si está rotada."""
    langs = _validate_langs(langs)
    target = in_path
    rotated_tmp = None
    deg = _detect_rotation(in_path)
    if deg:
        try:
            from PIL import Image
            img = Image.open(in_path).convert("RGB").rotate(-deg, expand=True)  # OSD = giro horario
            rotated_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
            img.save(rotated_tmp)
            target = rotated_tmp
        except Exception:
            target = in_path
    try:
        proc = subprocess.run(
            ["tesseract", target, "stdout", "-l", langs],
            check=True, capture_output=True, timeout=OCR_TIMEOUT,
        )
        return proc.stdout.decode("utf-8", errors="replace")
    finally:
        if rotated_tmp:
            try:
                os.unlink(rotated_tmp)
            except OSError:
                pass
