"""Entry point for FlashPDF Reader application."""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from flashpdf.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()

    if len(sys.argv) > 1:
        pdf_path = Path(sys.argv[1])
        if pdf_path.exists() and pdf_path.suffix.lower() == ".pdf":
            window.open_pdf(pdf_path)

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
