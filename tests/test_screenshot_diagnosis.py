"""Tests for ai_core/screenshot_diagnosis.py's graceful degradation.

pytesseract + the Tesseract binary are optional (requirements-vision.txt).
This module must never raise or return misleading data when they're
missing — every caller checks for None and shows a clear message instead.
"""
import base64
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ai_core.screenshot_diagnosis import extract_text_from_image, is_available


def test_extract_text_returns_none_on_garbage_input():
    # Not valid image bytes at all — must degrade to None, not raise.
    fake_b64 = base64.b64encode(b"not an image").decode()
    assert extract_text_from_image(fake_b64) is None


def test_extract_text_handles_data_url_prefix():
    fake_b64 = base64.b64encode(b"not an image").decode()
    data_url = f"data:image/png;base64,{fake_b64}"
    # Should not raise even though it's not a real image — OCR/decoding
    # failure must still degrade to None.
    assert extract_text_from_image(data_url) is None


def test_is_available_returns_bool():
    assert isinstance(is_available(), bool)
