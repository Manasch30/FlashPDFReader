"""Tests for FastAPI web server endpoints."""

from pathlib import Path

from fastapi.testclient import TestClient

from flashpdf.web_server import app

client = TestClient(app)
SAMPLE_PDF = "Lesson 1-3.pdf"


def test_list_pdfs() -> None:
    response = client.get("/api/pdfs")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_open_pdf() -> None:
    if not Path(SAMPLE_PDF).exists():
        return
    response = client.get(f"/api/open?pdf={SAMPLE_PDF}")
    assert response.status_code == 200
    data = response.json()
    assert "total_pages" in data
    assert data["total_pages"] > 0
    assert "speaker_annotations" in data


def test_render_page_endpoint() -> None:
    if not Path(SAMPLE_PDF).exists():
        return
    response = client.get(f"/api/page?pdf={SAMPLE_PDF}&page=0&scale=1.0")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert len(response.content) > 0


def test_render_thumbnail_endpoint() -> None:
    if not Path(SAMPLE_PDF).exists():
        return
    response = client.get(f"/api/thumbnail?pdf={SAMPLE_PDF}&page=0")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"


def test_index_page() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "FlashPDF Web Reader" in response.text
