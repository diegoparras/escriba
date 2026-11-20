"""GET /api/novedades: detras de la misma auth que el resto de la API.

Necesita las dependencias de runtime (markitdown, etc.): si no estan, se saltea. Corre completo
dentro de la imagen (ver README, "Versions & release notes")."""
import pytest

pytest.importorskip("markitdown")

from fastapi.testclient import TestClient  # noqa: E402

import app.auth as auth  # noqa: E402
import app.main as main  # noqa: E402


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(auth, "HUMAN_OPEN", False)
    return TestClient(main.app)


def test_sin_sesion_401(client):
    assert client.get("/api/novedades").status_code == 401


def test_con_sesion_devuelve_la_version_instalada(client):
    client.cookies.set(auth.COOKIE_NAME, auth.make_token("humano"))
    r = client.get("/api/novedades")
    assert r.status_code == 200
    d = r.json()
    assert d["version"] == main.APP_VERSION
    assert [v["version"] for v in d["versiones"]] == [main.APP_VERSION]
    # Ya vista: nada que mostrar. "desde" invalido se ignora (primera vez).
    assert client.get(f"/api/novedades?desde={main.APP_VERSION}").json()["versiones"] == []
    assert len(client.get("/api/novedades?desde=<x>").json()["versiones"]) == 1
    assert client.get("/api/novedades?todas=1").json()["versiones"][0]["version"] == main.APP_VERSION
