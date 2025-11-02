from __future__ import annotations

import logging
from typing import List

# Optional imports; we'll check availability at runtime
try:
    import fitz  # PyMuPDF
except Exception:  # pragma: no cover
    fitz = None  # type: ignore

try:
    import pdfplumber
except Exception:  # pragma: no cover
    pdfplumber = None  # type: ignore


logger = logging.getLogger(__name__)


def _extract_with_pymupdf(pdf_path: str, password: str = "") -> str:
    if fitz is None:
        raise ImportError("PyMuPDF (fitz) is not installed")
    doc = fitz.open(pdf_path)
    try:
        if getattr(doc, "needs_pass", False):
            ok = doc.authenticate(password)
            if not ok:
                raise PermissionError("Incorrect password for encrypted PDF (PyMuPDF)")
        pages: List[str] = []
        for page in doc:
            # 'text' provides layout-aware plain text extraction
            pages.append(page.get_text("text"))
        return "\n\n".join(pages).strip()
    finally:
        doc.close()


def _extract_with_pdfplumber(pdf_path: str, password: str = "") -> str:
    if pdfplumber is None:
        raise ImportError("pdfplumber is not installed")
    pages: List[str] = []
    with pdfplumber.open(pdf_path, password=password or None) as pdf:
        for page in pdf.pages:
            # extract_text() may return None for image-only pages
            txt = page.extract_text() or ""
            pages.append(txt)
    return "\n\n".join(pages).strip()


def extract_text(pdf_path: str, password: str = "") -> str:
    """
    Extract full text from a PDF file as a single string.

    Strategy:
    1) Try PyMuPDF (fast, robust). If unavailable or yields empty text, fall back to pdfplumber.
    2) If both fail or produce empty content, raise a ValueError.

    Args:
        pdf_path: Path to the PDF file.
        password: Optional password for encrypted PDFs.

    Returns:
        Concatenated text across all pages.
    """
    # Try PyMuPDF first
    try:
        text = _extract_with_pymupdf(pdf_path, password=password)
        if text:
            return text
        logger.warning("PyMuPDF returned empty text; attempting pdfplumber fallback...")
    except Exception as e:
        logger.debug("PyMuPDF extraction failed: %s", e)

    # Fallback: pdfplumber
    try:
        text = _extract_with_pdfplumber(pdf_path, password=password)
        if text:
            return text
    except Exception as e:
        logger.debug("pdfplumber extraction failed: %s", e)

    raise ValueError("Failed to extract text from PDF using both PyMuPDF and pdfplumber.")
