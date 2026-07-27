"""
AI Rescue USB - Screenshot diagnosis
======================================
Lets the user upload a photo/screenshot of an error screen (BSOD, error
dialog, boot message) instead of having to type the error code by hand.
Runs OCR to pull out the text, then feeds it into the same diagnosis path
as a typed symptom description.

Needs pytesseract (pip) + the Tesseract binary (system package, not pip —
see requirements-vision.txt). Degrades to a clear "not available" message
if either is missing, same graceful-degradation pattern as the LLM.
"""
import base64
import io
import logging
from typing import Optional

log = logging.getLogger("screenshot-diagnosis")


def is_available() -> bool:
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def extract_text_from_image(image_data: str) -> Optional[str]:
    """Decode a base64 image (optionally with a data: URL prefix) and OCR it.

    Returns None if OCR isn't available or extraction fails/finds nothing —
    callers must handle that explicitly rather than assume success.
    """
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        log.info("pytesseract/Pillow not installed — screenshot diagnosis unavailable")
        return None

    try:
        if "," in image_data and image_data.strip().startswith("data:"):
            image_data = image_data.split(",", 1)[1]
        image_bytes = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(image)
        text = text.strip()
        return text or None
    except Exception as e:
        log.warning(f"OCR extraction failed: {e}")
        return None
