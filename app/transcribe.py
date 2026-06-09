"""
Transcripción de audio y video con faster-whisper (local, offline).

- Extrae el audio con ffmpeg (16 kHz mono) y lo transcribe con Whisper.
- Usa el idioma elegido por el usuario (o autodetección).
- El modelo se carga una sola vez (singleton) y se reusa entre requests.
"""

import os
import subprocess
import tempfile
import threading

WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")   # tiny/base/small/medium/large-v3
WHISPER_COMPUTE = os.getenv("WHISPER_COMPUTE", "int8")
EXTRACT_TIMEOUT = int(os.getenv("EXTRACT_TIMEOUT", "1800"))

_model = None
_lock = threading.Lock()

AUDIO_EXTS = {"mp3", "wav", "m4a", "flac", "ogg", "aac", "opus", "wma"}
VIDEO_EXTS = {"mp4", "mov", "mkv", "webm", "avi", "m4v", "mpeg", "mpg", "wmv", "flv", "3gp"}


def _get_model():
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                from faster_whisper import WhisperModel
                _model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type=WHISPER_COMPUTE)
    return _model


def probe_duration(in_path: str):
    """Duración del medio en segundos (vía ffprobe). None si no se puede leer."""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", in_path],
            check=True, capture_output=True, timeout=60,
        ).stdout.decode().strip()
        return float(out)
    except Exception:
        return None


def _extract_audio(in_path: str) -> str:
    """Extrae el audio a WAV 16 kHz mono con ffmpeg."""
    out = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", in_path, "-vn", "-ac", "1", "-ar", "16000", "-f", "wav", out],
            check=True, capture_output=True, timeout=EXTRACT_TIMEOUT,
        )
    except BaseException:
        try:
            os.unlink(out)
        except OSError:
            pass
        raise
    return out


def transcribe_media(in_path: str, lang=None):
    """Devuelve (texto, idioma_detectado). El llamador ya borra in_path."""
    wav = _extract_audio(in_path)
    try:
        model = _get_model()
        language = lang.split("-")[0] if (lang and lang != "auto") else None
        segments, info = model.transcribe(wav, language=language, beam_size=5)
        text = " ".join(s.text.strip() for s in segments if s.text).strip()
        return text, getattr(info, "language", None)
    finally:
        try:
            os.unlink(wav)
        except OSError:
            pass
