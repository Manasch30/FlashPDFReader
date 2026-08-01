"""Main Qt window for reading interactive educational PDFs."""

from __future__ import annotations

import shutil
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction, QIcon, QImage, QKeyEvent, QKeySequence, QPixmap, QWheelEvent
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from .annotation_parser import (
    parse_answer_layers,
    parse_hide_actions,
    parse_speaker_annotations,
)
from .asset_extractor import extract_embedded_assets
from .audio_dialog import AudioDialog
from .audio_player import AudioPlayer
from .models import AnswerLayer, HideActionAnnotation, SpeakerAnnotation
from .page_view_widget import PageViewWidget
from .pdf_renderer import PdfRenderer
from .utils import default_cache_dir

DARK_STYLESHEET = """
QMainWindow { background-color: #1a1a20; color: #e0e0e0; }
QToolBar { background-color: #24242e; border-bottom: 1px solid #333342; spacing: 6px; padding: 4px; }
QToolBar QToolButton { background: #2d2d3a; color: #e0e0e0; border-radius: 4px; padding: 4px 8px; }
QToolBar QToolButton:hover { background: #3c3c4e; }
QListWidget { background-color: #22222b; color: #e0e0e0; border-right: 1px solid #333342; }
QListWidget::item:selected { background-color: #3b4252; color: #ffffff; border-radius: 4px; }
QScrollArea { background-color: #121218; border: none; }
QStatusBar { background-color: #24242e; color: #aaaaaa; }
QSpinBox, QComboBox { background-color: #2d2d3a; color: #ffffff; border: 1px solid #444456; border-radius: 4px; padding: 2px 6px; }
"""


