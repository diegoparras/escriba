# ============================================================================
#  Anonimal — OPF (OpenAI Privacy Filter) como microservicio.
#  El checkpoint se HORNEA en la imagen (capa estable, igual que el modelo
#  Whisper en Escriba) → cero descarga en runtime, listo en cada boot.
# ============================================================================
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    OPF_DEVICE=cpu

WORKDIR /app

# git: para instalar OPF desde su repo.  curl: para el HEALTHCHECK.
RUN apt-get update && apt-get install -y --no-install-recommends git curl \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# torch CPU-only PRIMERO: OPF corre en CPU, así evitamos ~2,5 GB de librerías
# CUDA inútiles (imagen ~8 GB → ~4 GB, pulls más rápidos). Al instalar OPF
# después, ve torch ya satisfecho y no baja la variante CUDA de PyPI.
RUN pip install --index-url https://download.pytorch.org/whl/cpu torch \
 && pip install -r requirements.txt \
 && pip install "git+https://github.com/openai/privacy-filter.git" \
 && python -c "import torch; assert torch.version.cuda is None, 'se coló torch CUDA'; print('torch CPU', torch.__version__)"

# Usuario NO-root. Creamos antes del horneado para que el checkpoint quede en su
# HOME, de su propiedad (lectura/escritura en runtime sin chown de 2,8 GB).
# OJO: NO seteamos OPF_CHECKPOINT — ensure_default_checkpoint() siempre baja a
# ~/.opf/privacy_filter, y OPF() (model=None) lee ese mismo default. Mantenerlos
# alineados evita el "Checkpoint directory not found".
RUN useradd -m -u 10001 anon
USER anon
ENV HOME=/home/anon \
    HF_HOME=/home/anon/.cache/huggingface

# --- Horneado del checkpoint (~2,8 GB) en una capa ESTABLE ------------------
# La descarga la hace ensure_default_checkpoint() (snapshot_download a
# ~/.opf/privacy_filter). OPF() solo valida, NO descarga. Reintentos para 429/
# cortes de HuggingFace. Luego un redact() de warm-up valida que cargue en CPU.
RUN for i in 1 2 3 4 5; do \
      python -c "from opf._common.checkpoint_download import ensure_default_checkpoint; print('checkpoint:', ensure_default_checkpoint())" && break; \
      echo "Reintento de descarga de OPF ($i)…"; sleep 30; \
    done \
 && python -c "from opf import OPF; OPF(device='cpu', output_mode='typed').redact('warm-up')" \
 && test -d /home/anon/.opf/privacy_filter

COPY app.py .

EXPOSE 8000

# Healthcheck liviano: alcanza con que /health responda (el server atiende desde
# el arranque; model_loaded pasa a true tras el warm-up en background).
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=5 \
  CMD curl -fsS http://localhost:8000/health || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
