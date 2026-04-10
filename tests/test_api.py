from fastapi.testclient import TestClient

import main


client = TestClient(main.app)


def test_root_returns_message():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "Fuel Tracker API"}


def test_health_returns_ok():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_extract_entry_data_rejects_non_image_upload():
    response = client.post(
        "/extract-entry-data",
        files={"image": ("not-image.txt", b"abc", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Upload an image file (e.g. PNG, JPEG)."


def test_extract_entry_data_rejects_empty_image_upload():
    response = client.post(
        "/extract-entry-data",
        files={"image": ("empty.png", b"", "image/png")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Empty file."


def test_extract_entry_data_returns_422_on_ocr_error(monkeypatch):
    monkeypatch.setattr(main, "extract_text_from_bytes", lambda _: "Error: OCR failed")

    response = client.post(
        "/extract-entry-data",
        files={"image": ("receipt.png", b"fake-image-content", "image/png")},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Error: OCR failed"


def test_extract_entry_data_returns_503_when_parser_unavailable(monkeypatch):
    monkeypatch.setattr(main, "extract_text_from_bytes", lambda _: "Total: 123.45")

    def _raise_runtime_error(_: str):
        raise RuntimeError("Missing API key")

    monkeypatch.setattr(main, "parse_receipt_ocr", _raise_runtime_error)

    response = client.post(
        "/extract-entry-data",
        files={"image": ("receipt.png", b"fake-image-content", "image/png")},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Missing API key"


def test_extract_entry_data_returns_502_when_parser_fails(monkeypatch):
    monkeypatch.setattr(main, "extract_text_from_bytes", lambda _: "Total: 123.45")

    def _raise_error(_: str):
        raise ValueError("Bad AI response")

    monkeypatch.setattr(main, "parse_receipt_ocr", _raise_error)

    response = client.post(
        "/extract-entry-data",
        files={"image": ("receipt.png", b"fake-image-content", "image/png")},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "Bad AI response"


def test_extract_entry_data_returns_structured_result(monkeypatch):
    monkeypatch.setattr(main, "extract_text_from_bytes", lambda _: "Total: 123.45")
    monkeypatch.setattr(
        main,
        "parse_receipt_ocr",
        lambda _: {
            "cost": 123.45,
            "fuel_quantity": 40.3,
            "cost_currency": "HUF",
            "fuel_unit": "L",
            "ignored_extra_key": "value",
        },
    )

    response = client.post(
        "/extract-entry-data",
        files={"image": ("receipt.png", b"fake-image-content", "image/png")},
    )

    assert response.status_code == 200
    assert response.json() == {
        "parsed": {
            "cost": 123.45,
            "fuel_quantity": 40.3,
            "cost_currency": "HUF",
            "fuel_unit": "L",
        }
    }
