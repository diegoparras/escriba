"""lockatus_client.py — cliente OIDC mínimo para federar Escriba (el hub de la suite) con Lockatus
(el hub de identidad). Solo se usa si AUTH_MODE=federado. Stdlib (urllib) para no sumar httpx;
`cryptography` se importa LAZY dentro de verify_jwt → el modo local no lo necesita instalado.
Verifica los tokens RS256 contra el JWKS del hub (offline). Espejo del cliente de Anonimal/Fisherboy."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
import urllib.parse
import urllib.request

_now_ms = lambda: int(time.time() * 1000)
_b64d = lambda s: base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))
_b64e = lambda b: base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _get_json(url: str):
    with urllib.request.urlopen(url, timeout=10) as r:  # noqa: S310 (URL del issuer, de confianza)
        return json.loads(r.read())


def _post_form(url: str, data: dict):
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=10) as r:  # noqa: S310
        return json.loads(r.read())


class Lockatus:
    def __init__(self, issuer: str, client_id: str, redirect_uri: str, secret: str):
        self.issuer = issuer.rstrip("/")
        self.client_id = client_id
        self.redirect_uri = redirect_uri
        self.secret = secret.encode() if isinstance(secret, str) else secret
        self._jwks = None
        self._jwks_at = 0.0

    def pkce(self):
        verifier = _b64e(secrets.token_bytes(32))
        challenge = _b64e(hashlib.sha256(verifier.encode()).digest())
        return verifier, challenge

    def random_id(self):
        return _b64e(secrets.token_bytes(12))

    def authorize_url(self, state, nonce, challenge):
        q = urllib.parse.urlencode({
            "client_id": self.client_id, "redirect_uri": self.redirect_uri, "response_type": "code",
            "scope": "openid email", "state": state, "nonce": nonce,
            "code_challenge": challenge, "code_challenge_method": "S256",
        })
        return f"{self.issuer}/authorize?{q}"

    def exchange(self, code, verifier):
        tok = _post_form(f"{self.issuer}/token", {
            "grant_type": "authorization_code", "code": code, "redirect_uri": self.redirect_uri,
            "client_id": self.client_id, "code_verifier": verifier,
        })
        if "access_token" not in tok:
            raise ValueError("no se pudo canjear el código")
        return tok

    def _keys(self):
        if self._jwks and time.time() - self._jwks_at < 3600:
            return self._jwks
        self._jwks = _get_json(f"{self.issuer}/jwks.json").get("keys", [])
        self._jwks_at = time.time()
        return self._jwks

    def verify_jwt(self, token, audience=None, nonce=None):
        from cryptography.hazmat.primitives import hashes  # import lazy: solo si federás
        from cryptography.hazmat.primitives.asymmetric import padding, rsa
        h_b, p_b, s_b = token.split(".")
        header = json.loads(_b64d(h_b))
        keys = self._keys()
        jwk = next((k for k in keys if k.get("kid") == header.get("kid")), keys[0] if keys else None)
        if not jwk:
            raise ValueError("sin clave en el JWKS")
        n = int.from_bytes(_b64d(jwk["n"]), "big")
        e = int.from_bytes(_b64d(jwk["e"]), "big")
        rsa.RSAPublicNumbers(e, n).public_key().verify(_b64d(s_b), f"{h_b}.{p_b}".encode(), padding.PKCS1v15(), hashes.SHA256())
        c = json.loads(_b64d(p_b))
        if c.get("iss") != self.issuer:
            raise ValueError("iss inválido")
        aud = c.get("aud")
        aud = aud if isinstance(aud, list) else [aud]
        if audience and audience not in aud:
            raise ValueError("aud inválido")
        if c.get("exp") and c["exp"] * 1000 < _now_ms():
            raise ValueError("token expirado")
        if nonce and c.get("nonce") != nonce:
            raise ValueError("nonce inválido")
        return c

    def sign(self, obj):
        body = _b64e(json.dumps(obj, separators=(",", ":")).encode())
        mac = _b64e(hmac.new(self.secret, body.encode(), hashlib.sha256).digest())
        return f"{body}.{mac}"

    def unsign(self, token):
        try:
            body, mac = (token or "").split(".")
            exp = _b64e(hmac.new(self.secret, body.encode(), hashlib.sha256).digest())
            if not hmac.compare_digest(mac, exp):
                return None
            o = json.loads(_b64d(body))
            if o.get("exp") and o["exp"] < _now_ms():
                return None
            return o
        except Exception:
            return None
