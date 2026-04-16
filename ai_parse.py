"""Turn noisy OCR receipt text into structured fields via Google Gemini."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import Any

from google import genai
from google.genai import types

SYSTEM_PROMPT = SYSTEM_PROMPT = """You extract structured data from noisy OCR text of a fuel/gas receipt.
The receipt may be in any language (Hungarian, German, Romanian, Slovak, etc.).
Respond with a single JSON object and nothing else. No markdown, no backticks, no explanation.

Keys:
- "cost": number or null — the final total paid. Look for keywords like:
  "ÖSSZESEN", "OSSZESEN", "TOTAL", "GESAMT", "SUMME", "TOTAAL", "SUMA", "CELKEM", "ИТОГО", "MONTANT"
  or payment method lines like "BANKKARTYA", "CARD", "KARTE", "CASH", "BARGELD".
  Use the largest clearly identified final total. Never use subtotals, discounts, or foreign currency conversion lines.

- "fuel_quantity": number or null — volume of fuel pumped. Look for a number near units like
  "L", "LTR", "LITER", "LITRE", "GAL", "GALLON" or near fuel type words like
  "BENZIN", "BENZINE", "PETROL", "GASOLINE", "DIESEL", "GAZOLAJ", "NAFTA", "ESSENCE".
  OCR often garbles decimals — treat both comma and period as possible decimal separators.
  A space or apostrophe inside a number is a thousands separator, not a decimal: "21 320" = 21320, "21,320" = 21.32.
  Use context (realistic fuel quantities are 5–120 litres) to pick the correct interpretation.
  If you see something like "21340" and it's a valid number, it's probably a mistake, set it to 21.34. Apply this rule to all numbers.


- "cost_currency": string or null — infer from currency symbols or words:
  "Ft", "FT", "forint" → "HUF"
  "€", "EUR" → "EUR" (only if that is the paid currency, not a conversion line)
  "$" → "USD"
  "£" → "GBP"
  "RON", "lei" → "RON"
  "CZK", "Kč" → "CZK"
  "PLN", "zł" → "PLN"
  "CHF" → "CHF"
  Any other symbol → use the ISO 4217 code if inferrable, else null.
  Ignore informational currency conversion lines (e.g. "EUROBAN", "ARFOLYAM", "KURS", "RATE").

- "fuel_unit": string or null — "L" for litres, "gal" for gallons. Infer from the text.

- "receipt_date": string or null — receipt issue date normalized to "YYYY-MM-DD".
  Common formats can appear as:
  "YYYY-MM-DD", "YYYY/MM/DD", "YYYY.MM.DD", "DD.MM.YYYY", "DD/MM/YYYY", "DD-MM-YYYY"
  Return null when no reliable date is visible.

OCR noise rules — correct these before parsing:
- "COO", "C00", "coo" trailing a number = those are zeros: "14 796 COO" → 14796
- "eC00", "eCOO" = discount marker, ignore
- "S"/"s" may be misread "5", "O" may be misread "0", "l" may be misread "1", "I" may be "1"
- Spaces inside numbers are thousands separators: "25 413" = 25413
- Ignore any line containing conversion keywords: "EUROBAN", "ARFOLYAM", "KURS", "RATE", "EXCHANGE"

Realistic sanity checks:
- Fuel quantity should be between 1 and 200 litres (or 0.3–50 gallons)
- Cost should be a plausible fuel purchase amount for the currency
- If a value fails the sanity check, set it to null rather than returning a garbage value.

If something cannot be determined, use null. Do not guess or invent values."""


def _normalize_receipt_date(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    # Already normalized or close to normalized.
    for candidate in (
        text,
        text.replace("/", "-"),
        text.replace(".", "-"),
    ):
        try:
            return datetime.strptime(candidate, "%Y-%m-%d").date().isoformat()
        except ValueError:
            continue

    # Extract likely date-like token from noisy text.
    match = re.search(r"(\d{1,4}[./-]\d{1,2}[./-]\d{1,4})", text)
    if not match:
        return None

    token = match.group(1)
    for fmt in (
        "%d.%m.%Y",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y.%m.%d",
        "%Y/%m/%d",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(token, fmt).date().isoformat()
        except ValueError:
            continue

    return None


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
    for key in ("cost", "fuel_quantity", "cost_currency", "fuel_unit", "receipt_date"):
        if key not in data:
            data[key] = None
    data["receipt_date"] = _normalize_receipt_date(data.get("receipt_date"))
    print("JSON parsed: ", data)
    return data
