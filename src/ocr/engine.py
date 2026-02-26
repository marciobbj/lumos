"""OCR engine: converts PDF pages to images and extracts text via Tesseract."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Callable
import asyncio
import logging

import pytesseract
from pdf2image import convert_from_path

logger = logging.getLogger(__name__)


@dataclass
class OCRResult:
    """Result of OCR processing on a PDF file."""

    text: str  # Full extracted text (all pages joined)
    pages: list[str]  # Per-page text
    total_pages: int
    language: str
    source_file: str
    char_count: int = field(init=False)

    def __post_init__(self):
        self.char_count = len(self.text)


class OCREngine:
    """Async OCR engine that converts PDFs to text using Tesseract.

    Usage:
        engine = OCREngine(language="por+eng")
        result = await engine.process_pdf("document.pdf")
        print(result.text)
    """

    def __init__(
        self,
        language: str = "por+eng",
        dpi: int = 300,
        tesseract_config: str = "",
    ):
        self.language = language
        self.dpi = dpi
        self.tesseract_config = tesseract_config

    async def process_pdf(
        self,
        pdf_path: str | Path,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> OCRResult:
        """Convert PDF to images, run Tesseract OCR, return combined text.

        Args:
            pdf_path: Path to the PDF file.
            progress_callback: Optional callback(current_page, total_pages)
                called after each page is processed.

        Returns:
            OCRResult with extracted text and metadata.

        Raises:
            FileNotFoundError: If pdf_path does not exist.
            pytesseract.TesseractError: If Tesseract fails on a page.
        """
        pdf_path = Path(pdf_path)

        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        if pdf_path.suffix.lower() != ".pdf":
            logger.warning(
                "File '%s' does not have .pdf extension — proceeding anyway",
                pdf_path.name,
            )

        loop = asyncio.get_event_loop()

        # PDF → PIL Images (CPU/IO bound)
        logger.info("Converting PDF to images at %d DPI: %s", self.dpi, pdf_path)
        images = await loop.run_in_executor(
            None, self._convert_pdf_to_images, str(pdf_path)
        )
        total = len(images)
        logger.info("Got %d page(s) from PDF", total)

        # Images → Text (CPU bound, one page at a time for progress)
        pages_text: list[str] = []
        for i, image in enumerate(images):
            try:
                text = await loop.run_in_executor(
                    None, self._extract_text_from_image, image
                )
            except pytesseract.TesseractError as exc:
                raise pytesseract.TesseractError(
                    exc.status,
                    f"Tesseract failed on page {i + 1}/{total}: {exc.message}",
                ) from exc
            finally:
                image.close()

            pages_text.append(text)

            if progress_callback:
                progress_callback(i + 1, total)

        # Join with page markers
        full_text = self._join_pages(pages_text)

        return OCRResult(
            text=full_text,
            pages=pages_text,
            total_pages=total,
            language=self.language,
            source_file=str(pdf_path),
        )

    def _convert_pdf_to_images(self, pdf_path: str) -> list:
        """Convert PDF file to a list of PIL Image objects."""
        return convert_from_path(pdf_path, dpi=self.dpi)

    def _extract_text_from_image(self, image) -> str:
        """Run Tesseract OCR on a single PIL Image."""
        return pytesseract.image_to_string(
            image,
            lang=self.language,
            config=self.tesseract_config,
        )

    def get_available_languages(self) -> list[str]:
        """Return list of installed Tesseract language packs."""
        return pytesseract.get_languages()

    @staticmethod
    def _join_pages(pages: list[str]) -> str:
        """Join per-page text with page separator markers."""
        if not pages:
            return ""
        if len(pages) == 1:
            return pages[0]

        parts: list[str] = []
        for i, page_text in enumerate(pages, start=1):
            parts.append(f"--- Page {i} ---\n\n{page_text}")
        return "\n\n".join(parts)
