"""Headless FastAPI Server for FlashPDF Reader (Cloud & Web Deployment)."""

import io
from pathlib import Path
from tempfile import gettempdir
from typing import Annotated

import fitz  # PyMuPDF
import numpy as np
import pikepdf
from fastapi import FastAPI, File, HTTPException, Query, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.flashpdf.annotation_parser import (
    parse_answer_layers,
    parse_hide_actions,
    parse_speaker_annotations,
)
from src.flashpdf.asset_extractor import extract_embedded_assets

app = FastAPI(title="FlashPDF Reader Web Engine")

# Enable CORS for browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root PDF Search Directory
WORKSPACE_DIR = Path(__file__).parent.resolve()
AUDIO_CACHE_DIR = Path(gettempdir()) / "flashpdf_audio_cache"
AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# In-memory Document Cache
DOC_CACHE: dict[str, fitz.Document] = {}


def get_pdf_path(pdf_name: str) -> Path:
    """Find PDF file in workspace directory."""
    path = WORKSPACE_DIR / pdf_name
    if not path.exists() or path.suffix.casefold() != ".pdf":
        # Check subdirectories
        matches = list(WORKSPACE_DIR.glob(f"**/{pdf_name}"))
        if matches:
            return matches[0]
        raise HTTPException(status_code=404, detail=f"PDF '{pdf_name}' not found.")
    return path


@app.get("/api/pdfs")
def list_pdfs() -> list[str]:
    """List all available PDF textbooks in the project."""
    pdf_files = [p.name for p in WORKSPACE_DIR.glob("*.pdf")]
    return sorted(pdf_files)


@app.get("/api/open")
def open_pdf(pdf: str) -> dict:
    """Open PDF document and extract embedded audio assets."""
    pdf_path = get_pdf_path(pdf)
    if pdf not in DOC_CACHE:
        DOC_CACHE[pdf] = fitz.open(pdf_path)

    doc = DOC_CACHE[pdf]

    # Extract audio assets to cache directory
    extracted = extract_embedded_assets(pdf_path, cache_dir=AUDIO_CACHE_DIR)
    extracted_audio = [asset.name for asset in extracted]

    return {
        "pdf": pdf_path.name,
        "total_pages": len(doc),
        "extracted_audio": extracted_audio,
    }


@app.post("/api/upload")
def upload_pdf(file: UploadFile = File(...)) -> dict:
    """Upload a custom PDF file, save it to the server, and extract interactive assets."""
    if not file.filename or not file.filename.casefold().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    save_path = WORKSPACE_DIR / file.filename
    with open(save_path, "wb") as f:
        f.write(file.file.read())

    # Open document and extract assets
    DOC_CACHE[file.filename] = fitz.open(save_path)
    extracted = extract_embedded_assets(save_path, cache_dir=AUDIO_CACHE_DIR)
    extracted_audio = [asset.name for asset in extracted]

    return {
        "pdf": file.filename,
        "total_pages": len(DOC_CACHE[file.filename]),
        "extracted_audio": extracted_audio,
    }


