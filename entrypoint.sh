#!/bin/sh
set -e

# ---------------------------------------------------------------------------
# Workers (procesos en paralelo). "auto"/vacío => tantos como núcleos.
# ---------------------------------------------------------------------------
if [ -z "$WEB_CONCURRENCY" ] || [ "$WEB_CONCURRENCY" = "auto" ]; then
  CORES=$(nproc 2>/dev/null || echo 2)
  WEB_CONCURRENCY="$CORES"
fi
export WEB_CONCURRENCY

# ---------------------------------------------------------------------------
# Secretos: deben ser IGUALES en todos los workers, así que se generan UNA vez
# acá (antes de levantar uvicorn) y se exportan. Fijalos como env para que
# persistan entre reinicios/deploys.
# ---------------------------------------------------------------------------
if [ -z "$SECRET_KEY" ]; then
  export SECRET_KEY="$(python -c 'import secrets;print(secrets.token_hex(32))')"
  echo "[advertencia] SECRET_KEY autogenerada: las sesiones se reinician en cada deploy. Fijala como variable de entorno."
fi

if [ -z "$GOD_PASSWORD" ] && [ -z "$ANGEL_PASSWORD" ] && [ -z "$HUMAN_PASSWORD" ] && [ "${HUMAN_OPEN:-false}" != "true" ]; then
  export GOD_PASSWORD="$(python -c 'import secrets;print(secrets.token_urlsafe(12))')"
  echo "──────────────────────────────────────────────"
  echo " [!] No definiste contraseñas. GOD_PASSWORD para este arranque:"
  echo "     $GOD_PASSWORD"
  echo "     (definí GOD_PASSWORD/ANGEL_PASSWORD/HUMAN_PASSWORD como env para fijarlas)"
  echo "──────────────────────────────────────────────"
fi

# ---------------------------------------------------------------------------
# Redis para rate-limit compartido entre workers:
#   - Si REDIS_URL ya está definido  -> se usa ese (Redis externo).
#   - Si no, y EMBEDDED_REDIS != false -> levantamos un Redis local embebido.
#   - Si EMBEDDED_REDIS=false y sin URL -> rate-limit en memoria (por proceso).
# ---------------------------------------------------------------------------
REDIS_MODE="memoria (por proceso)"
if [ -n "$REDIS_URL" ]; then
  REDIS_MODE="externo ($REDIS_URL)"
elif [ "${EMBEDDED_REDIS:-true}" != "false" ]; then
  redis-server --save "" --appendonly no --dir /tmp --bind 127.0.0.1 --port 6379 --loglevel warning &
  # Esperar a que responda antes de arrancar la app (los workers se conectan al importar).
  i=0
  while [ $i -lt 20 ]; do
    redis-cli -h 127.0.0.1 ping >/dev/null 2>&1 && break
    i=$((i + 1)); sleep 0.25
  done
  export REDIS_URL="redis://127.0.0.1:6379/0"
  REDIS_MODE="embebido (127.0.0.1:6379)"
fi

PORT="${PORT:-8000}"
echo "──────────────────────────────────────────────"
echo " MarkItDown Web"
echo "   workers (paralelo) : $WEB_CONCURRENCY"
echo "   max subida (MB)    : ${MAX_UPLOAD_MB:-100}"
echo "   HUMAN_OPEN         : ${HUMAN_OPEN:-false}"
echo "   rate-limit / redis : $REDIS_MODE"
echo "   puerto             : $PORT"
echo "──────────────────────────────────────────────"

exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --workers "$WEB_CONCURRENCY" --proxy-headers --forwarded-allow-ips='*'
