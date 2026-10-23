"""PDF extraction with OCR fallback for scanned campus notices and documents."""

import hashlib
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

try:
    import pymupdf
except ImportError:
    try:
        import fitz as pymupdf
    except ImportError:
        pymupdf = None

try:
    from PIL import Image
    import pytesseract
except ImportError:
    Image = None
    pytesseract = None


@dataclass
class ExtractedPage:
    """Represents text extracted from a single PDF page."""

    text: str
    source: str
    page_number: int


class PDFExtractor:
    """Extracts text from PDF documents with OCR fallback for scanned pages."""

    def __init__(self, ocr_min_chars: int = 50):
        self.ocr_min_chars = ocr_min_chars

    @staticmethod
    def compute_file_fingerprint(file_path: Path) -> str:
        """Compute SHA-256 hash of the entire file."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def extract_pdf(self, file_path: Path) -> Tuple[List[ExtractedPage], str]:
        """Extract pages and calculate document fingerprint."""
        if pymupdf is None:
            raise ImportError(
                "PyMuPDF is required for PDF extraction. Run: pip install pymupdf"
            )

        file_path = Path(file_path).resolve()
        if not file_path.exists():
            raise FileNotFoundError(f"PDF not found: {file_path}")

        fingerprint = self.compute_file_fingerprint(file_path)
        filename = file_path.name
        extracted_pages: List[ExtractedPage] = []

        doc = pymupdf.open(str(file_path))

        for page_index, page in enumerate(doc):
            # 1. Normal text extraction
            text = page.get_text("text").strip()

            # 2. OCR fallback if page text is minimal (e.g. scanned image notice)
            if len(text) < self.ocr_min_chars and Image and pytesseract:
                try:
                    pix = page.get_pixmap(
                        matrix=pymupdf.Matrix(2, 2),
                        alpha=False,
                    )
                    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                        tmp_path = tmp.name
                    pix.save(tmp_path)

                    image = Image.open(tmp_path)
                    ocr_text = pytesseract.image_to_string(image, lang="eng").strip()
                    try:
                        os.remove(tmp_path)
                    except OSError:
                        pass

                    if len(ocr_text) > len(text):
                        text = ocr_text
                except Exception as ocr_err:
                    # Graceful skip if OCR engine (Tesseract binary) is not configured
                    pass

            if text:
                extracted_pages.append(
                    ExtractedPage(
                        text=text,
                        source=filename,
                        page_number=page_index + 1,
                    )
                )

        doc.close()
        return extracted_pages, fingerprint
