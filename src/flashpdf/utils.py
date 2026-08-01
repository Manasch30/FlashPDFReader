"""Small reusable helpers."""

from __future__ import annotations

import json
from pathlib import Path

MAX_HISTORY_ITEMS = 10


def default_cache_dir(pdf_path: str | Path) -> Path:
    """Return an isolated cache location for the given source document."""
    path = Path(pdf_path)
    return path.parent / "cache" / path.stem


def get_history_file() -> Path:
    """Return path to user's recent PDF history JSON file."""
    history_dir = Path.home() / ".cache" / "flashpdf"
    history_dir.mkdir(parents=True, exist_ok=True)
    return history_dir / "history.json"


def load_recent_history() -> list[Path]:
    """Load recent valid PDF paths from history file."""
    history_file = get_history_file()
    if not history_file.exists():
        return []
    try:
        data = json.loads(history_file.read_text(encoding="utf-8"))
        paths = [Path(p) for p in data if isinstance(p, str) and Path(p).is_file()]
        return paths[:MAX_HISTORY_ITEMS]
    except Exception:  # noqa: BLE001
        return []


def save_recent_history(paths: list[Path]) -> None:
    """Save PDF paths to history file."""
    history_file = get_history_file()
    try:
        valid_paths = [str(p.resolve()) for p in paths if p.is_file()]
        history_file.write_text(json.dumps(valid_paths, indent=2), encoding="utf-8")
    except Exception:  # noqa: BLE001
        return


def add_to_recent_history(pdf_path: str | Path) -> list[Path]:
    """Add a PDF path to the recent history list and save it."""
    path = Path(pdf_path).resolve()
    if not path.is_file():
        return load_recent_history()

    history = load_recent_history()
    # Filter out existing instance of this path
    new_history = [p for p in history if p.resolve() != path]
    new_history.insert(0, path)
    new_history = new_history[:MAX_HISTORY_ITEMS]
    save_recent_history(new_history)
    return new_history
