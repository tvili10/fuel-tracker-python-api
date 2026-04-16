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


@app.get("/")
def read_root():
    return {"message": "Fuel Tracker API"}


@app.api_route("/health", methods=["GET", "HEAD"])
def health():
    print("Health check")
    return {"status": "ok"}

@app.post("/extract-entry-data")
async def extract_entry_data(image: UploadFile = File(...)):
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
            "receipt_date": parsed.get("receipt_date"),
        },
    }



if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
