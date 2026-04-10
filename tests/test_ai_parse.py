import pytest

from ai_parse import parse_receipt_ocr


def test_parse_receipt_ocr_requires_api_key(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with pytest.raises(RuntimeError) as exc:
        parse_receipt_ocr("Total: 100")

    assert "Set GOOGLE_API_KEY" in str(exc.value)
