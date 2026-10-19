import io

import pytest
from docx import Document as DocxDocument
from pypdf import PdfWriter

from app.services.extraction_service import (
    ExtractionError,
    UnsupportedFormatError,
    extract_text,
)


def test_txt_utf8():
    assert extract_text("a.txt", "Night City ñ".encode("utf-8")) == "Night City ñ"


def test_txt_cp1252_fallback():
    assert extract_text("a.md", "Peña".encode("cp1252")) == "Peña"


def test_csv():
    assert "V,Merc" in extract_text("p.csv", b"nombre,rol\nV,Merc\n")


def test_nul_removed():
    assert extract_text("a.txt", b"ab\x00cd") == "abcd"


def test_docx():
    buf = io.BytesIO()
    d = DocxDocument()
    d.add_paragraph("Johnny Silverhand")
    d.save(buf)
    assert "Johnny Silverhand" in extract_text("a.docx", buf.getvalue())


def test_pdf_without_text():
    buf = io.BytesIO()
    w = PdfWriter()
    w.add_blank_page(width=100, height=100)
    w.write(buf)
    with pytest.raises(ExtractionError):
        extract_text("a.pdf", buf.getvalue())


def test_corrupt_pdf_and_docx():
    with pytest.raises(ExtractionError):
        extract_text("a.pdf", b"no es un pdf")
    with pytest.raises(ExtractionError):
        extract_text("a.docx", b"no es un docx")


def test_empty_and_unsupported():
    with pytest.raises(ExtractionError):
        extract_text("a.txt", b"")
    with pytest.raises(ExtractionError):
        extract_text("a.txt", b"   \n ")
    with pytest.raises(UnsupportedFormatError):
        extract_text("a.exe", b"x")
