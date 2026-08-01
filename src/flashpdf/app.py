"""Application entry point."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Configure FlexiBLAS library search path for PyInstaller Linux freezes
if getattr(sys, "frozen", False):
    bundle_dir = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    flex_dir = os.path.join(bundle_dir, "flexiblas")
    if os.path.exists(flex_dir):
        os.environ["FLEXIBLAS_LIB_PATH"] = flex_dir

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
