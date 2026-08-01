"""Application entry point."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from flashpdf.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    default_pdf = Path.cwd() / "Lesson 1-3.pdf"
    if default_pdf.is_file():
        window.open_pdf(default_pdf)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
