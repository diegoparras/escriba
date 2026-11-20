"""Novedades por version, leidas del CHANGELOG.md (una sola fuente de verdad).

Se muestran en tres lugares: el log de arranque (lo primero que se ve en los registros de
EasyPanel), la UI (aviso "Novedades" al entrar despues de una actualizacion) y el Release de
GitHub que crea el CI. Formato esperado (Keep a Changelog):

    ## [X.Y.Z] - AAAA-MM-DD
    ### Seccion
    - item (las lineas siguientes con sangria continuan el item)

La version instalada vive en el archivo VERSION (raiz del repo, viaja en la imagen).

Uso por linea de comandos (sin dependencias: no importa la app):
    python -m app.novedades            -> cartel de arranque (nunca falla)
    python -m app.novedades notas      -> notas en markdown de la version actual (sale 1 si faltan)
    python -m app.novedades --version  -> solo el numero
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Optional

PREFIJO = "[escriba] "
_RAIZ = Path(__file__).resolve().parent.parent
CHANGELOG = _RAIZ / "CHANGELOG.md"
VERSION_FILE = _RAIZ / "VERSION"

_RE_VERSION = re.compile(r"^## \[(\d+\.\d+\.\d+)\](?:\s*-\s*(\d{4}-\d{2}-\d{2}))?")
_RE_SECCION = re.compile(r"^### (.+)")
_RE_ITEM = re.compile(r"^- (.*)")
_RE_CONT = re.compile(r"^\s+\S")


def parsear(texto: str) -> list[dict]:
    """Lista de versiones (de la mas nueva a la mas vieja, como en el archivo):
    {"version", "fecha", "secciones": [{"titulo", "items"}]}. Los items que no estan bajo un
    "###" quedan en una seccion sin titulo (None)."""
    versiones: list[dict] = []
    v: Optional[dict] = None
    sec: Optional[dict] = None
    for linea in str(texto or "").splitlines():
        m = _RE_VERSION.match(linea)
        if m:
            v = {"version": m.group(1), "fecha": m.group(2), "secciones": []}
            versiones.append(v)
            sec = None
            continue
        if v is None:
            continue
        if linea.startswith("## "):   # otra cosa de nivel 2 (p. ej. "No publicado"): se corta
            v = None
            continue
        t = _RE_SECCION.match(linea)
        if t:
            sec = {"titulo": t.group(1).strip(), "items": []}
            v["secciones"].append(sec)
            continue
        item = _RE_ITEM.match(linea)
        if item:
            if sec is None:
                sec = {"titulo": None, "items": []}
                v["secciones"].append(sec)
            sec["items"].append(item.group(1).strip())
            continue
        if sec is not None and sec["items"] and _RE_CONT.match(linea):
            sec["items"][-1] += " " + linea.strip()
    for x in versiones:
        x["secciones"] = [s for s in x["secciones"] if s["items"]]
    return versiones


def _tupla(v: Optional[str]) -> tuple[int, int, int]:
    m = re.match(r"^v?(\d+)\.(\d+)\.(\d+)", str(v or ""))
    return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else (0, 0, 0)


def comparar(a: Optional[str], b: Optional[str]) -> int:
    ta, tb = _tupla(a), _tupla(b)
    return (ta > tb) - (ta < tb)


def desde(versiones: list[dict], vista: Optional[str], actual: str) -> list[dict]:
    """Versiones posteriores a `vista` y hasta `actual` inclusive (sin `vista`: solo la actual)."""
    if not vista:
        return [x for x in versiones if x["version"] == actual]
    return [x for x in versiones if comparar(x["version"], vista) > 0 and comparar(x["version"], actual) <= 0]


def _plano(s: str) -> str:
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", str(s))
    return re.sub(r"`([^`]+)`", r"\1", s)


def lineas_log(v: dict) -> list[str]:
    """Una linea por item, sin markdown, para el log del contenedor."""
    return [
        (f"{s['titulo']}: " if s["titulo"] else "") + _plano(i)
        for s in v["secciones"]
        for i in s["items"]
    ]


def _cortar(texto: str, ancho: int, pre: str, sangria: str) -> list[str]:
    """Corta en renglones de hasta `ancho`; el primero lleva `pre`, los demas `sangria`."""
    out: list[str] = []
    linea, base = pre, True
    for palabra in str(texto).split():
        if not base and len(linea) + 1 + len(palabra) > ancho:
            out.append(linea)
            linea, base = sangria, True
        linea += ("" if base else " ") + palabra
        base = False
    out.append(linea)
    return out


def cartel_arranque(version: str, versiones: list[dict], ancho: int = 80) -> list[str]:
    """Cartel que se imprime PRIMERO al levantar el contenedor: version, fecha y que cambia,
    cortado al ancho para leerlo sin scroll lateral."""
    v = next((x for x in versiones or [] if x["version"] == version), None)
    raya = "=" * min(ancho, 60)
    titulo = f"ESCRIBA v{version}" + (f"  ({v['fecha']})" if v and v.get("fecha") else "")
    lineas = [raya, titulo]
    if not v or not v["secciones"]:
        lineas.append("Sin notas para esta version en el CHANGELOG.")
    else:
        lineas.append("Que cambia en esta version:")
        for item in lineas_log(v):
            lineas.extend(_cortar(item, ancho, "- ", "    "))
    lineas.append(raya)
    return lineas


def notas_markdown(v: dict) -> str:
    """Notas en markdown para el Release de GitHub."""
    bloques = []
    for s in v["secciones"]:
        items = "\n".join(f"- {i}" for i in s["items"])
        bloques.append(f"### {s['titulo']}\n{items}" if s["titulo"] else items)
    return "\n\n".join(bloques) + "\n"


_CACHE: dict[str, list[dict]] = {}


def todas(ruta: Optional[Path] = None) -> list[dict]:
    """CHANGELOG.md de la instalacion (viene en la imagen). Sin archivo: lista vacia, nunca tira."""
    p = Path(ruta) if ruta else CHANGELOG
    clave = str(p)
    if clave not in _CACHE:
        try:
            _CACHE[clave] = parsear(p.read_text(encoding="utf-8"))
        except Exception:   # sin archivo, ilegible o mal formado: sin notas, la app sigue
            _CACHE[clave] = []
    return _CACHE[clave]


def version_instalada() -> Optional[str]:
    """Version del archivo VERSION (X.Y.Z) o None si no esta o no tiene ese formato."""
    try:
        v = VERSION_FILE.read_text(encoding="utf-8").strip()
    except Exception:
        return None
    return v if re.fullmatch(r"\d+\.\d+\.\d+", v) else None


def _main(argv: list[str]) -> int:
    version = version_instalada()
    if "--version" in argv:
        if not version:
            print("El archivo VERSION falta o no es X.Y.Z.", file=sys.stderr)
            return 1
        sys.stdout.write(version)
        return 0
    if "notas" in argv:
        v = next((x for x in todas() if x["version"] == version), None)
        if not version or not v or not v["secciones"]:
            print(f'CHANGELOG.md no tiene la seccion "## [{version}]" (o esta vacia): '
                  "agregala antes de publicar.", file=sys.stderr)
            return 1
        sys.stdout.write(notas_markdown(v))
        return 0
    # Cartel de arranque: jamas debe impedir que la app levante.
    try:
        for linea in cartel_arranque(version or "dev", todas()):
            print(PREFIJO + linea, flush=True)
    except Exception:
        print(PREFIJO + "Sin notas para esta version en el CHANGELOG.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
