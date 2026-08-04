"""Tests for the headless FastAPI cloud web server."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

import pytest
from fastapi.testclient import TestClient

from server import app

client = TestClient(app)

def test_list_pdfs():
    response = client.get("/api/pdfs")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(p.endswith(".pdf") for p in data)

def test_open_pdf():
    pdfs_resp = client.get("/api/pdfs")
    pdf_list = pdfs_resp.json()
    assert len(pdf_list) > 0
    pdf_name = pdf_list[0]

    response = client.get(f"/api/open?pdf={pdf_name}")
    assert response.status_code == 200
    data = response.json()
    assert "total_pages" in data
    assert data["total_pages"] > 0
    assert "extracted_audio" in data

def test_render_page_and_interactivity():
    pdfs_resp = client.get("/api/pdfs")
    pdf_name = pdfs_resp.json()[0]

    # Test page image rendering
    img_resp = client.get(f"/api/page?pdf={pdf_name}&page=0&scale=1.0&dark=true")
    assert img_resp.status_code == 200
    assert img_resp.headers["content-type"] == "image/png"
    assert len(img_resp.content) > 100

    # Test interactivity metadata
    inter_resp = client.get(f"/api/interactivity?pdf={pdf_name}&page=0")
    assert inter_resp.status_code == 200
    data = inter_resp.json()
    assert "speakers" in data
    assert "answers" in data
    assert "page_size" in data
