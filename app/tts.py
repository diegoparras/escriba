"""
Texto → audio (TTS) para Escriba. Cierra el otro ciclo: documento → Markdown
limpio → MP3 ("escuchá tu documento" / podcast).

Dos motores:
  - Piper (LOCAL, offline): binario único + modelos de voz horneados en la imagen.
    El texto NUNCA sale del servidor. Es el motor por defecto.
  - OpenAI TTS (CLOUD, opcional): mejor calidad; usa la API key del usuario, el
    texto va a OpenAI (solo si el usuario lo elige, igual que la IA opcional).

Dos modos:
  - Narración: una voz lee el documento.
  - Podcast: una IA arma un guion de diálogo entre 2 voces (A/B) y se sintetiza
    alternando voces; los segmentos se concatenan con ffmpeg.

Tono / velocidad / volumen se aplican con ffmpeg (ya viene en la imagen):
  - velocidad → atempo
  - tono      → asetrate + aresample + atempo (compensa el tempo)
  - volumen   → volume
"""
from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import tempfile

log = logging.getLogger("markitdown.tts")

# --- Config (env) ------------------------------------------------------------
ENABLE_TTS = os.getenv("ENABLE_TTS", "true").lower() in ("1", "true", "yes", "on")
PIPER_BIN = os.getenv("PIPER_BIN", "/opt/piper/piper")
PIPER_VOICES_DIR = os.getenv("PIPER_VOICES_DIR", "/opt/piper-voices")
TTS_TIMEOUT = int(os.getenv("TTS_TIMEOUT", "600"))
TTS_MAX_CHARS = int(os.getenv("TTS_MAX_CHARS", "8000"))
OPENAI_TTS_MODEL = os.getenv("TTS_OPENAI_MODEL", "tts-1")
OPENAI_TTS_CHUNK = 3800  # límite de la API ~4096 char por request

SR = 22050  # los modelos Piper suelen ser 22.05 kHz

_LANG_NAMES = {
    "es": "Español", "en": "English", "pt": "Português", "fr": "Français",
    "it": "Italiano", "de": "Deutsch", "zh": "中文", "ja": "日本語",
    "ca": "Català", "nl": "Nederlands", "ru": "Русский",
}
# Pistas de género por voz Piper (m/f); si falta, se marca neutra ("n").
_PIPER_GENDER = {
    "es_ES-sharvard": "f", "es_ES-davefx": "m", "es_ES-mls_10246": "f",
    "es_MX-claude": "f", "es_MX-ald": "m",
    "en_US-amy": "f", "en_US-lessac": "f", "en_US-hfc_female": "f",
    "en_US-ryan": "m", "en_US-joe": "m", "en_US-hfc_male": "m",
    "en_GB-alba": "f", "en_GB-alan": "m", "en_GB-cori": "f",
    "pt_BR-faber": "m", "pt_BR-edresson": "m", "pt_PT-tugão": "m",
    "fr_FR-siwis": "f", "fr_FR-upmc": "f", "fr_FR-tom": "m", "fr_FR-gilles": "m",
    "it_IT-riccardo": "m", "it_IT-paola": "f",
    "de_DE-thorsten": "m", "de_DE-eva_k": "f", "de_DE-kerstin": "f", "de_DE-ramona": "f",
    "zh_CN-huayan": "f",
    "ja_JP-test": "n",
}

# Voces de OpenAI TTS (multilingüe; el idioma sale del texto).
_OPENAI_VOICES = [
    ("alloy", "n"), ("echo", "m"), ("fable", "m"),
    ("onyx", "m"), ("nova", "f"), ("shimmer", "f"),
]

# Presets de los controles (estilo Zamzar) → factores numéricos.
_SPEED = {"slow": 0.8, "normal": 1.0, "fast": 1.25, "veryfast": 1.5}
_PITCH = {"low": 0.92, "medium": 1.0, "high": 1.10}
_VOLUME = {"low": 0.6, "medium": 1.0, "high": 1.6}


