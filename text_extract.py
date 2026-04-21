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


def _ocr_settings() -> tuple[str, str]:
    lang = "eng"
    tesseract_config = (
        os.environ.get(
            "OCR_TESSERACT_CONFIG",
            "--oem 1 --psm 6 -c load_system_dawg=0 -c load_freq_dawg=0",
        ).strip()
        or "--oem 1 --psm 6 -c load_system_dawg=0 -c load_freq_dawg=0"
    )
    return lang, tesseract_config


def _prepare(img: Image.Image) -> Image.Image:
    img = ImageOps.exif_transpose(img)   # fix phone rotation
    max_side = 1200
    if max(img.size) > max_side:
        img.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    img = img.convert("L")               # grayscale helps Tesseract
    return img


def _extract_text(img: Image.Image) -> str:
    lang, tesseract_config = _ocr_settings()
    return pytesseract.image_to_string(
        img,
        lang=lang,
        config=tesseract_config,
    )


def extract_text_from_path(image_path: str) -> str:
    try:
        configure_tesseract()
        img = _prepare(Image.open(image_path))
        text = _extract_text(img)
        return text.strip()
    except Exception as e:
        return f"Error: {e}" 


def extract_text_from_bytes(image_bytes: bytes) -> str:
    try:
        configure_tesseract()
        img = _prepare(Image.open(BytesIO(image_bytes)))
        text = _extract_text(img)
        return text.strip()
    except Exception as e:
        return f"Error: {e}"