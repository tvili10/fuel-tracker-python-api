"""Image-to-text via Tesseract (same idea as text_extractor_first_try/script.py)."""

from io import BytesIO
import os
import shutil

from PIL import Image
import pytesseract


def configure_tesseract() -> None:
    tesseract_path = shutil.which("tesseract")
    if tesseract_path:
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
        return

    default_windows_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.exists(default_windows_path):
        pytesseract.pytesseract.tesseract_cmd = default_windows_path


def extract_text_from_path(image_path: str) -> str:
    try:
        configure_tesseract()
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img)
        return text.strip()
    except Exception as e:
        return f"Error: {e}"


def extract_text_from_bytes(image_bytes: bytes) -> str:
    try:
        configure_tesseract()
        img = Image.open(BytesIO(image_bytes))
        text = pytesseract.image_to_string(img)
        return text.strip()
    except Exception as e:
        return f"Error: {e}"