class TtsError(Exception):
    """Falla de síntesis (motor ausente, voz inválida, texto vacío, etc.)."""


# --- Disponibilidad / catálogo ----------------------------------------------
def piper_available() -> bool:
    return ENABLE_TTS and os.path.isfile(PIPER_BIN) and os.path.isdir(PIPER_VOICES_DIR)


def _piper_models() -> dict:
    """{voice_id: ruta .onnx} de lo realmente horneado en la imagen."""
    out = {}
    if not os.path.isdir(PIPER_VOICES_DIR):
        return out
    for root, _dirs, files in os.walk(PIPER_VOICES_DIR):
        for fn in files:
            if fn.endswith(".onnx"):
                vid = fn[:-5]  # ej. es_ES-sharvard-medium
                out[vid] = os.path.join(root, fn)
    return out


def catalog(openai_ok: bool = False) -> list:
    """Voces disponibles para el front. `openai_ok`=True agrega las cloud."""
    voices = []
    for vid, _path in sorted(_piper_models().items()):
        locale = vid.split("-")[0]            # es_ES
        lang = locale.split("_")[0]           # es
        base = "-".join(vid.split("-")[:2])   # es_ES-sharvard
        gender = _PIPER_GENDER.get(base, "n")
        name = vid.split("-")[1] if "-" in vid else vid
        voices.append({
            "id": "piper:" + vid,
            "engine": "piper",
            "lang": lang,
            "gender": gender,
            "label": f"{_LANG_NAMES.get(lang, lang)} · {name.capitalize()}",
        })
    if openai_ok:
        for vname, gender in _OPENAI_VOICES:
            voices.append({
                "id": "openai:" + vname,
                "engine": "openai",
                "lang": "multi",
                "gender": gender,
                "label": f"OpenAI · {vname.capitalize()}",
            })
    return voices


# --- ffmpeg helpers ----------------------------------------------------------
def _afilter(pitch: str, speed: str, volume: str) -> str:
    p = _PITCH.get((pitch or "medium").lower(), 1.0)
    s = _SPEED.get((speed or "normal").lower(), 1.0)
    v = _VOLUME.get((volume or "medium").lower(), 1.0)
    parts = []
    if abs(p - 1.0) > 1e-3:
        # subir/bajar el sample rate cambia el tono; aresample lo normaliza y
        # atempo compensa el cambio de duración que introdujo asetrate.
        parts.append(f"asetrate={SR}*{p:.4f}")
        parts.append(f"aresample={SR}")
        parts.append(f"atempo={1.0/p:.4f}")
    if abs(s - 1.0) > 1e-3:
        parts.append(f"atempo={s:.4f}")     # atempo válido entre 0.5 y 2.0
    if abs(v - 1.0) > 1e-3:
        parts.append(f"volume={v:.4f}")
    return ",".join(parts)


def _encode_mp3(in_path: str, pitch: str, speed: str, volume: str) -> bytes:
    """Toma un WAV/PCM y devuelve MP3 (con tono/velocidad/volumen aplicados)."""
    out = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
    cmd = ["ffmpeg", "-y", "-i", in_path]
    af = _afilter(pitch, speed, volume)
    if af:
        cmd += ["-af", af]
    cmd += ["-codec:a", "libmp3lame", "-q:a", "4", out]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=TTS_TIMEOUT)
        with open(out, "rb") as fh:
            return fh.read()
    except subprocess.CalledProcessError as e:
        msg = (e.stderr or b"").decode("utf-8", "replace")[:200]
        log.warning("ffmpeg MP3 falló: %s", msg)
        raise TtsError("No se pudo codificar el audio.") from e
    finally:
        try:
            os.unlink(out)
        except OSError:
            pass


