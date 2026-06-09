# -*- coding: utf-8 -*-
"""
Anonimal — microservicio de detección/anonimización de PII con OpenAI Privacy
Filter (OPF). Envuelve el modelo en un singleton cargado UNA sola vez.

Diseño:
- El modelo se carga en BACKGROUND al arrancar (no bloquea el servidor): así
  /health responde al instante y /anonymize devuelve 503 hasta terminar el
  warm-up. Evita que el healthcheck marque el contenedor como unhealthy mientras
  el modelo entra en RAM.
- Inferencia SERIALIZADA (un forward pass a la vez, asyncio.Lock) para proteger
  la RAM, ejecutada en un threadpool para no bloquear el event loop.
- Contrato "detecta, no decide": devuelve el to_dict() crudo de OPF (spans +
  offsets). Quien llama (Escriba) arma el reemplazo de su lado.

SEGURIDAD: este servicio es SOLO para la red interna de Docker. Nunca exponerlo
a internet — no tiene auth porque se asume aislado detrás de Escriba.
"""
import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("anonimal")

OPF_DEVICE = os.getenv("OPF_DEVICE", "cpu")
MAX_CHARS = int(os.getenv("ANONIMAL_MAX_CHARS", "500000"))

# Estado del singleton del modelo.
_state = {"opf": None, "error": None}
_infer_lock = asyncio.Lock()   # un redact() a la vez (protege la RAM)


def _load_model_blocking():
    """Carga OPF y hace warm-up. Bloqueante → se corre en un thread."""
    from opf import OPF
    # OPF() solo VALIDA un checkpoint existente; la descarga la hace una función
    # aparte. Si no hay override OPF_CHECKPOINT, garantizamos el checkpoint por
    # defecto (~/.opf/privacy_filter): no-op si ya está horneado, descarga si falta.
    if not os.getenv("OPF_CHECKPOINT"):
        from opf._common.checkpoint_download import ensure_default_checkpoint
        log.info("Verificando checkpoint OPF…")
        ensure_default_checkpoint()
    log.info("Cargando OPF (device=%s)…", OPF_DEVICE)
    opf = OPF(device=OPF_DEVICE, output_mode="typed")
    # Primer forward pass para que el 1er request real no pague la carga lazy.
    opf.redact("warm-up")
    log.info("OPF cargado y caliente.")
    return opf


async def _load_model():
    try:
        _state["opf"] = await asyncio.to_thread(_load_model_blocking)
    except Exception as e:  # noqa: BLE001
        _state["error"] = str(e)
        log.exception("No se pudo cargar OPF")


@asynccontextmanager
async def lifespan(app):
    # Carga en background: el server atiende /health enseguida.
    task = asyncio.create_task(_load_model())
    yield
    task.cancel()


app = FastAPI(title="Anonimal", version="1.0", lifespan=lifespan)


class AnonReq(BaseModel):
    text: str


@app.get("/health")
async def health():
    return {
        "status": "ok" if _state["opf"] else ("error" if _state["error"] else "loading"),
        "model_loaded": _state["opf"] is not None,
        "device": OPF_DEVICE,
        "error": _state["error"],
    }


@app.post("/anonymize")
async def anonymize(req: AnonReq):
    if _state["opf"] is None:
        if _state["error"]:
            raise HTTPException(status_code=503, detail=f"El modelo no cargó: {_state['error']}")
        raise HTTPException(status_code=503, detail="El modelo aún se está cargando. Probá en unos segundos.")
    if len(req.text) > MAX_CHARS:
        raise HTTPException(status_code=413, detail=f"El texto supera el límite de {MAX_CHARS} caracteres.")
    if not req.text.strip():
        return {"text": req.text, "detected_spans": [], "redacted_text": req.text, "summary": {}}
    async with _infer_lock:
        result = await asyncio.to_thread(_state["opf"].redact, req.text)
    return result.to_dict()
