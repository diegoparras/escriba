# Anonimal

PII **anonymization microservice** for [Escriba](../README.md), wrapping
[OpenAI Privacy Filter](https://github.com/openai/privacy-filter) (OPF, Apache-2.0).
It detects and masks personal data — names, emails, phones, addresses,
account/tax numbers (DNI/CUIT/CBU…), URLs and secrets — **locally**, on CPU.

> ⚠️ **Internal only.** Anonimal has no authentication; it assumes it sits on a
> private network behind Escriba. **Never expose it to the internet.**

## How it works

- The OPF checkpoint (~2.8 GB) is **baked into the image** in a stable layer, so
  there is no runtime download — the model is present on every boot.
- It is loaded **once** into RAM in the background at startup (singleton) and
  warmed up, so `/health` answers immediately and the healthcheck never flaps
  while the ~5 GB model enters memory. `/anonymize` returns `503` until ready.
- Inference is **serialized** (one forward pass at a time) to protect RAM.

## Endpoints

| Method | Path | Body / response |
|---|---|---|
| `POST` | `/anonymize` | `{"text": "…"}` → OPF `to_dict()` (`text`, `detected_spans` with `label/start/end/text/placeholder`, `redacted_text`, `summary`). |
| `GET` | `/health` | `{status, model_loaded, device, error}` |

Escriba builds two outputs from one response: **typed** (uses `redacted_text` /
per-category placeholders) and **anon** (each span → `<<ANOM_DATA>>`).

## Environment

| Variable | Default | Description |
|---|---|---|
| `OPF_DEVICE` | `cpu` | `cpu` or `cuda`. |
| `ANONIMAL_MAX_CHARS` | `500000` | Max input size; larger → `413`. |

## Run

```bash
# Prebuilt image
docker run -d --name anonimal ghcr.io/diegoparras/anonimal:latest
# Build locally
docker build -t anonimal ./anonimal
```

Then point Escriba at it with `ANONIMAL_URL=http://anonimal:8000`.

### Resources

The model is resident in RAM (~5 GB). Give the container ~6 GB and it is
CPU-bound, so it shares cores with Escriba.

## EasyPanel

1. Create an **App** from `ghcr.io/diegoparras/anonimal:latest`.
2. **Do not** assign a public domain/port — keep it on the internal network.
3. In the Escriba service, set `ANONIMAL_URL` to the internal hostname
   (e.g. `http://anonimal:8000`).
