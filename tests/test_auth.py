"""Tests de auth: token HMAC (firma/expiración/tamper), login por rol, matriz de caps."""
import hashlib
import hmac
import json
import time

import app.auth as auth


def test_token_roundtrip():
    assert auth.verify_token(auth.make_token("dios")) == "dios"
    assert auth.verify_token(auth.make_token("humano")) == "humano"


def test_token_tampered_signature_rejected():
    body, sig = auth.make_token("dios").split(".", 1)
    bad_sig = sig[:-1] + ("A" if sig[-1] != "A" else "B")
    assert auth.verify_token(body + "." + bad_sig) is None
    assert auth.verify_token("garbage") is None
    assert auth.verify_token(body + ".xxxx") is None


def test_token_payload_tamper_rejected():
    # Editar el payload (p.ej. subir de rol) sin re-firmar debe invalidar el token.
    body, sig = auth.make_token("humano").split(".", 1)
    forged_body = auth._b64e(json.dumps(
        {"role": "dios", "exp": int(time.time()) + 9999, "jti": "x"}).encode())
    assert auth.verify_token(forged_body + "." + sig) is None


def test_token_expired_rejected():
    # Firma VÁLIDA pero exp en el pasado → rechazado.
    body = auth._b64e(json.dumps(
        {"role": "dios", "exp": int(time.time()) - 10, "jti": "x"}).encode())
    sig = auth._b64e(hmac.new(auth.SECRET_BYTES, body.encode(), hashlib.sha256).digest())
    assert auth.verify_token(body + "." + sig) is None


def test_role_for_password(monkeypatch):
    monkeypatch.setattr(auth, "_PASSWORDS", {"dios": "zeus", "angel": None, "humano": "hola"})
    assert auth.role_for_password("zeus") == "dios"
    assert auth.role_for_password("hola") == "humano"
    assert auth.role_for_password("mal") is None
    assert auth.role_for_password("") is None


def test_caps_matrix():
    assert auth.caps_for("dios")["allow_internal"] is True
    assert auth.caps_for("humano")["allow_internal"] is False
    assert auth.caps_for("humano")["convert_url"] is False
