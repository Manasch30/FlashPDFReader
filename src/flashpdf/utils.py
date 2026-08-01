"""Small reusable helpers."""

from __future__ import annotations

from pathlib import Path


def default_cache_dir(pdf_path: str | Path) -> Path:
    """Return an isolated cache location for the given source document."""
    path = Path(pdf_path)
    return path.parent / "cache" / path.stem
