"""Multi-format Document Extraction (PDF, DOCX, Images/OCR) with Scoping."""

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
    import docx
except ImportError:
    docx = None

try:
    from PIL import Image
    import pytesseract
except ImportError:
    Image = None
    pytesseract = None


@dataclass
class ExtractedPage:
    """Represents text extracted from a single document page or section."""

    text: str
    source: str
    page_number: int
    doc_scope: str = "official"  # "official" or "personal"


class MultiFormatExtractor:
    """Extracts text from PDF, DOCX, and Image files with OCR fallback."""

    SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".png", ".jpg", ".jpeg"}

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

    def extract_document(
        self, file_path: Path, doc_scope: str = "official"
    ) -> Tuple[List[ExtractedPage], str]:
        """Extract pages/sections and return document fingerprint."""
        file_path = Path(file_path).resolve()
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = file_path.suffix.lower()
        fingerprint = self.compute_file_fingerprint(file_path)

        if ext == ".pdf":
            return self._extract_pdf(file_path, doc_scope), fingerprint
        elif ext in {".docx", ".doc"}:
            return self._extract_docx(file_path, doc_scope), fingerprint
        elif ext in {".png", ".jpg", ".jpeg"}:
            return self._extract_image(file_path, doc_scope), fingerprint
        else:
            raise ValueError(f"Unsupported file format: {ext}")

    def _extract_pdf(self, file_path: Path, doc_scope: str) -> List[ExtractedPage]:
        if pymupdf is None:
            raise ImportError("PyMuPDF is required for PDF extraction. Run: pip install pymupdf")

        filename = file_path.name
        extracted: List[ExtractedPage] = []
        doc = pymupdf.open(str(file_path))

        for page_index, page in enumerate(doc):
            text = page.get_text("text").strip()

            # OCR fallback for scanned pages
            if len(text) < self.ocr_min_chars and Image and pytesseract:
                try:
                    pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
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
                except Exception:
                    pass

            if text:
                extracted.append(
                    ExtractedPage(
                        text=text,
                        source=filename,
                        page_number=page_index + 1,
                        doc_scope=doc_scope,
                    )
                )

        doc.close()
        return extracted

    def _extract_docx(self, file_path: Path, doc_scope: str) -> List[ExtractedPage]:
        if docx is None:
            raise ImportError("python-docx is required for DOCX files. Run: pip install python-docx")

        document = docx.Document(str(file_path))
        full_text = []
        for para in document.paragraphs:
            if para.text.strip():
                full_text.append(para.text.strip())

        text = "\n\n".join(full_text)
        if not text:
            return []

        return [
            ExtractedPage(
                text=text,
                source=file_path.name,
                page_number=1,
                doc_scope=doc_scope,
            )
        ]

    def _extract_image(self, file_path: Path, doc_scope: str) -> List[ExtractedPage]:
        if Image is None or pytesseract is None:
            raise ImportError("Pillow and pytesseract are required for OCR image extraction.")

        image = Image.open(str(file_path))
        text = pytesseract.image_to_string(image, lang="eng").strip()
        if not text:
            return []

        return [
            ExtractedPage(
                text=text,
                source=file_path.name,
                page_number=1,
                doc_scope=doc_scope,
            )
        ]


# Backward compatibility alias
PDFExtractor = MultiFormatExtractor
