"""
OCR Preprocessing Module for PDF Bank Statements

Handles PDFs with encoding issues or scanned images by:
1. Converting PDF pages to images
2. Applying OCR (Tesseract) to extract text
3. Returning cleaned text for transaction parsing

Critical for Capitec bank statements and other PDFs with font encoding issues.
"""

import os
from typing import List, Optional
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
import tempfile


class OCRProcessor:
    """Processes PDFs using OCR for text extraction when standard extraction fails."""

    def __init__(self, tesseract_cmd: Optional[str] = None):
        """
        Initialize OCR processor.

        Args:
            tesseract_cmd: Path to tesseract executable (optional, auto-detected on most systems)
        """
        # Set tesseract command if provided
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

        # Try to auto-detect on macOS
        elif os.path.exists('/opt/homebrew/bin/tesseract'):
            pytesseract.pytesseract.tesseract_cmd = '/opt/homebrew/bin/tesseract'
        elif os.path.exists('/usr/local/bin/tesseract'):
            pytesseract.pytesseract.tesseract_cmd = '/usr/local/bin/tesseract'

    def pdf_to_images(self, pdf_path: str, dpi: int = 300) -> List[Image.Image]:
        """
        Convert PDF to list of images.

        Args:
            pdf_path: Path to PDF file
            dpi: Resolution for conversion (higher = better quality but slower)

        Returns:
            List of PIL Images, one per page
        """
        try:
            images = convert_from_path(pdf_path, dpi=dpi)
            return images
        except Exception as e:
            raise RuntimeError(f"Failed to convert PDF to images: {str(e)}")

    def image_to_text(self, image: Image.Image, lang: str = 'eng') -> str:
        """
        Extract text from image using Tesseract OCR.

        Args:
            image: PIL Image object
            lang: Tesseract language code (eng, afr for Afrikaans, etc.)

        Returns:
            Extracted text
        """
        try:
            # Use custom config for better table extraction
            custom_config = r'--oem 3 --psm 6'  # PSM 6 = Assume uniform block of text
            text = pytesseract.image_to_string(image, lang=lang, config=custom_config)
            return text
        except Exception as e:
            raise RuntimeError(f"OCR failed: {str(e)}")

    def process_pdf_with_ocr(
        self,
        pdf_path: str,
        dpi: int = 300,
        lang: str = 'eng'
    ) -> List[str]:
        """
        Complete OCR pipeline: PDF → Images → Text extraction.

        Args:
            pdf_path: Path to PDF file
            dpi: Resolution for PDF conversion
            lang: OCR language (eng, afr, etc.)

        Returns:
            List of lines of text extracted from all pages
        """
        # Convert PDF to images
        images = self.pdf_to_images(pdf_path, dpi=dpi)

        # Extract text from each image
        all_lines = []
        for page_num, image in enumerate(images, 1):
            text = self.image_to_text(image, lang=lang)

            if text.strip():
                # Split into lines and add to collection
                lines = text.split('\n')
                all_lines.extend(lines)

        return all_lines

    def is_text_garbled(self, text: str, threshold: float = 0.3) -> bool:
        """
        Heuristic to detect if extracted text is garbled (encoding issues).

        Args:
            text: Text to check
            threshold: Ratio of non-ASCII chars that indicates garbled text

        Returns:
            True if text appears garbled
        """
        if not text:
            return False

        # Count non-ASCII characters
        non_ascii = sum(1 for char in text if ord(char) > 127)
        total = len(text)

        # If more than threshold% are non-ASCII, likely garbled
        if total > 0 and (non_ascii / total) > threshold:
            return True

        # Check for excessive special characters that indicate corruption
        special_chars = sum(1 for char in text if char in '¢†ƒ⁄¶…§•fl¤›ƒ‹fi‡°')
        if total > 0 and (special_chars / total) > 0.1:
            return True

        return False


def extract_text_with_fallback(
    pdf_path: str,
    use_ocr: bool = False,
    auto_detect_garbled: bool = True
) -> List[str]:
    """
    Extract text from PDF with automatic fallback to OCR if needed.

    Args:
        pdf_path: Path to PDF file
        use_ocr: Force OCR usage (skip standard extraction)
        auto_detect_garbled: Automatically detect garbled text and retry with OCR

    Returns:
        List of text lines

    Strategy:
        1. Try standard text extraction first (faster)
        2. If garbled or fails, fall back to OCR
        3. Return best available text
    """
    import pdfplumber

    # Force OCR if requested
    if use_ocr:
        processor = OCRProcessor()
        return processor.process_pdf_with_ocr(pdf_path)

    # Try standard extraction first
    try:
        lines = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    lines.extend(text.split('\n'))

        # Check if text is garbled
        if auto_detect_garbled and lines:
            sample_text = ' '.join(lines[:20])  # Check first 20 lines
            processor = OCRProcessor()

            if processor.is_text_garbled(sample_text):
                print("⚠️  Garbled text detected, falling back to OCR...")
                return processor.process_pdf_with_ocr(pdf_path)

        return lines

    except Exception as e:
        # Standard extraction failed, try OCR
        print(f"⚠️  Standard extraction failed ({str(e)}), trying OCR...")
        processor = OCRProcessor()
        return processor.process_pdf_with_ocr(pdf_path)
