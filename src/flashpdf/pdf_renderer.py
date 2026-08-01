"""Render PDF pages using pikepdf and PyMuPDF (fitz)."""

from __future__ import annotations

import io
from pathlib import Path

import fitz  # type: ignore[import-untyped]
import numpy as np
import pikepdf
from PySide6.QtGui import QImage


class PdfRenderer:
    """Encapsulates PDF rendering and native answer-layer visibility handling."""

    def __init__(self) -> None:
        self._path: Path | None = None
        self._page_count: int = 0
        self._doc: fitz.Document | None = None

    def open(self, pdf_path: str | Path) -> None:
        """Open a PDF file for rendering."""
        self.close()
        self._path = Path(pdf_path)
        self._doc = fitz.open(self._path)
        self._page_count = len(self._doc)

    def close(self) -> None:
        """Close the currently open document."""
        if self._doc is not None:
            self._doc.close()
            self._doc = None
        self._path = None
        self._page_count = 0

    @property
    def page_count(self) -> int:
        return self._page_count

    def page_size(self, page_number: int) -> tuple[float, float]:
        """Return the (width, height) of a zero-indexed page in PDF user-space points."""
        if self._doc is None or not (0 <= page_number < self._page_count):
            return 0.0, 0.0
        rect = self._doc[page_number].rect
        return rect.width, rect.height

    def extract_text_in_rect(
        self, page_number: int, rect: tuple[float, float, float, float]
    ) -> str:
        """Extract plain text within a top-left origin bounding rectangle (x1, y1, x2, y2)."""
        if self._doc is None or not (0 <= page_number < self._page_count):
            return ""
        page = self._doc[page_number]
        x1, y1, x2, y2 = rect
        fitz_rect = fitz.Rect(
            min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)
        )
        return page.get_text("text", clip=fitz_rect).strip()

    def render_page(
        self,
        page_number: int,
        scale: float = 1.0,
        visible_answers: set[str] | None = None,
        dark_mode: bool = False,
    ) -> QImage:
        """Render a zero-indexed page to a QImage at the specified zoom scale.

        If ``visible_answers`` contains answer field names, their annotation hidden flags (/F)
        are updated in-memory via pikepdf so their native appearance stream renders directly on the page.
        If ``dark_mode`` is True, applies smart color transformation with smooth anti-aliased red text blending.
        """
        if self._path is None or not (0 <= page_number < self._page_count):
            return QImage()

        visible = visible_answers or set()

        if visible:
            with pikepdf.open(self._path) as pdf:
                page = pdf.pages[page_number]

                # Expand visible set generically using group stems and spatial proximity
                expanded_visible = set(visible)
                for v in visible:
                    target_rect = None
                    for a in page.get("/Annots", []):
                        if str(a.get("/T", "")) == v and a.get("/Rect"):
                            target_rect = [float(x) for x in a.get("/Rect")]
                            break

                    stems = set()
                    if len(v) >= 4 and v[-1].isdigit() and v[-2].isdigit():
                        stems.add(v[:-2])
                        stems.add(v[:-1])
                    elif len(v) >= 3 and v[-1].isdigit():
                        stems.add(v[:-1])
                    else:
                        stems.add(v.rstrip("0123456789"))

                    for annot in page.get("/Annots", []):
                        name = str(annot.get("/T", ""))
                        flags = int(annot.get("/F", 0))
                        if not name:
                            continue
                        if flags & 32:  # hidden bit
                            if any(name.startswith(s) for s in stems if s):
                                expanded_visible.add(name)
                                continue
                            if target_rect and annot.get("/Rect"):
                                r = [float(x) for x in annot.get("/Rect")]
                                v_overlap = max(
                                    0, min(target_rect[3], r[3]) - max(target_rect[1], r[1])
                                )
                                if v_overlap > 5 or (
                                    abs(target_rect[1] - r[1]) < 60
                                    and abs(target_rect[3] - r[3]) < 60
                                ):
                                    expanded_visible.add(name)

                for annot in page.get("/Annots", []):
                    name = str(annot.get("/T", ""))
                    if name and "/F" in annot:
                        current_f = int(annot["/F"])
                        if name in expanded_visible:
                            annot["/F"] = current_f & ~32  # clear hidden bit
                        elif current_f & 32:
                            annot["/F"] = current_f | 32  # keep hidden

                buf = io.BytesIO()
                pdf.save(buf)
                pdf_bytes = buf.getvalue()

            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            page_obj = doc[page_number]
            matrix = fitz.Matrix(scale, scale)
            pix = page_obj.get_pixmap(matrix=matrix, alpha=False)
            doc.close()
        else:
            page_obj = self._doc[page_number]
            matrix = fitz.Matrix(scale, scale)
            pix = page_obj.get_pixmap(matrix=matrix, alpha=False)

        if dark_mode:
            arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                (pix.height, pix.width, 3)
            ).astype(np.float32)

            dark_bg = np.array([30.0, 32.0, 38.0])
            coral_red = np.array([255.0, 90.0, 90.0])

            # Luminance mapping: white page bg -> dark slate bg, black text -> white text
            luma = (0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]) / 255.0

            output = np.zeros_like(arr)
            for c in range(3):
                output[:, :, c] = dark_bg[c] * luma + 235.0 * (1.0 - luma)

            # Red dominance for smooth anti-aliased edge blending
            max_gb = np.maximum(arr[:, :, 1], arr[:, :, 2])
            red_dominance = np.maximum(0.0, arr[:, :, 0] - max_gb) / 255.0
            r_weight = np.clip(red_dominance * 2.5, 0.0, 1.0)

            for c in range(3):
                output[:, :, c] = (1.0 - r_weight) * output[:, :, c] + r_weight * coral_red[c]

            out_bytes = np.clip(output, 0, 255).astype(np.uint8)

            image = QImage(
                out_bytes.data,
                pix.width,
                pix.height,
                pix.stride,
                QImage.Format.Format_RGB888,
            )
            return image.copy()

        image = QImage(
            pix.samples,
            pix.width,
            pix.height,
            pix.stride,
            QImage.Format.Format_RGB888,
        )
        return image.copy()

    def render_thumbnail(self, page_number: int, max_height: int = 150) -> QImage:
        """Render a small thumbnail QImage of a page for sidebar navigation."""
        if self._doc is None or not (0 <= page_number < self._page_count):
            return QImage()
        page = self._doc[page_number]
        rect = page.rect
        scale = max_height / rect.height if rect.height > 0 else 0.2
        matrix = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        image = QImage(
            pix.samples,
            pix.width,
            pix.height,
            pix.stride,
            QImage.Format.Format_RGB888,
        )
        return image.copy()
