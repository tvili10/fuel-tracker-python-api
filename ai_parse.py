"""Turn noisy OCR receipt text into structured fields via Google Gemini."""

from __future__ import annotations

import json
import os
from typing import Any

from google import genai
from google.genai import types

SYSTEM_PROMPT = """You extract structured data from noisy OCR text of a fuel / gas receipt.
Respond with a single JSON object and nothing else. Use only these keys:
- "cost": number or null — total amount paid (one number, no currency symbols in the value)
- "fuel_quantity": number or null — volume of fuel (one number)
- "cost_currency": string or null — ISO-style currency if inferable (e.g. "HUF", "EUR", "USD")
- "fuel_unit": string or null — "L" or "gal" or similar if inferable from the text

If something cannot be determined from the text, use null. Do not guess or invent amounts."""


def parse_receipt_ocr(ocr_text: str) -> dict[str, Any]:
    print(ocr_text)
    api_key = (
        os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY") or ""
    ).strip()
    if not api_key:
        raise RuntimeError(
            "Set GOOGLE_API_KEY (or GEMINI_API_KEY) from Google AI Studio to enable parsing."
        )

    model_name = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash").strip()

    prompt = f"{SYSTEM_PROMPT}\n\nOCR text:\n\n{ocr_text}"
    with genai.Client(api_key=api_key) as client:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0,
            ),
        )
    raw = (response.text or "").strip()
    if not raw:
        raise ValueError("Empty model response")
    print("Raw response: ", raw)
    data = json.loads(raw)
    for key in ("cost", "fuel_quantity", "cost_currency", "fuel_unit"):
        if key not in data:
            data[key] = None
    print("JSON parsed: ", data)
    return data
