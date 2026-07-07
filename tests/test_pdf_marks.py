"""Tests del marcador OPCIONAL de página/diapositiva (feature `mark_pages`).

Cubre el módulo `app.pdf_extract`, que concentra todo el marcado:
- `page_marker`  → formato del marcador (ancla citable + línea visible).
- `extract_pdf_text` → intercalado por página (con/sin flag) y numeración original.
- `mark_slides`  → normalización de los delimitadores de diapositiva de MarkItDown.

No importa `app.main` a propósito: la lógica vive en `pdf_extract`, así el test
no arrastra FastAPI/markitdown y prueba solo la unidad relevante.
"""
import pymupdf
import pytest

import app.pdf_extract as px


def _make_pdf(path, n_pages):
    """PDF sintético de `n_pages`, con texto distinguible por página."""
    doc = pymupdf.open()
    for i in range(1, n_pages + 1):
        page = doc.new_page()
        page.insert_text((72, 72), f"Contenido de la pagina numero {i}.")
    doc.save(str(path))
    doc.close()


# ---------- page_marker (formato del marcador) ----------

def test_page_marker_formato_pagina():
    assert px.page_marker(3) == "<!-- page:3 -->\n**Página 3**"


def test_page_marker_label_diapositiva():
    assert px.page_marker(4, "Diapositiva") == "<!-- page:4 -->\n**Diapositiva 4**"


# ---------- extract_pdf_text ----------

def test_sin_marca_no_agrega_ancla(tmp_path):
    """Sin el flag, el output NO debe contener marcadores (cero regresión)."""
    pdf = tmp_path / "doc.pdf"
    _make_pdf(pdf, 3)
    out = px.extract_pdf_text(str(pdf))
    assert "<!-- page:" not in out
    assert "**Página" not in out
    # El contenido real se conserva.
    for i in (1, 2, 3):
        assert f"pagina numero {i}" in out


def test_con_marca_intercala_por_pagina(tmp_path):
    pdf = tmp_path / "doc.pdf"
    _make_pdf(pdf, 3)
    out = px.extract_pdf_text(str(pdf), mark_pages=True)
    for n in (1, 2, 3):
        assert f"<!-- page:{n} -->" in out
        assert f"**Página {n}**" in out
    # Cada marcador va ANTES de su contenido.
    assert out.index("<!-- page:1 -->") < out.index("pagina numero 1") < out.index("<!-- page:2 -->")


def test_numeracion_original_tras_recorte(tmp_path):
    """Con `page_numbers`, el marcador cita la página REAL del archivo (no la del
    recorte): simula un subset cuyas 3 páginas físicas eran 5, 6 y 7 en el original."""
    pdf = tmp_path / "recorte.pdf"
    _make_pdf(pdf, 3)
    out = px.extract_pdf_text(str(pdf), mark_pages=True, page_numbers=[5, 6, 7])
    for n in (5, 6, 7):
        assert f"<!-- page:{n} -->" in out
    # No debe usar la numeración 1..3 del recorte.
    assert "<!-- page:1 -->" not in out


def test_page_numbers_ignorado_sin_flag(tmp_path):
    pdf = tmp_path / "doc.pdf"
    _make_pdf(pdf, 2)
    out = px.extract_pdf_text(str(pdf), mark_pages=False, page_numbers=[5, 6])
    assert "<!-- page:" not in out


# ---------- mark_slides (PPTX de MarkItDown) ----------

def test_mark_slides_normaliza_comentarios():
    sample = (
        "<!-- Slide number: 1 -->\n# Titulo\nBienvenidos\n\n"
        "<!-- Slide number: 2 -->\n## Agenda\n- A\n- B\n\n"
        "<!-- Slide number: 3 -->\nCierre\n"
    )
    out = px.mark_slides(sample)
    assert "Slide number" not in out
    for n in (1, 2, 3):
        assert f"<!-- page:{n} -->" in out
        assert f"**Diapositiva {n}**" in out


def test_mark_slides_tolerante_a_espaciado():
    # MarkItDown puede variar el espaciado interno del comentario.
    assert px.mark_slides("<!--Slide number:7-->") == px.page_marker(7, "Diapositiva")
    assert px.mark_slides("<!--   Slide number:   9   -->") == px.page_marker(9, "Diapositiva")


def test_mark_slides_sin_diapositivas_no_cambia_nada():
    txt = "# Un documento normal\nsin diapositivas."
    assert px.mark_slides(txt) == txt


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
