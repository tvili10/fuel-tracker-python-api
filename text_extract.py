from io import BytesIO
from functools import lru_cache
import os
import shutil

from PIL import Image, ImageOps
import pytesseract


@lru_cache(maxsize=1)
def configure_tesseract() -> None:
    tesseract_path = shutil.which("tesseract")
    if tesseract_path:
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
        return

    default_windows_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.exists(default_windows_path):
        pytesseract.pytesseract.tesseract_cmd = default_windows_path


def _prepare(img: Image.Image) -> Image.Image:
    img = ImageOps.exif_transpose(img)   # fix phone rotation
    img = img.convert("L")               # grayscale helps Tesseract
    return img


def extract_text_from_path(image_path: str) -> str:
    try:
        configure_tesseract()
        img = _prepare(Image.open(image_path))
        text = pytesseract.image_to_string(img, lang="hun+eng")
        return text.strip()
    except Exception as e:
        return f"Error: {e}"


def extract_text_from_bytes(image_bytes: bytes) -> str:
    try:
        configure_tesseract()
        img = _prepare(Image.open(BytesIO(image_bytes)))
        text = pytesseract.image_to_string(img, lang="hun+eng")
        return text.strip()
    except Exception as e:
        return f"Error: {e}"