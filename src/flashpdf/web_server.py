"""FastAPI web server for Docker containerized FlashPDF Reader."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from PySide6.QtCore import QBuffer, QByteArray, QIODevice

from .annotation_parser import (
    parse_answer_layers,
    parse_hide_actions,
    parse_speaker_annotations,
)
from .asset_extractor import extract_embedded_assets
from .pdf_renderer import PdfRenderer
from .utils import default_cache_dir

PDF_DIR = Path("/app/pdfs") if Path("/app/pdfs").exists() else Path.cwd()

app = FastAPI(title="FlashPDF Reader Web Server")

# Cache open PdfRenderer instances per PDF path
_renderers: dict[str, PdfRenderer] = {}


def get_renderer(pdf_path: Path) -> PdfRenderer:
    key = str(pdf_path.resolve())
    if key not in _renderers:
        renderer = PdfRenderer()
        renderer.open(pdf_path)
        _renderers[key] = renderer
    return _renderers[key]


def _qimage_to_png_bytes(qimage: Any) -> bytes:
    ba = QByteArray()
    buffer = QBuffer(ba)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    qimage.save(buffer, "PNG")
    buffer.close()
    return bytes(ba.data())


@app.get("/api/pdfs")
def list_pdfs() -> list[dict[str, Any]]:
    """List all available PDF files in the PDF directory."""
    pdfs = sorted(PDF_DIR.glob("*.pdf"))
    return [{"name": p.name, "path": str(p)} for p in pdfs]


@app.get("/api/open")
def open_pdf(pdf: str = Query(...)) -> dict[str, Any]:
    """Open a PDF, extract its audio assets, and return interactivity metadata."""
    pdf_path = PDF_DIR / pdf if not Path(pdf).is_absolute() else Path(pdf)
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail=f"PDF file '{pdf}' not found.")

    try:
        renderer = get_renderer(pdf_path)
        cache_dir = default_cache_dir(pdf_path)

        assets = {
            asset.name: str(asset.path)
            for asset in extract_embedded_assets(pdf_path, cache_dir)
            if asset.mime == "audio/mpeg"
        }

        speakers = [
            {
                "page": a.page,
                "rect": a.rect,
                "audio": a.audio,
                "button_name": a.button_name,
            }
            for a in parse_speaker_annotations(pdf_path)
        ]

        answers = [
            {
                "page": a.page,
                "field_name": a.field_name,
                "rect": a.rect,
                "hidden": a.hidden,
            }
            for a in parse_answer_layers(pdf_path)
        ]

        hide_actions = [
            {
                "page": a.page,
                "rect": a.rect,
                "button_name": a.button_name,
                "target_field": a.target_field,
                "hide": a.hide,
            }
            for a in parse_hide_actions(pdf_path)
        ]

        return {
            "name": pdf_path.name,
            "total_pages": renderer.page_count,
            "assets": assets,
            "speaker_annotations": speakers,
            "answer_layers": answers,
            "hide_actions": hide_actions,
        }
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err)) from err


@app.get("/api/page")
def render_page(
    pdf: str = Query(...),
    page: int = Query(0, ge=0),
    scale: float = Query(1.25, gt=0.1, le=4.0),
    answers: str = Query(""),
    dark: bool = Query(False),
) -> Response:
    """Render a zero-indexed PDF page to a PNG image response."""
    pdf_path = PDF_DIR / pdf if not Path(pdf).is_absolute() else Path(pdf)
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF not found.")

    renderer = get_renderer(pdf_path)
    if not (0 <= page < renderer.page_count):
        raise HTTPException(status_code=400, detail="Page index out of bounds.")

    visible_set = set(answers.split(",")) if answers else set()
    qimage = renderer.render_page(
        page, scale=scale, visible_answers=visible_set, dark_mode=dark
    )

    png_bytes = _qimage_to_png_bytes(qimage)
    return Response(content=png_bytes, media_type="image/png")


@app.get("/api/thumbnail")
def render_thumbnail(pdf: str = Query(...), page: int = Query(0, ge=0)) -> Response:
    """Render a thumbnail PNG image of a page for the sidebar."""
    pdf_path = PDF_DIR / pdf if not Path(pdf).is_absolute() else Path(pdf)
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF not found.")

    renderer = get_renderer(pdf_path)
    qimage = renderer.render_thumbnail(page, max_height=140)

    png_bytes = _qimage_to_png_bytes(qimage)
    return Response(content=png_bytes, media_type="image/png")


@app.get("/api/audio")
def get_audio(pdf: str = Query(...), name: str = Query(...)) -> FileResponse:
    """Stream an extracted MP3 audio file."""
    pdf_path = PDF_DIR / pdf if not Path(pdf).is_absolute() else Path(pdf)
    cache_dir = default_cache_dir(pdf_path)
    audio_file = cache_dir / name

    if not audio_file.exists():
        raise HTTPException(status_code=404, detail=f"Audio file '{name}' not found.")

    return FileResponse(path=audio_file, media_type="audio/mpeg", filename=name)


static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    """Serve the main web reader HTML page."""
    index_file = static_dir / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>FlashPDF Reader API Server is Running</h1>")