class ZoomableScrollArea(QScrollArea):
    """QScrollArea that supports Ctrl + Mouse Wheel zooming."""

    def __init__(
        self,
        zoom_in_cb: Callable[[], None],
        zoom_out_cb: Callable[[], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._zoom_in_cb = zoom_in_cb
        self._zoom_out_cb = zoom_out_cb

    def wheelEvent(self, event: QWheelEvent) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self._zoom_in_cb()
            elif delta < 0:
                self._zoom_out_cb()
            event.accept()
        else:
            super().wheelEvent(event)


class MainWindow(QMainWindow):
    """A cross-platform viewer for Flash-based interactive educational PDFs."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("FlashPDF Reader")
        self.resize(1200, 850)
        self._renderer = PdfRenderer()
        self._audio = AudioPlayer()
        self._pdf_path: Path | None = None
        self._annotations: dict[int, list[SpeakerAnnotation]] = defaultdict(list)
        self._answer_layers: dict[int, list[AnswerLayer]] = defaultdict(list)
        self._hide_actions: dict[int, list[HideActionAnnotation]] = defaultdict(list)
        self._visible_answers: set[str] = set()
        self._assets: dict[str, Path] = {}
        self._page_number = 0
        self._zoom = 1.25
        self._view_mode: str = "single"  # "single" or "continuous"
        self._dark_mode: bool = False
        self._page_widgets: list[PageViewWidget] = []

        # UI Components
        self._splitter = QSplitter(Qt.Orientation.Horizontal)

        # Thumbnail Sidebar
        self._thumbnail_list = QListWidget()
        self._thumbnail_list.setIconSize(QSize(120, 160))
        self._thumbnail_list.setMaximumWidth(200)
        self._thumbnail_list.setMinimumWidth(120)
        self._thumbnail_list.currentRowChanged.connect(self._on_thumbnail_selected)
        self._splitter.addWidget(self._thumbnail_list)

        # Main Page View Container with Ctrl+Wheel Zooming
        self._scroll_area = ZoomableScrollArea(
            zoom_in_cb=self.zoom_in, zoom_out_cb=self.zoom_out
        )
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._scroll_area.verticalScrollBar().valueChanged.connect(self._on_scroll_position_changed)

        self._view_container = QWidget()
        self._view_layout = QVBoxLayout(self._view_container)
        self._view_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self._view_layout.setContentsMargins(10, 10, 10, 10)
        self._view_layout.setSpacing(15)
        self._scroll_area.setWidget(self._view_container)

        self._splitter.addWidget(self._scroll_area)
        self._splitter.setSizes([170, 1030])
        self.setCentralWidget(self._splitter)

        self._status = self.statusBar()
        self._build_toolbar()

    def open_pdf(self, pdf_path: str | Path, force_reextract: bool = False) -> None:
        """Load a PDF, extract its assets, parse interactive elements, and display page 1."""
        path = Path(pdf_path)
        try:
            self._audio.stop()
            self._renderer.open(path)
            self._pdf_path = path
            cache_dir = default_cache_dir(path)

            if force_reextract and cache_dir.exists():
                shutil.rmtree(cache_dir, ignore_errors=True)

            self._assets = {
                asset.name: asset.path
                for asset in extract_embedded_assets(path, cache_dir)
                if asset.mime == "audio/mpeg"
            }
            self._annotations = defaultdict(list)
            for annotation in parse_speaker_annotations(path):
                self._annotations[annotation.page - 1].append(annotation)

            self._answer_layers = defaultdict(list)
            for layer in parse_answer_layers(path):
                self._answer_layers[layer.page - 1].append(layer)

            self._hide_actions = defaultdict(list)
            for action in parse_hide_actions(path):
                self._hide_actions[action.page - 1].append(action)

            self._visible_answers.clear()
        except Exception as error:  # noqa: BLE001
            self._renderer.close()
            QMessageBox.critical(self, "Could not open PDF", str(error))
            return

        self.setWindowTitle(f"FlashPDF Reader — {path.name}")
        self._page_number = 0
        self._update_page_spinbox_range()
        self._build_thumbnails()
        self._rebuild_page_views()

    def refresh_assets(self) -> None:
        """Force re-extraction of audio assets and re-parsing of annotations."""
        if self._pdf_path:
            self.open_pdf(self._pdf_path, force_reextract=True)
            self._status.showMessage(
                f"Refreshed assets for {self._pdf_path.name} ({len(self._assets)} audio files loaded)"
            )

    def show_audio_inspector(self) -> None:
        """Open the Audio File Inspector dialog."""
        if not self._assets:
            QMessageBox.information(
                self, "Audio Assets", "No extracted audio files found for this document."
            )
            return
        dialog = AudioDialog(self._assets, self._audio, self)
        dialog.exec()

    def choose_pdf(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self, "Open Educational PDF", "", "PDF files (*.pdf)"
        )
        if filename:
            self.open_pdf(filename)

    def toggle_view_mode(self) -> None:
        """Toggle between Single Page Mode and Continuous Scroll Mode."""
        self._view_mode = "continuous" if self._view_mode == "single" else "single"
        self._mode_action.setText("📜 Scroll Mode" if self._view_mode == "single" else "📄 Single Page")
        self._rebuild_page_views()

    def toggle_dark_mode(self) -> None:
        """Toggle between Light Mode and Smart Dark Mode."""
        self._dark_mode = not self._dark_mode
        self._dark_action.setText("☀️ Light Mode" if self._dark_mode else "🌙 Dark Mode")

        app = QApplication.instance()
        if app:
            app.setStyleSheet(DARK_STYLESHEET if self._dark_mode else "")

        self._update_all_page_views()

    def next_page(self) -> None:
        if self._page_number + 1 < self._renderer.page_count:
            self.go_to_page(self._page_number + 1)

    def previous_page(self) -> None:
        if self._page_number > 0:
            self.go_to_page(self._page_number - 1)

    def go_to_page(self, page_index: int) -> None:
        """Jump directly to a zero-indexed page number."""
        if not (0 <= page_index < self._renderer.page_count):
            return

        self._page_number = page_index
        self._page_spinbox.blockSignals(True)
        self._page_spinbox.setValue(page_index + 1)
        self._page_spinbox.blockSignals(False)

        self._thumbnail_list.blockSignals(True)
        self._thumbnail_list.setCurrentRow(page_index)
        self._thumbnail_list.blockSignals(False)

        if self._view_mode == "single":
            self._rebuild_page_views()
        elif 0 <= page_index < len(self._page_widgets):
            widget = self._page_widgets[page_index]
            self._scroll_area.verticalScrollBar().setValue(widget.y())

    def zoom_in(self) -> None:
        self._zoom = min(self._zoom + 0.2, 4.0)
        self._update_all_page_views()

    def zoom_out(self) -> None:
        self._zoom = max(self._zoom - 0.2, 0.4)
        self._update_all_page_views()

    def toggle_sidebar(self) -> None:
        self._thumbnail_list.setVisible(not self._thumbnail_list.isVisible())

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle keyboard navigation shortcuts."""
        if event.key() in (Qt.Key.Key_Left, Qt.Key.Key_PageUp):
            self.previous_page()
            event.accept()
        elif event.key() in (Qt.Key.Key_Right, Qt.Key.Key_PageDown):
            self.next_page()
            event.accept()
        elif event.key() == Qt.Key.Key_Home:
            self.go_to_page(0)
            event.accept()
        elif event.key() == Qt.Key.Key_End:
            if self._renderer.page_count:
                self.go_to_page(self._renderer.page_count - 1)
            event.accept()
        else:
            super().keyPressEvent(event)

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Reader", self)
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self._add_action(toolbar, "Open", self.choose_pdf, QKeySequence.StandardKey.Open)
        self._add_action(toolbar, "Sidebar", self.toggle_sidebar)
        self._mode_action = QAction("📜 Scroll Mode", self)
        self._mode_action.triggered.connect(self.toggle_view_mode)
        toolbar.addAction(self._mode_action)

        self._dark_action = QAction("🌙 Dark Mode", self)
        self._dark_action.triggered.connect(self.toggle_dark_mode)
        toolbar.addAction(self._dark_action)

        self._add_action(toolbar, "Refresh", self.refresh_assets, QKeySequence.StandardKey.Refresh)
        self._add_action(toolbar, "Audio Files", self.show_audio_inspector)
        toolbar.addSeparator()

        self._add_action(toolbar, "Previous", self.previous_page, QKeySequence.StandardKey.Back)

        # Page Number SpinBox
        self._page_spinbox = QSpinBox(self)
        self._page_spinbox.setMinimum(1)
        self._page_spinbox.setMaximum(1)
        self._page_spinbox.setToolTip("Jump to page")
        self._page_spinbox.valueChanged.connect(self._on_spinbox_page_changed)
        toolbar.addWidget(self._page_spinbox)

        self._page_total_label = QLabel(" / 0 ")
        toolbar.addWidget(self._page_total_label)

        self._add_action(toolbar, "Next", self.next_page, QKeySequence.StandardKey.Forward)
        toolbar.addSeparator()

        self._add_action(toolbar, "Zoom Out", self.zoom_out, QKeySequence.StandardKey.ZoomOut)
        self._add_action(toolbar, "Zoom In", self.zoom_in, QKeySequence.StandardKey.ZoomIn)
        toolbar.addSeparator()

        self._add_action(toolbar, "Pause", self._audio.pause)
        self._add_action(toolbar, "Stop", self._audio.stop)
        self._add_action(toolbar, "Replay", self._audio.replay)

        speed_picker = QComboBox(self)
        speed_picker.addItems(["0.75×", "1.0×", "1.25×", "1.5×", "2.0×"])
        speed_picker.setCurrentText("1.0×")
        speed_picker.setToolTip("Playback speed")
        speed_picker.currentTextChanged.connect(self._set_playback_speed)
        toolbar.addWidget(speed_picker)

    def _on_spinbox_page_changed(self, value: int) -> None:
        self.go_to_page(value - 1)

    def _on_thumbnail_selected(self, row: int) -> None:
        if row >= 0:
            self.go_to_page(row)

    def _on_scroll_position_changed(self, value: int) -> None:
        """Update active page based on continuous scrollbar position."""
        if self._view_mode != "continuous" or not self._page_widgets:
            return

        viewport_center = value + self._scroll_area.viewport().height() // 2
        for idx, widget in enumerate(self._page_widgets):
            w_top = widget.y()
            w_bottom = w_top + widget.height()
            if w_top <= viewport_center <= w_bottom and idx != self._page_number:
                self._page_number = idx
                self._page_spinbox.blockSignals(True)
                self._page_spinbox.setValue(idx + 1)
                self._page_spinbox.blockSignals(False)

                self._thumbnail_list.blockSignals(True)
                self._thumbnail_list.setCurrentRow(idx)
                self._thumbnail_list.blockSignals(False)
                self._update_status_bar()
                break

    def _update_page_spinbox_range(self) -> None:
        count = self._renderer.page_count
        self._page_spinbox.blockSignals(True)
        self._page_spinbox.setMaximum(max(1, count))
        self._page_spinbox.setValue(1)
        self._page_spinbox.blockSignals(False)
        self._page_total_label.setText(f" / {count} ")

    def _build_thumbnails(self) -> None:
        self._thumbnail_list.blockSignals(True)
        self._thumbnail_list.clear()
        for i in range(self._renderer.page_count):
            pil_thumb = self._renderer.render_thumbnail(i, max_height=140)
            qimg = QImage(
                pil_thumb.tobytes(),
                pil_thumb.width,
                pil_thumb.height,
                pil_thumb.width * 3,
                QImage.Format.Format_RGB888,
            )
            pix = QPixmap.fromImage(qimg)
            icon = QIcon(pix)
            item = QListWidgetItem(icon, f"Page {i + 1}")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._thumbnail_list.addItem(item)
        if self._renderer.page_count:
            self._thumbnail_list.setCurrentRow(0)
        self._thumbnail_list.blockSignals(False)

    def _set_playback_speed(self, label: str) -> None:
        self._audio.set_playback_rate(float(label.removesuffix("×")))

    def _add_action(
        self, toolbar: QToolBar, text: str, callback: object, shortcut: QKeySequence | None = None
    ) -> None:
        action = QAction(text, self)
        action.triggered.connect(callback)  # type: ignore[arg-type]
        if shortcut:
            action.setShortcut(shortcut)
        toolbar.addAction(action)

    def _rebuild_page_views(self) -> None:
        """Clear and rebuild page view widgets according to current view mode."""
        self._clear_layout(self._view_layout)
        self._page_widgets.clear()

        if not self._renderer.page_count:
            return

        pages_to_render = (
            range(self._renderer.page_count)
            if self._view_mode == "continuous"
            else [self._page_number]
        )

        for p_num in pages_to_render:
            page_widget = PageViewWidget(
                page_number=p_num,
                renderer=self._renderer,
                annotations=self._annotations[p_num],
                answer_layers=self._answer_layers[p_num],
                hide_actions=self._hide_actions[p_num],
                visible_answers=self._visible_answers,
                assets=self._assets,
                audio_player=self._audio,
                zoom=self._zoom,
                toggle_callback=self._toggle_answer_field,
                status_callback=self._status.showMessage,
                dark_mode=self._dark_mode,
            )
            self._view_layout.addWidget(page_widget)
            self._page_widgets.append(page_widget)

        self._update_status_bar()

    def _update_all_page_views(self) -> None:
        """Update zoom, visible answer overlays, and dark mode on existing page widgets."""
        for widget in self._page_widgets:
            widget.update_page(self._zoom, self._visible_answers, dark_mode=self._dark_mode)
        self._update_status_bar()

    def _toggle_answer_field(self, hide_action: HideActionAnnotation) -> None:
        """Toggle an answer field overlay state and re-render page widgets."""
        target = hide_action.target_field
        if hide_action.hide:
            self._visible_answers.discard(target)
        else:
            self._visible_answers.add(target)
        self._update_all_page_views()

    def _update_status_bar(self) -> None:
        if not self._renderer.page_count:
            return
        audio_count = len(self._annotations[self._page_number])
        hide_count = len(self._hide_actions[self._page_number])
        visible_count = len(self._visible_answers)
        mode_label = "Continuous Scroll" if self._view_mode == "continuous" else "Single Page"
        theme_label = "Dark" if self._dark_mode else "Light"
        self._status.showMessage(
            f"Page {self._page_number + 1} of {self._renderer.page_count} ({mode_label}, {theme_label}) · {self._zoom:.0%} · "
            f"{audio_count} audio triggers · {hide_count} answer toggles ({visible_count} active)"
        )

    def _clear_layout(self, layout: QVBoxLayout) -> None:
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
