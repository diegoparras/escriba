"""Novedades por version: salen del CHANGELOG.md (una sola fuente) y se muestran en el log de
arranque (deploy en EasyPanel), en la UI al entrar despues de una actualizacion y en el Release."""
import re
from pathlib import Path

import app.novedades as nov

RAIZ = Path(__file__).resolve().parent.parent

MUESTRA = """# Changelog

Formato basado en Keep a Changelog.

## [0.3.0] - 2026-11-21

### Nuevo
- **Novedades** en la UI: se ven al entrar
  despues de una actualizacion (`GET /api/novedades`).

### Corregido
- Un arreglo corto.

## [0.2.1] - 2026-11-20

### Corregido
- Otro arreglo.

## [No publicado]

### Nuevo
- Esto no es una version.

## [0.2.0] - 2026-11-19

### Nuevo
- Algo grande.
"""


def test_parsea_versiones_fechas_secciones_e_items_multilinea():
    v = nov.parsear(MUESTRA)
    assert [x["version"] for x in v] == ["0.3.0", "0.2.1", "0.2.0"]
    assert v[0]["fecha"] == "2026-11-21"
    assert [s["titulo"] for s in v[0]["secciones"]] == ["Nuevo", "Corregido"]
    assert v[0]["secciones"][0]["items"] == [
        "**Novedades** en la UI: se ven al entrar despues de una actualizacion (`GET /api/novedades`)."
    ]


def test_items_sin_seccion_y_encabezado_con_titulo():
    v = nov.parsear("## [1.0.1] — Algo\n\n- Un item suelto.\n")
    assert v[0]["version"] == "1.0.1" and v[0]["fecha"] is None
    assert nov.lineas_log(v[0]) == ["Un item suelto."]


def test_desde_la_ultima_vista_hasta_la_actual():
    v = nov.parsear(MUESTRA)
    assert [x["version"] for x in nov.desde(v, "0.2.0", "0.3.0")] == ["0.3.0", "0.2.1"]
    assert nov.desde(v, "0.3.0", "0.3.0") == [], "ya vista: nada que mostrar"
    assert [x["version"] for x in nov.desde(v, None, "0.3.0")] == ["0.3.0"], "primera vez: solo la actual"
    assert [x["version"] for x in nov.desde(v, "0.2.0", "0.2.1")] == ["0.2.1"], "nunca posteriores a la que corre"
    assert nov.desde(v, "0.10.0", "0.3.0") == [], "compara como version, no como texto"


def test_texto_plano_para_el_log_y_markdown_para_el_release():
    v = nov.parsear(MUESTRA)[0]
    assert nov.lineas_log(v) == [
        "Nuevo: Novedades en la UI: se ven al entrar despues de una actualizacion (GET /api/novedades).",
        "Corregido: Un arreglo corto.",
    ]
    md = nov.notas_markdown(v)
    assert re.match(r"^### Nuevo\n- \*\*Novedades\*\* en la UI", md)
    assert "### Corregido\n- Un arreglo corto." in md


def test_cartel_de_arranque_cortado_al_ancho():
    v = nov.parsear(MUESTRA)
    lineas = nov.cartel_arranque("0.3.0", v, 60)
    assert all(len(x) <= 60 for x in lineas), "ningun renglon pasa el ancho"
    assert re.fullmatch(r"=+", lineas[0])
    assert lineas[1] == "ESCRIBA v0.3.0  (2026-11-21)"
    assert lineas[2] == "Que cambia en esta version:"
    assert lineas[3] == "- Nuevo: Novedades en la UI: se ven al entrar despues de una"
    assert re.match(r"^ {4}actualizacion", lineas[4]), "la continuacion queda sangrada"
    assert re.fullmatch(r"=+", lineas[-1])
    assert all("**" not in x and "`" not in x for x in lineas), "sin markdown"
    sin = nov.cartel_arranque("9.9.9", v, 60)
    assert sin[1] == "ESCRIBA v9.9.9"
    assert sin[2] == "Sin notas para esta version en el CHANGELOG."


def test_sin_changelog_no_rompe(tmp_path):
    assert nov.todas(tmp_path / "no-existe.md") == []
    lineas = nov.cartel_arranque("1.2.3", nov.todas(tmp_path / "no-existe.md"))
    assert "Sin notas para esta version en el CHANGELOG." in lineas


def test_el_changelog_real_tiene_la_seccion_de_la_version_actual():
    version = (RAIZ / "VERSION").read_text(encoding="utf-8").strip()
    assert re.fullmatch(r"\d+\.\d+\.\d+", version), "VERSION debe ser X.Y.Z"
    assert nov.version_instalada() == version
    v = nov.parsear((RAIZ / "CHANGELOG.md").read_text(encoding="utf-8"))
    actual = next((x for x in v if x["version"] == version), None)
    assert actual, f'falta "## [{version}]" en CHANGELOG.md'
    assert any(s["items"] for s in actual["secciones"]), f"la seccion {version} del CHANGELOG esta vacia"
    assert v[0]["version"] == version, "la version de VERSION es la primera del CHANGELOG"
    cartel = nov.cartel_arranque(version, v)
    assert all(len(x) <= 80 for x in cartel)
    assert "Sin notas" not in "\n".join(cartel)
