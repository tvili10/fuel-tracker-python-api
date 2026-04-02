from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from text_extract import extract_text_from_path

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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
