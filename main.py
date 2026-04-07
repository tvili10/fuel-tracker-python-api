from pathlib import Path

import logging
import os
import threading
import time

import requests
from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent
load_dotenv(_ROOT / ".env")

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from ai_parse import parse_receipt_ocr
from text_extract import extract_text_from_bytes, extract_text_from_path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Fuel Tracker API")

# Lets a separate local dev UI (other port) call this API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FIXED_IMAGE = Path(__file__).resolve().parent / "assets" / "fourth.png"
TIME_BETWEEN_PINGS_TO_BACKEND_SERVICE = 60


def ping_backend_service_forever():
    backend_url = os.environ.get("BACKEND_SERVICE_URL")
    if not backend_url:
        logger.warning("BACKEND_SERVICE_URL is not set; skipping backend ping loop.")
        return

    ping_url = f"{backend_url}/ping"
    logger.info("Starting backend ping loop: %s", ping_url)

    while True:
        try:
            response = requests.get(ping_url, timeout=10)
            if response.status_code == 200:
                logger.info("Ping to backend service successful")
            else:
                logger.warning(
                    "Ping to backend service failed (status=%s)",
                    response.status_code,
                )
        except requests.RequestException as exc:
            logger.warning("Ping to backend service unreachable: %s", exc)
        time.sleep(TIME_BETWEEN_PINGS_TO_BACKEND_SERVICE)


@app.on_event("startup")
def start_ping_thread():
    thread = threading.Thread(target=ping_backend_service_forever, daemon=True)
    thread.start()
    logger.info("Background backend ping thread started.")


@app.get("/")
def read_root():
    return {"message": "Fuel Tracker API"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/test/extract-text")
def extract_text():
    """OCR for `assets/forth.png` only (fixed path)."""
    if not FIXED_IMAGE.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"Image not found: {FIXED_IMAGE}",
        )
    text = extract_text_from_path(str(FIXED_IMAGE))
    if text.startswith("Error:"):
        raise HTTPException(status_code=422, detail=text)

    return {"text": text, "source": FIXED_IMAGE.name}


@app.post("/extract-entry-data")
async def extract_entry_data(image: UploadFile = File(...)):
    """OCR on the uploaded image."""
    if image.content_type is None or not image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Upload an image file (e.g. PNG, JPEG).",
        )
    data = await image.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file.")

    text = extract_text_from_bytes(data)
    if text.startswith("Error:"):
        raise HTTPException(status_code=422, detail=text)

    try:
        parsed = parse_receipt_ocr(text)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    return {
        "parsed": {
            "cost": parsed.get("cost"),
            "fuel_quantity": parsed.get("fuel_quantity"),
            "cost_currency": parsed.get("cost_currency"),
            "fuel_unit": parsed.get("fuel_unit"),
        },
    }



if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
