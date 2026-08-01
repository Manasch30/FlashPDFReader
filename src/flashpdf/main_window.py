"""Main Qt window for reading interactive educational PDFs with multi-tab & history support."""

from __future__ import annotations

import shutil
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction, QIcon, QKeyEvent, QKeySequence, QPixmap, QWheelEvent
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QToolBar,
    QToolButton,
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
from .utils import add_to_recent_history, default_cache_dir, load_recent_history

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
QTabWidget::pane { border: 1px solid #333342; background: #121218; }
QTabBar::tab { background: #24242e; color: #a0a0b0; padding: 6px 14px; border-top-left-radius: 4px; border-top-right-radius: 4px; margin-right: 2px; }
QTabBar::tab:selected { background: #3b4252; color: #ffffff; font-weight: bold; }
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


class PdfTabWidget(QWidget):
    """Container widget representing a single open PDF document tab."""

    def __init__(
        self,
        pdf_path: Path,
        audio_player: AudioPlayer,
        zoom_in_cb: Callable[[], None],
        zoom_out_cb: Callable[[], None],
        status_cb: Callable[[str], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.pdf_path = pdf_path
        self._audio = audio_player
        self._status_cb = status_cb
        self.renderer = PdfRenderer()

        self.annotations: dict[int, list[SpeakerAnnotation]] = defaultdict(list)
        self.answer_layers: dict[int, list[AnswerLayer]] = defaultdict(list)
        self.hide_actions: dict[int, list[HideActionAnnotation]] = defaultdict(list)
        self.visible_answers: set[str] = set()
        self.assets: dict[str, Path] = {}
        self.page_number = 0
        self.zoom = 1.25
        self.view_mode: str = "single"  # "single" or "continuous"
        self.dark_mode: bool = False
        self.page_widgets: list[PageViewWidget] = []

        # UI Setup
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        # Thumbnail Sidebar
        self.thumbnail_list = QListWidget()
        self.thumbnail_list.setIconSize(QSize(120, 160))
        self.thumbnail_list.setMaximumWidth(200)
        self.thumbnail_list.setMinimumWidth(120)
        self.splitter.addWidget(self.thumbnail_list)

        # Scroll Area for PDF Pages
        self.scroll_area = ZoomableScrollArea(
            zoom_in_cb=zoom_in_cb, zoom_out_cb=zoom_out_cb
        )
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.view_container = QWidget()
        self.view_layout = QVBoxLayout(self.view_container)
        self.view_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self.view_layout.setContentsMargins(10, 10, 10, 10)
        self.view_layout.setSpacing(15)
        self.scroll_area.setWidget(self.view_container)

        self.splitter.addWidget(self.scroll_area)
        self.splitter.setSizes([170, 1030])
        layout.addWidget(self.splitter)

        self._load_document()

    def _load_document(self, force_reextract: bool = False) -> None:
        """Load PDF structure, extract assets, and parse annotations."""
        self.renderer.open(self.pdf_path)
        cache_dir = default_cache_dir(self.pdf_path)

        if force_reextract and cache_dir.exists():
            shutil.rmtree(cache_dir, ignore_errors=True)

        self.assets = {
            asset.name: asset.path
            for asset in extract_embedded_assets(self.pdf_path, cache_dir)
            if asset.mime == "audio/mpeg"
        }
        self.annotations = defaultdict(list)
        for annotation in parse_speaker_annotations(self.pdf_path):
            self.annotations[annotation.page - 1].append(annotation)

        self.answer_layers = defaultdict(list)
        for layer in parse_answer_layers(self.pdf_path):
            self.answer_layers[layer.page - 1].append(layer)

        self.hide_actions = defaultdict(list)
        for action in parse_hide_actions(self.pdf_path):
            self.hide_actions[action.page - 1].append(action)

        self.visible_answers.clear()
        self.page_number = 0
        self.build_thumbnails()
        self.rebuild_page_views()

    def reload(self, force_reextract: bool = False) -> None:
        """Re-extract assets and refresh view."""
        self.renderer.close()
        self._load_document(force_reextract=force_reextract)

    def close_document(self) -> None:
        """Close PDF handle and cleanup."""
        self.renderer.close()

    def build_thumbnails(self) -> None:
        self.thumbnail_list.blockSignals(True)
        self.thumbnail_list.clear()
        for i in range(self.renderer.page_count):
            thumb_img = self.renderer.render_thumbnail(i, max_height=140)
            pix = QPixmap.fromImage(thumb_img)
            icon = QIcon(pix)
            item = QListWidgetItem(icon, f"Page {i + 1}")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.thumbnail_list.addItem(item)
        if self.renderer.page_count:
            self.thumbnail_list.setCurrentRow(0)
        self.thumbnail_list.blockSignals(False)

    def rebuild_page_views(self) -> None:
        """Clear and rebuild page view widgets according to current view mode."""
        self._clear_layout(self.view_layout)
        self.page_widgets.clear()

        if not self.renderer.page_count:
            return

        pages_to_render = (
            range(self.renderer.page_count)
            if self.view_mode == "continuous"
            else [self.page_number]
        )

        for p_num in pages_to_render:
            page_widget = PageViewWidget(
                page_number=p_num,
                renderer=self.renderer,
                annotations=self.annotations[p_num],
                answer_layers=self.answer_layers[p_num],
                hide_actions=self.hide_actions[p_num],
                visible_answers=self.visible_answers,
                assets=self.assets,
                audio_player=self._audio,
                zoom=self.zoom,
                toggle_callback=self._toggle_answer_field,
                status_callback=self._status_cb,
                dark_mode=self.dark_mode,
            )
            self.view_layout.addWidget(page_widget)
            self.page_widgets.append(page_widget)

    def update_all_page_views(self) -> None:
        """Update zoom, visible answer overlays, and dark mode on existing page widgets."""
        for widget in self.page_widgets:
            widget.update_page(self.zoom, self.visible_answers, dark_mode=self.dark_mode)

    def _toggle_answer_field(self, hide_action: HideActionAnnotation) -> None:
        """Toggle an answer field overlay state and re-render page widgets."""
        target = hide_action.target_field
        if hide_action.hide:
            self.visible_answers.discard(target)
        else:
            self.visible_answers.add(target)
        self.update_all_page_views()

    def _clear_layout(self, layout: QVBoxLayout) -> None:
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()


class MainWindow(QMainWindow):
    """A multi-tab cross-platform viewer for Flash-based interactive educational PDFs."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("FlashPDF Reader")
        self.resize(1250, 850)
        self._audio = AudioPlayer()

        # Tab Widget Central Area
        self._tab_widget = QTabWidget(self)
        self._tab_widget.setTabsClosable(True)
        self._tab_widget.setMovable(True)
        self._tab_widget.tabCloseRequested.connect(self._close_tab)
        self._tab_widget.currentChanged.connect(self._on_tab_changed)
        self.setCentralWidget(self._tab_widget)

        self._status = self.statusBar()
        self._build_toolbar()
        self._refresh_recent_menu()

    @property
    def current_tab(self) -> PdfTabWidget | None:
        widget = self._tab_widget.currentWidget()
        return widget if isinstance(widget, PdfTabWidget) else None

    def open_pdf(self, pdf_path: str | Path, force_reextract: bool = False) -> None:
        """Open a PDF file in a new tab (or switch to its tab if already open)."""
        path = Path(pdf_path).resolve()
        if not path.is_file():
            QMessageBox.critical(self, "File Not Found", f"File '{path}' does not exist.")
            return

        # Check if already open in a tab
        for i in range(self._tab_widget.count()):
            tab = self._tab_widget.widget(i)
            if isinstance(tab, PdfTabWidget) and tab.pdf_path.resolve() == path:
                self._tab_widget.setCurrentIndex(i)
                if force_reextract:
                    tab.reload(force_reextract=True)
                return

        try:
            tab = PdfTabWidget(
                pdf_path=path,
                audio_player=self._audio,
                zoom_in_cb=self.zoom_in,
                zoom_out_cb=self.zoom_out,
                status_cb=self._status.showMessage,
                parent=self._tab_widget,
            )
            tab.thumbnail_list.currentRowChanged.connect(self._on_thumbnail_selected)
            tab.scroll_area.verticalScrollBar().valueChanged.connect(self._on_scroll_position_changed)

            index = self._tab_widget.addTab(tab, path.name)
            self._tab_widget.setTabToolTip(index, str(path))
            self._tab_widget.setCurrentIndex(index)

            add_to_recent_history(path)
            self._refresh_recent_menu()
        except Exception as error:  # noqa: BLE001
            QMessageBox.critical(self, "Could not open PDF", str(error))

    def _close_tab(self, index: int) -> None:
        """Close tab at index."""
        tab = self._tab_widget.widget(index)
        if isinstance(tab, PdfTabWidget):
            tab.close_document()
        self._tab_widget.removeTab(index)
        if self._tab_widget.count() == 0:
            self.setWindowTitle("FlashPDF Reader")
            self._status.showMessage("No PDF documents open.")

    def choose_pdf(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self, "Open Educational PDF", "", "PDF files (*.pdf)"
        )
        if filename:
            self.open_pdf(filename)

    def refresh_assets(self) -> None:
        """Force re-extraction of audio assets and re-parsing for the active tab."""
        tab = self.current_tab
        if tab:
            tab.reload(force_reextract=True)
            self._status.showMessage(
                f"Refreshed assets for {tab.pdf_path.name} ({len(tab.assets)} audio files loaded)"
            )

    def show_audio_inspector(self) -> None:
        """Open the Audio File Inspector dialog for the active tab."""
        tab = self.current_tab
        if not tab or not tab.assets:
            QMessageBox.information(
                self, "Audio Assets", "No extracted audio files found for this document."
            )
            return
        dialog = AudioDialog(tab.assets, self._audio, self)
        dialog.exec()

    def toggle_view_mode(self) -> None:
        """Toggle between Single Page Mode and Continuous Scroll Mode."""
        tab = self.current_tab
        if not tab:
            return
        tab.view_mode = "continuous" if tab.view_mode == "single" else "single"
        self._mode_action.setText("📜 Scroll Mode" if tab.view_mode == "single" else "📄 Single Page")
        tab.rebuild_page_views()
        self._update_status_bar()

    def toggle_dark_mode(self) -> None:
        """Toggle between Light Mode and Smart Dark Mode across all tabs."""
        tab = self.current_tab
        if not tab:
            return
        new_dark_state = not tab.dark_mode

        # Update dark mode state across all tabs
        for i in range(self._tab_widget.count()):
            t = self._tab_widget.widget(i)
            if isinstance(t, PdfTabWidget):
                t.dark_mode = new_dark_state
                t.update_all_page_views()

        self._dark_action.setText("☀️ Light Mode" if new_dark_state else "🌙 Dark Mode")
        app = QApplication.instance()
        if app:
            app.setStyleSheet(DARK_STYLESHEET if new_dark_state else "")
        self._update_status_bar()

    def next_page(self) -> None:
        tab = self.current_tab
        if tab and tab.page_number + 1 < tab.renderer.page_count:
            self.go_to_page(tab.page_number + 1)

    def previous_page(self) -> None:
        tab = self.current_tab
        if tab and tab.page_number > 0:
            self.go_to_page(tab.page_number - 1)

    def go_to_page(self, page_index: int) -> None:
        """Jump directly to a zero-indexed page number in the active tab."""
        tab = self.current_tab
        if not tab or not (0 <= page_index < tab.renderer.page_count):
            return

        tab.page_number = page_index
        self._page_spinbox.blockSignals(True)
        self._page_spinbox.setValue(page_index + 1)
        self._page_spinbox.blockSignals(False)

        tab.thumbnail_list.blockSignals(True)
        tab.thumbnail_list.setCurrentRow(page_index)
        tab.thumbnail_list.blockSignals(False)

        if tab.view_mode == "single":
            tab.rebuild_page_views()
        elif 0 <= page_index < len(tab.page_widgets):
            widget = tab.page_widgets[page_index]
            tab.scroll_area.verticalScrollBar().setValue(widget.y())

        self._update_status_bar()

    def zoom_in(self) -> None:
        tab = self.current_tab
        if tab:
            tab.zoom = min(tab.zoom + 0.2, 4.0)
            tab.update_all_page_views()
            self._update_status_bar()

    def zoom_out(self) -> None:
        tab = self.current_tab
        if tab:
            tab.zoom = max(tab.zoom - 0.2, 0.4)
            tab.update_all_page_views()
            self._update_status_bar()

    def toggle_sidebar(self) -> None:
        tab = self.current_tab
        if tab:
            tab.thumbnail_list.setVisible(not tab.thumbnail_list.isVisible())

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
            tab = self.current_tab
            if tab and tab.renderer.page_count:
                self.go_to_page(tab.renderer.page_count - 1)
            event.accept()
        else:
            super().keyPressEvent(event)

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Reader", self)
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self._add_action(toolbar, "Open", self.choose_pdf, QKeySequence.StandardKey.Open)

        # Recent PDFs Dropdown Tool Button
        self._recent_button = QToolButton(self)
        self._recent_button.setText("Recent PDFs ▾")
        self._recent_menu = QMenu(self._recent_button)
        self._recent_button.setMenu(self._recent_menu)
        self._recent_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        toolbar.addWidget(self._recent_button)

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

    def _refresh_recent_menu(self) -> None:
        """Populate Recent PDFs menu from saved history."""
        self._recent_menu.clear()
        history = load_recent_history()
        if not history:
            no_item = self._recent_menu.addAction("No Recent PDFs")
            no_item.setEnabled(False)
            return

        for p in history:
            action = self._recent_menu.addAction(p.name)
            action.setToolTip(str(p))
            action.triggered.connect(lambda _, path=p: self.open_pdf(path))

    def _on_tab_changed(self, index: int) -> None:
        """Update toolbar & status bar when active tab changes."""
        tab = self.current_tab
        if not tab:
            return

        self.setWindowTitle(f"FlashPDF Reader — {tab.pdf_path.name}")
        self._page_spinbox.blockSignals(True)
        self._page_spinbox.setMaximum(max(1, tab.renderer.page_count))
        self._page_spinbox.setValue(tab.page_number + 1)
        self._page_spinbox.blockSignals(False)
        self._page_total_label.setText(f" / {tab.renderer.page_count} ")

        self._mode_action.setText("📄 Single Page" if tab.view_mode == "continuous" else "📜 Scroll Mode")
        self._dark_action.setText("☀️ Light Mode" if tab.dark_mode else "🌙 Dark Mode")
        self._update_status_bar()

    def _on_spinbox_page_changed(self, value: int) -> None:
        self.go_to_page(value - 1)

    def _on_thumbnail_selected(self, row: int) -> None:
        if row >= 0:
            self.go_to_page(row)

    def _on_scroll_position_changed(self, value: int) -> None:
        """Update active page based on continuous scrollbar position in current tab."""
        tab = self.current_tab
        if not tab or tab.view_mode != "continuous" or not tab.page_widgets:
            return

        viewport_center = value + tab.scroll_area.viewport().height() // 2
        for idx, widget in enumerate(tab.page_widgets):
            w_top = widget.y()
            w_bottom = w_top + widget.height()
            if w_top <= viewport_center <= w_bottom and idx != tab.page_number:
                tab.page_number = idx
                self._page_spinbox.blockSignals(True)
                self._page_spinbox.setValue(idx + 1)
                self._page_spinbox.blockSignals(False)

                tab.thumbnail_list.blockSignals(True)
                tab.thumbnail_list.setCurrentRow(idx)
                tab.thumbnail_list.blockSignals(False)
                self._update_status_bar()
                break

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

    def _update_status_bar(self) -> None:
        tab = self.current_tab
        if not tab or not tab.renderer.page_count:
            return
        audio_count = len(tab.annotations[tab.page_number])
        hide_count = len(tab.hide_actions[tab.page_number])
        visible_count = len(tab.visible_answers)
        mode_label = "Continuous Scroll" if tab.view_mode == "continuous" else "Single Page"
        theme_label = "Dark" if tab.dark_mode else "Light"
        self._status.showMessage(
            f"Page {tab.page_number + 1} of {tab.renderer.page_count} ({mode_label}, {theme_label}) · {tab.zoom:.0%} · "
            f"{audio_count} audio triggers · {hide_count} answer toggles ({visible_count} active)"
        )
