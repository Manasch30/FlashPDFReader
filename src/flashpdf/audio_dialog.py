"""Dialog for inspecting and previewing extracted PDF audio assets."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .audio_player import AudioPlayer


class AudioDialog(QDialog):
    """A dialog displaying extracted audio files with direct play preview capabilities."""

    def __init__(
        self, assets: dict[str, Path], audio_player: AudioPlayer, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Extracted Audio Assets Inspector")
        self.resize(750, 480)
        self._assets = assets
        self._audio = audio_player

        layout = QVBoxLayout(self)

        # Header summary label
        total_files = len(assets)
        total_bytes = sum(p.stat().st_size for p in assets.values() if p.exists())
        size_mb = total_bytes / (1024 * 1024)
        header = QLabel(
            f"<b>Extracted Audio Assets:</b> {total_files} files ({size_mb:.2f} MB total)"
        )
        layout.addWidget(header)

        # Table
        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["Filename", "Size", "Cache Path", "Preview"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        self._populate_table()
        layout.addWidget(self._table)

        # Footer close button
        footer_layout = QHBoxLayout()
        footer_layout.addStretch()
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        footer_layout.addWidget(close_button)
        layout.addLayout(footer_layout)

    def _populate_table(self) -> None:
        self._table.setRowCount(len(self._assets))
        sorted_assets = sorted(self._assets.items())

        for row, (name, path) in enumerate(sorted_assets):
            name_item = QTableWidgetItem(name)
            name_item.setFlags(name_item.flags() ^ Qt.ItemFlag.ItemIsEditable)

            size_str = "N/A"
            if path.exists():
                size_kb = path.stat().st_size / 1024
                size_str = f"{size_kb:.1f} KB"
            size_item = QTableWidgetItem(size_str)
            size_item.setFlags(size_item.flags() ^ Qt.ItemFlag.ItemIsEditable)
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            path_item = QTableWidgetItem(str(path))
            path_item.setFlags(path_item.flags() ^ Qt.ItemFlag.ItemIsEditable)

            play_button = QPushButton("▶ Play")
            play_button.setStyleSheet(
                "background: #237dd2; color: white; border: 0; border-radius: 3px; padding: 3px 8px;"
            )
            play_button.clicked.connect(
                lambda checked=False, p=path: self._audio.play(p)
            )

            self._table.setItem(row, 0, name_item)
            self._table.setItem(row, 1, size_item)
            self._table.setItem(row, 2, path_item)
            self._table.setCellWidget(row, 3, play_button)