def _concat_wavs_to_mp3(wavs: list, pitch: str, speed: str, volume: str,
                        gap: float = 0.4) -> bytes:
    """Concatena varios WAV (con un silencio entre cada uno) → MP3."""
    if not wavs:
        raise TtsError("Nada para concatenar.")
    if len(wavs) == 1:
        return _encode_mp3(wavs[0], pitch, speed, volume)
    out = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
    # filtro: [0][silence][1][silence]... concat
    inputs = []
    for w in wavs:
        inputs += ["-i", w]
    n = len(wavs)
    fc = []
    streams = ""
    for i in range(n):
        streams += f"[{i}:a]"
        if i < n - 1:
            # inserta un silencio corto generado con anullsrc entre segmentos
            pass
    # más simple y robusto: concat directo (sin silencio extra) y dejamos que
    # cada segmento ya traiga su pausa natural; el gap se agrega con apad.
    filt = "".join(f"[{i}:a]" for i in range(n)) + f"concat=n={n}:v=0:a=1[a]"
    af = _afilter(pitch, speed, volume)
    if af:
        filt += f";[a]{af}[out]"
        amap = "[out]"
    else:
        amap = "[a]"
    cmd = ["ffmpeg", "-y"] + inputs + ["-filter_complex", filt,
           "-map", amap, "-codec:a", "libmp3lame", "-q:a", "4", out]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=TTS_TIMEOUT)
        with open(out, "rb") as fh:
            return fh.read()
    except subprocess.CalledProcessError as e:
        msg = (e.stderr or b"").decode("utf-8", "replace")[:200]
        log.warning("ffmpeg concat falló: %s", msg)
        raise TtsError("No se pudo unir el audio del podcast.") from e
    finally:
        try:
            os.unlink(out)
        except OSError:
            pass


# --- Limpieza de Markdown para que la voz no lea símbolos --------------------
def clean_for_speech(md: str) -> str:
    t = md or ""
    t = re.sub(r"```.*?```", " ", t, flags=re.S)        # bloques de código
    t = re.sub(r"`([^`]*)`", r"\1", t)                  # código inline
    t = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", t)         # imágenes
    t = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", t)      # links → texto
    t = re.sub(r"^\s{0,3}#{1,6}\s*", "", t, flags=re.M)  # headings
    t = re.sub(r"[*_~>#|]+", " ", t)                     # marcas sueltas
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


# --- Piper -------------------------------------------------------------------
def _piper_to_wav(text: str, model_path: str) -> str:
    """Sintetiza con Piper a un WAV temporal; devuelve la ruta."""
    out = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name
    try:
        subprocess.run(
            [PIPER_BIN, "--model", model_path, "--output_file", out],
            input=text.encode("utf-8"), check=True, capture_output=True, timeout=TTS_TIMEOUT,
        )
        return out
    except BaseException:
        try:
            os.unlink(out)
        except OSError:
            pass
        raise


# --- OpenAI ------------------------------------------------------------------
def _chunks(text: str, size: int):
    text = text.strip()
    while text:
        if len(text) <= size:
            yield text
            return
        cut = text.rfind(". ", 0, size)
        if cut < size * 0.5:
            cut = text.rfind(" ", 0, size)
        if cut <= 0:
            cut = size
        yield text[:cut + 1].strip()
        text = text[cut + 1:].lstrip()


def _openai_to_wav(text: str, voice: str, client, model: str) -> str:
    """Sintetiza con OpenAI TTS a WAV (para poder concatenar/filtrar uniforme)."""
    out = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name
    raw = bytearray()
    try:
        for ch in _chunks(text, OPENAI_TTS_CHUNK):
            resp = client.audio.speech.create(
                model=model or OPENAI_TTS_MODEL, voice=voice, input=ch, response_format="wav")
            raw += resp.read() if hasattr(resp, "read") else resp.content
        # cada respuesta es un WAV con header; para simplificar, escribimos el
        # primero entero y, si hubo varios, los unimos vía ffmpeg en el caller.
        with open(out, "wb") as fh:
            fh.write(bytes(raw))
        return out
    except BaseException:
        try:
            os.unlink(out)
        except OSError:
            pass
        raise


