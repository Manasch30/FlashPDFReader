"""Extract audio and Flash assets from PDF embedded-file structures."""

from __future__ import annotations

import argparse
import hashlib
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pikepdf

from .models import EmbeddedAsset

_SUPPORTED_SUFFIXES = {".mp3": "audio/mpeg", ".swf": "application/x-shockwave-flash"}
_UNSAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]+")


def extract_embedded_assets(
    pdf_path: str | Path, cache_dir: str | Path | None = None
) -> list[EmbeddedAsset]:
    """Extract supported embedded files and return their local descriptions.

    Both the document-level ``/EmbeddedFiles`` name tree and RichMedia ``/Assets`` name
    trees are checked. The returned paths are safe basenames in ``cache_dir``; duplicate
    embedded streams are only written once.
    """
    source = Path(pdf_path)
    destination = Path(cache_dir) if cache_dir is not None else source.parent / "cache"
    destination.mkdir(parents=True, exist_ok=True)

    extracted: list[EmbeddedAsset] = []
    seen_streams: set[tuple[str, str]] = set()
    names_in_use: set[str] = set()

    with pikepdf.open(source) as pdf:
        for embedded_name, stream in _iter_embedded_streams(pdf):
            suffix = Path(embedded_name).suffix.lower()
            mime = _SUPPORTED_SUFFIXES.get(suffix)
            if mime is None:
                continue

            content = bytes(stream.read_bytes())
            digest = hashlib.sha256(content).hexdigest()
            key = (suffix, digest)
            if key in seen_streams:
                continue
            seen_streams.add(key)

            filename = _unique_filename(embedded_name, names_in_use)
            output_path = destination / filename
            if (
                not output_path.exists()
                or hashlib.sha256(output_path.read_bytes()).hexdigest() != digest
            ):
                output_path.write_bytes(content)
            extracted.append(EmbeddedAsset(name=filename, path=output_path, mime=mime))

    return extracted


def _iter_embedded_streams(pdf: pikepdf.Pdf) -> Iterator[tuple[str, Any]]:
    """Yield filename/stream pairs from standard and RichMedia asset name trees."""
    seen_objects: set[tuple[int, int]] = set()
    for tree_root in _asset_name_tree_roots(pdf):
        for name, filespec in _walk_name_tree(tree_root):
            stream = _embedded_file_stream(filespec)
            if stream is None:
                continue
            objgen = tuple(stream.objgen)
            if objgen != (0, 0) and objgen in seen_objects:
                continue
            seen_objects.add(objgen)
            yield name, stream


def _asset_name_tree_roots(pdf: pikepdf.Pdf) -> Iterator[Any]:
    root = pdf.Root
    names = root.get("/Names")
    if names and names.get("/EmbeddedFiles"):
        yield names["/EmbeddedFiles"]

    for page in pdf.pages:
        annotations = page.get("/Annots", [])
        for annotation in annotations:
            rich_media = annotation.get("/RichMediaContent")
            assets = rich_media.get("/Assets") if rich_media else None
            if assets:
                yield assets


def _walk_name_tree(node: Any) -> Iterator[tuple[str, Any]]:
    """Walk a PDF name tree without relying on pikepdf's high-level wrapper."""
    values = node.get("/Names", [])
    for index in range(0, len(values) - 1, 2):
        yield str(values[index]), values[index + 1]
    for child in node.get("/Kids", []):
        yield from _walk_name_tree(child)


def _embedded_file_stream(filespec: Any) -> Any | None:
    embedded_file = filespec.get("/EF") if hasattr(filespec, "get") else None
    if not embedded_file:
        return None
    return embedded_file.get("/F") or embedded_file.get("/UF")


def _unique_filename(name: str, names_in_use: set[str]) -> str:
    """Return a portable cache filename, preserving its extension when possible."""
    basename = Path(name).name
    cleaned = _UNSAFE_FILENAME.sub("_", basename).strip(".") or "embedded_asset"
    stem, suffix = Path(cleaned).stem, Path(cleaned).suffix.lower()
    candidate = f"{stem}{suffix}"
    number = 2
    while candidate.casefold() in names_in_use:
        candidate = f"{stem}-{number}{suffix}"
        number += 1
    names_in_use.add(candidate.casefold())
    return candidate


def main() -> None:
    """Run extraction from the command line."""
    parser = argparse.ArgumentParser(description="Extract MP3 and SWF assets from a PDF.")
    parser.add_argument("pdf", type=Path, help="PDF to inspect")
    parser.add_argument("--cache-dir", type=Path, help="Directory for extracted assets")
    args = parser.parse_args()
    for asset in extract_embedded_assets(args.pdf, args.cache_dir):
        print(f"{asset.mime:32} {asset.name} -> {asset.path}")


if __name__ == "__main__":
    main()
