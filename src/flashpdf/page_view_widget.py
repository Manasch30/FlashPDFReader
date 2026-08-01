"""Widget displaying a rendered PDF page along with interactive audio and answer overlays."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QMouseEvent, QPixmap
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QWidget

from .audio_player import AudioPlayer
from .models import AnswerLayer, HideActionAnnotation, SpeakerAnnotation
from .pdf_renderer import PdfRenderer


class PageViewWidget(QWidget):
    """Encapsulates a single rendered PDF page with overlays and text selection."""

    def __init__(
        self,
        page_number: int,
        renderer: PdfRenderer,
        annotations: list[SpeakerAnnotation],
        answer_layers: list[AnswerLayer],
        hide_actions: list[HideActionAnnotation],
        visible_answers: set[str],
        assets: dict[str, Path],
        audio_player: AudioPlayer,
        zoom: float,
        toggle_callback: Callable[[HideActionAnnotation], None],
        status_callback: Callable[[str], None] | None = None,
        dark_mode: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._page_number = page_number
        self._renderer = renderer
        self._annotations = annotations
        self._answer_layers = answer_layers
        self._hide_actions = hide_actions
        self._visible_answers = visible_answers
        self._assets = assets
        self._audio = audio_player
        self._zoom = zoom
        self._toggle_callback = toggle_callback
        self._status_callback = status_callback
        self._dark_mode = dark_mode

        self._selection_start: QPoint | None = None
        self._selection_overlay: QLabel | None = None

        self._page_label = QLabel(self)
        self._page_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.update_page(self._zoom, self._visible_answers, self._dark_mode)

    @property
    def page_number(self) -> int:
        return self._page_number

    def update_page(
        self, zoom: float, visible_answers: set[str], dark_mode: bool = False
    ) -> None:
        """Re-render the page pixmap and update overlay geometry."""
        self._zoom = zoom
        self._visible_answers = visible_answers
        self._dark_mode = dark_mode

        self._clear_selection()
        image = self._renderer.render_page(
            self._page_number,
            self._zoom,
            visible_answers=self._visible_answers,
            dark_mode=self._dark_mode,
        )
        self._page_label.setPixmap(QPixmap.fromImage(image))
        self._page_label.setFixedSize(image.size())
        self.setFixedSize(image.size())

        self._clear_overlays()
        self._add_interactive_overlays()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Start drag rectangle selection for text extraction."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._clear_selection()
            self._selection_start = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Update active text selection visual rectangle while dragging."""
        if self._selection_start is not None and (event.buttons() & Qt.MouseButton.LeftButton):
            rect = QRect(self._selection_start, event.pos()).normalized()
            if rect.width() > 4 and rect.height() > 4:
                if self._selection_overlay is None:
                    self._selection_overlay = QLabel(self)
                    self._selection_overlay.setStyleSheet(
                        "background: rgba(66, 133, 244, 90); border: 1px solid #1a73e8;"
                    )
                self._selection_overlay.setGeometry(rect)
                self._selection_overlay.show()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Complete text selection and copy extracted text to system clipboard."""
        if event.button() == Qt.MouseButton.LeftButton and self._selection_start is not None:
            rect = QRect(self._selection_start, event.pos()).normalized()
            self._selection_start = None

            if rect.width() > 6 and rect.height() > 6:
                pdf_left = rect.left() / self._zoom
                pdf_top = rect.top() / self._zoom
                pdf_right = rect.right() / self._zoom
                pdf_bottom = rect.bottom() / self._zoom

                extracted_text = self._renderer.extract_text_in_rect(
                    self._page_number, (pdf_left, pdf_top, pdf_right, pdf_bottom)
                )

                if extracted_text:
                    clipboard = QApplication.clipboard()
                    if clipboard:
                        clipboard.setText(extracted_text)
                    preview = extracted_text.replace("\n", " ")
                    if len(preview) > 60:
                        preview = preview[:57] + "..."
                    msg = f"Copied to clipboard: \"{preview}\""
                    if self._status_callback:
                        self._status_callback(msg)
                else:
                    if self._status_callback:
                        self._status_callback("No text found in selection.")

        super().mouseReleaseEvent(event)

    def _clear_selection(self) -> None:
        if self._selection_overlay is not None:
            self._selection_overlay.deleteLater()
            self._selection_overlay = None

    def _clear_overlays(self) -> None:
        for button in self.findChildren(QPushButton):
            button.deleteLater()

    def _add_interactive_overlays(self) -> None:
        _, page_height = self._renderer.page_size(self._page_number)

        # Render speaker audio overlays
        for annotation in self._annotations:
            audio_path = self._assets.get(annotation.audio)
            if audio_path is None:
                continue
            x1, y1, x2, y2 = annotation.rect
            left, right = sorted((x1, x2))
            bottom, top = sorted((y1, y2))
            button = QPushButton("🔊", self)
            button.setToolTip(f"Play {annotation.audio}")
            button.setCursor(Qt.CursorShape.PointingHandCursor)

            spk_bg = "rgba(45, 140, 240, 220)" if self._dark_mode else "rgba(35, 125, 210, 200)"
            button.setStyleSheet(
                f"background: {spk_bg}; color: white; border: 1px solid rgba(255,255,255,100); border-radius: 10px;"
            )
            button.clicked.connect(lambda checked=False, path=audio_path: self._audio.play(path))
            button.setGeometry(
                round(left * self._zoom),
                round((page_height - top) * self._zoom),
                max(20, round((right - left) * self._zoom)),
                max(20, round((top - bottom) * self._zoom)),
            )
            button.show()

        # Render Show/Hide answer toggle button overlays
        for hide_action in self._hide_actions:
            x1, y1, x2, y2 = hide_action.rect
            left, right = sorted((x1, x2))
            bottom, top = sorted((y1, y2))
            is_hide = hide_action.hide
            target_field = hide_action.target_field

            is_currently_visible = target_field in self._visible_answers

            if not is_hide and is_currently_visible:
                continue
            if is_hide and not is_currently_visible:
                continue

            label = "❌ Close" if is_hide else "💡 Answer"
            bg = "rgba(220, 50, 50, 210)" if is_hide else "rgba(40, 160, 70, 210)"
            tooltip = (
                f"Hide answer field '{target_field}'"
                if is_hide
                else f"Show answer field '{target_field}'"
            )

            button = QPushButton(label, self)
            button.setToolTip(tooltip)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setStyleSheet(
                f"background: {bg}; color: white; font-weight: bold; border: 0; border-radius: 4px; padding: 2px;"
            )
            button.clicked.connect(
                lambda checked=False, act=hide_action: self._toggle_callback(act)
            )
            button.setGeometry(
                round(left * self._zoom),
                round((page_height - top) * self._zoom),
                max(40, round((right - left) * self._zoom)),
                max(22, round((top - bottom) * self._zoom)),
            )
            button.show()