# --- API de alto nivel -------------------------------------------------------
def _resolve_piper(voice_id: str) -> str:
    vid = voice_id.split(":", 1)[1] if ":" in voice_id else voice_id
    models = _piper_models()
    if vid in models:
        return models[vid]
    # fallback: primera voz del mismo idioma
    lang = vid.split("_")[0]
    for k, p in models.items():
        if k.startswith(lang):
            return p
    if models:
        return next(iter(models.values()))
    raise TtsError("No hay voces locales instaladas.")


def synthesize_narration(text, voice_id, pitch="medium", speed="normal",
                         volume="medium", openai_client=None, openai_model=None) -> bytes:
    text = clean_for_speech(text)
    if not text:
        raise TtsError("No hay texto para leer.")
    engine = "openai" if str(voice_id).startswith("openai:") else "piper"
    wav = None
    try:
        if engine == "openai":
            if not openai_client:
                raise TtsError("Falta la API key para la voz cloud.")
            vname = voice_id.split(":", 1)[1]
            wav = _openai_to_wav(text, vname, openai_client, openai_model)
        else:
            if not piper_available():
                raise TtsError("El motor de voz local no está disponible.")
            wav = _piper_to_wav(text, _resolve_piper(voice_id))
        return _encode_mp3(wav, pitch, speed, volume)
    finally:
        if wav:
            try:
                os.unlink(wav)
            except OSError:
                pass


_DIALOGUE_SYS = (
    "You write short, lively two-host podcast scripts that explain a document. "
    "Two hosts: A (host) and B (expert). Natural, conversational, in the SAME "
    "language as the document. 8-16 short turns. Return ONLY JSON: "
    '{\"turns\":[{\"speaker\":\"A\",\"text\":\"...\"},...]}. No markdown, no extra text.'
)


def generate_dialogue(text, openai_client, model) -> list:
    """Pide a la IA un guion de podcast (2 voces). Devuelve [{speaker,text}]."""
    src = clean_for_speech(text)[:6000]
    if not openai_client:
        raise TtsError("El modo podcast necesita una API de IA configurada.")
    try:
        resp = openai_client.chat.completions.create(
            model=model or "gpt-4o-mini",
            messages=[{"role": "system", "content": _DIALOGUE_SYS},
                      {"role": "user", "content": src}],
            temperature=0.7,
        )
        raw = resp.choices[0].message.content or ""
        raw = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.M).strip()
        data = json.loads(raw)
        turns = data.get("turns") or []
        out = [{"speaker": ("B" if str(t.get("speaker", "A")).upper().startswith("B") else "A"),
                "text": (t.get("text") or "").strip()} for t in turns if (t.get("text") or "").strip()]
        if not out:
            raise TtsError("La IA no devolvió un guion válido.")
        return out
    except TtsError:
        raise
    except Exception as e:  # noqa: BLE001
        log.warning("Guion de podcast falló: %s", e)
        raise TtsError("No se pudo generar el guion del podcast.") from e


def synthesize_podcast(text, voice_a, voice_b, pitch="medium", speed="normal",
                       volume="medium", openai_client=None, openai_model=None,
                       script_model=None) -> bytes:
    turns = generate_dialogue(text, openai_client, script_model)
    eng_a = "openai" if str(voice_a).startswith("openai:") else "piper"
    eng_b = "openai" if str(voice_b).startswith("openai:") else "piper"
    wavs = []
    try:
        for tn in turns:
            v = voice_a if tn["speaker"] == "A" else voice_b
            eng = eng_a if tn["speaker"] == "A" else eng_b
            if eng == "openai":
                if not openai_client:
                    raise TtsError("Falta la API key para la voz cloud.")
                wavs.append(_openai_to_wav(tn["text"], v.split(":", 1)[1], openai_client, openai_model))
            else:
                if not piper_available():
                    raise TtsError("El motor de voz local no está disponible.")
                wavs.append(_piper_to_wav(tn["text"], _resolve_piper(v)))
        return _concat_wavs_to_mp3(wavs, pitch, speed, volume)
    finally:
        for w in wavs:
            try:
                os.unlink(w)
            except OSError:
                pass
