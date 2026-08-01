"""Unit tests for Multi-Tab MainWindow and Recent History helpers."""

from pathlib import Path

from PySide6.QtWidgets import QApplication

from flashpdf.main_window import MainWindow
from flashpdf.utils import add_to_recent_history, load_recent_history

SAMPLE_PDF = Path("Lesson 1-3.pdf")


def test_recent_history_helpers(tmp_path: Path) -> None:
    test_pdf = tmp_path / "test_doc.pdf"
    test_pdf.write_bytes(b"%PDF-1.4 mock content")

    history = add_to_recent_history(test_pdf)
    assert len(history) > 0
    assert test_pdf.resolve() in [p.resolve() for p in history]

    loaded = load_recent_history()
    assert test_pdf.resolve() in [p.resolve() for p in loaded]


def test_main_window_tabs() -> None:
    _ = QApplication.instance() or QApplication([])
    window = MainWindow()

    if SAMPLE_PDF.exists():
        window.open_pdf(SAMPLE_PDF)
        assert window._tab_widget.count() == 1
        assert window.current_tab is not None
        assert window.current_tab.pdf_path.name == SAMPLE_PDF.name

        # Opening same PDF switches tab rather than duplicating
        window.open_pdf(SAMPLE_PDF)
        assert window._tab_widget.count() == 1

        # Closing tab
        window._close_tab(0)
        assert window._tab_widget.count() == 0
        assert window.current_tab is None

    window.close()
