from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent
load_dotenv(_ROOT / ".env")

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from ai_parse import parse_receipt_ocr
from text_extract import extract_text_from_bytes, extract_text_from_path

app = FastAPI(title="Fuel Tracker API")

# Lets a separate local dev UI (other port) call this API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FIXED_IMAGE = Path(__file__).resolve().parent / "assets" / "fourth.png"


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

    # 0.0.0.0: reachable from other devices on your LAN (e.g. phone on same Wi‑Fi).
    uvicorn.run(app, host="0.0.0.0", port=8000)