@app.get("/api/page")
def render_page(
    pdf: str,
    page: int = 0,
    scale: float = 1.5,
    dark: bool = False,
    visible: Annotated[list[str] | None, Query()] = None,
) -> Response:
    """Render a zero-indexed page to a PNG image with zoom, dark mode, and revealed answer layers."""
    pdf_path = get_pdf_path(pdf)
    visible_set = set(visible or [])

    if visible_set:
        # Update hidden flag (/F) in memory via pikepdf
        with pikepdf.open(pdf_path) as pdf_doc:
            page_obj = pdf_doc.pages[page]

            expanded_visible = set(visible_set)
            for v in visible_set:
                stems = set()
                if len(v) >= 4 and v[-1].isdigit() and v[-2].isdigit():
                    stems.add(v[:-2])
                    stems.add(v[:-1])
                elif len(v) >= 3 and v[-1].isdigit():
                    stems.add(v[:-1])
                else:
                    stems.add(v.rstrip("0123456789"))

                for annot in page_obj.get("/Annots", []):
                    name = str(annot.get("/T", ""))
                    if not name:
                        continue
                    if any(name.startswith(s) for s in stems if s):
                        expanded_visible.add(name)

            for annot in page_obj.get("/Annots", []):
                name = str(annot.get("/T", ""))
                if name and "/F" in annot:
                    current_f = int(annot["/F"])
                    if name in expanded_visible:
                        annot["/F"] = current_f & ~32  # clear hidden bit
                    elif current_f & 32:
                        annot["/F"] = current_f | 32

            buf = io.BytesIO()
            pdf_doc.save(buf)
            pdf_bytes = buf.getvalue()

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        fitz_page = doc[page]
        matrix = fitz.Matrix(scale, scale)
        pix = fitz_page.get_pixmap(matrix=matrix, alpha=False)
        doc.close()
    else:
        if pdf not in DOC_CACHE:
            DOC_CACHE[pdf] = fitz.open(pdf_path)
        doc = DOC_CACHE[pdf]
        if not (0 <= page < len(doc)):
            raise HTTPException(status_code=400, detail="Page index out of bounds")
        fitz_page = doc[page]
        matrix = fitz.Matrix(scale, scale)
        pix = fitz_page.get_pixmap(matrix=matrix, alpha=False)

    if dark:
        arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
            (pix.height, pix.width, 3)
        ).astype(np.float32)

        dark_bg = np.array([30.0, 32.0, 38.0])
        coral_red = np.array([255.0, 90.0, 90.0])

        luma = (0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]) / 255.0

        output = np.zeros_like(arr)
        for c in range(3):
            output[:, :, c] = dark_bg[c] * luma + 235.0 * (1.0 - luma)

        max_gb = np.maximum(arr[:, :, 1], arr[:, :, 2])
        red_dominance = np.maximum(0.0, arr[:, :, 0] - max_gb) / 255.0
        r_weight = np.clip(red_dominance * 2.5, 0.0, 1.0)

        for c in range(3):
            output[:, :, c] = (1.0 - r_weight) * output[:, :, c] + r_weight * coral_red[c]

        out_bytes = np.clip(output, 0, 255).astype(np.uint8)

        # Convert array to PNG via PyMuPDF
        dark_pix = fitz.Pixmap(fitz.csRGB, pix.width, pix.height, out_bytes.tobytes(), False)
        png_data = dark_pix.tobytes("png")
    else:
        png_data = pix.tobytes("png")

    return Response(content=png_data, media_type="image/png")


@app.get("/api/interactivity")
def get_interactivity(pdf: str, page: int = 0) -> dict:
    """Return speaker annotations and answer overlay layers for a specific page."""
    pdf_path = get_pdf_path(pdf)
    if pdf not in DOC_CACHE:
        DOC_CACHE[pdf] = fitz.open(pdf_path)
    doc = DOC_CACHE[pdf]
    
    if not (0 <= page < len(doc)):
        raise HTTPException(status_code=400, detail="Page index out of bounds")

    fitz_page = doc[page]
    page_rect = fitz_page.rect
    page_w, page_h = page_rect.width, page_rect.height

    # Parse 1-indexed page annotations
    page_1based = page + 1
    speakers = parse_speaker_annotations(pdf_path)
    answers = parse_answer_layers(pdf_path)
    hides = parse_hide_actions(pdf_path)

    page_speakers = [
        {
            "rect": list(s.rect),  # [x1, y1, x2, y2]
            "audio": s.audio,
            "button_name": s.button_name,
        }
        for s in speakers
        if s.page == page_1based
    ]

    page_answers = [
        {
            "rect": list(a.rect),
            "field_name": a.field_name,
            "hidden": a.hidden,
        }
        for a in answers
        if a.page == page_1based
    ]

    page_hides = [
        {
            "rect": list(h.rect),
            "button_name": h.button_name,
            "target_field": h.target_field,
            "hide": h.hide,
        }
        for h in hides
        if h.page == page_1based
    ]

    return {
        "page": page,
        "page_size": [page_w, page_h],
        "speakers": page_speakers,
        "answers": page_answers,
        "hide_actions": page_hides,
    }


@app.get("/api/audio/{filename}")
def get_audio(filename: str) -> Response:
    """Stream extracted MP3 audio file."""
    audio_path = AUDIO_CACHE_DIR / filename
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    with open(audio_path, "rb") as f:
        audio_bytes = f.read()

    return Response(content=audio_bytes, media_type="audio/mpeg")


# Serve static web frontend
static_dir = WORKSPACE_DIR / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
