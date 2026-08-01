"""Read native-audio mappings and interactive PDF annotations."""

from __future__ import annotations

import argparse
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl

import pikepdf

from .asset_extractor import extract_embedded_assets
from .models import (
    AnswerLayer,
    DocumentInteractivityReport,
    HideActionAnnotation,
    SpeakerAnnotation,
)


def parse_speaker_annotations(pdf_path: str | Path) -> list[SpeakerAnnotation]:
    """Return speaker annotations, prioritizing clickable Widget trigger rectangles.

    Page numbers are one-based to match visible PDF pages. Bounding rectangles retain PDF
    user-space coordinates (x1, y1, x2, y2).
    """
    annotations: list[SpeakerAnnotation] = []
    seen_rich_media_objs: set[tuple[int, int]] = set()

    with pikepdf.open(Path(pdf_path)) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            annots = page.get("/Annots", [])

            # First pass: check Widget annotations triggering /RichMediaExecute
            for annot in annots:
                if str(annot.get("/Subtype")) != "/Widget":
                    continue
                action = _get_action(annot)
                if not action or str(action.get("/S")) != "/RichMediaExecute":
                    continue

                widget_rect = _rect(annot.get("/Rect"))
                if not widget_rect:
                    continue

                target_annot = action.get("/TA")
                if target_annot:
                    objgen = tuple(target_annot.objgen)
                    if objgen != (0, 0):
                        seen_rich_media_objs.add(objgen)
                    for flash_vars in _flash_vars(target_annot):
                        audio = _audio_source(flash_vars)
                        if audio:
                            annotations.append(
                                SpeakerAnnotation(
                                    page=page_number,
                                    rect=widget_rect,
                                    audio=audio,
                                    button_name=str(annot.get("/T", "")),
                                )
                            )

            # Second pass: direct /RichMedia annotations not claimed by a Widget trigger
            for annot in annots:
                if str(annot.get("/Subtype")) != "/RichMedia":
                    continue
                objgen = tuple(annot.objgen)
                if objgen != (0, 0) and objgen in seen_rich_media_objs:
                    continue
                rect = _rect(annot.get("/Rect"))
                if not rect:
                    continue
                for flash_vars in _flash_vars(annot):
                    audio = _audio_source(flash_vars)
                    if audio:
                        annotations.append(
                            SpeakerAnnotation(
                                page=page_number,
                                rect=rect,
                                audio=audio,
                                button_name=str(annot.get("/NM", "")),
                            )
                        )

    return annotations


def parse_answer_layers(pdf_path: str | Path) -> list[AnswerLayer]:
    """Return interactive answer overlay fields across the PDF.

    Discovers form fields targeted by /Hide actions or matching standard answer layer patterns.
    """
    hide_actions = parse_hide_actions(pdf_path)
    base_targets = {action.target_field for action in hide_actions if action.target_field}

    layers: list[AnswerLayer] = []
    with pikepdf.open(Path(pdf_path)) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            annots = page.get("/Annots", [])

            page_stems = set()
            for t in base_targets:
                if len(t) >= 4 and t[-1].isdigit() and t[-2].isdigit():
                    page_stems.add(t[:-2])
                    page_stems.add(t[:-1])
                elif len(t) >= 3 and t[-1].isdigit():
                    page_stems.add(t[:-1])
                else:
                    page_stems.add(t.rstrip("0123456789"))

            for annot in annots:
                if str(annot.get("/Subtype")) != "/Widget":
                    continue
                field_name = str(annot.get("/T", ""))
                if not field_name:
                    continue

                is_target = (
                    field_name in base_targets
                    or any(field_name.startswith(p) for p in page_stems if p)
                    or field_name.casefold().startswith("answer")
                    or field_name.casefold().startswith("ans")
                )

                if is_target:
                    rect = _rect(annot.get("/Rect"))
                    if not rect:
                        continue

                    flags = int(annot.get("/F", 0))
                    hidden = bool(flags & 32)

                    layers.append(
                        AnswerLayer(
                            page=page_number,
                            field_name=field_name,
                            rect=rect,
                            hidden=hidden,
                        )
                    )
    return layers


def parse_hide_actions(pdf_path: str | Path) -> list[HideActionAnnotation]:
    """Return interactive buttons that execute /Hide actions to show or hide answer layers."""
    hide_actions: list[HideActionAnnotation] = []
    with pikepdf.open(Path(pdf_path)) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            for annot in page.get("/Annots", []):
                if str(annot.get("/Subtype")) != "/Widget":
                    continue
                action = _get_action(annot)
                if not action or str(action.get("/S")) != "/Hide":
                    continue
                rect = _rect(annot.get("/Rect"))
                if not rect:
                    continue
                target_field = str(action.get("/T", ""))
                button_name = str(annot.get("/T", ""))
                hide_val = bool(action.get("/H", True))

                hide_actions.append(
                    HideActionAnnotation(
                        page=page_number,
                        rect=rect,
                        button_name=button_name,
                        target_field=target_field,
                        hide=hide_val,
                    )
                )
    return hide_actions


def inspect_pdf_interactivity(pdf_path: str | Path) -> DocumentInteractivityReport:
    """Generate a complete Phase 2 interactivity report for a PDF."""
    path = Path(pdf_path)
    with pikepdf.open(path) as pdf:
        total_pages = len(pdf.pages)

    embedded_assets = extract_embedded_assets(path)
    speaker_annotations = parse_speaker_annotations(path)
    answer_layers = parse_answer_layers(path)
    hide_actions = parse_hide_actions(path)

    return DocumentInteractivityReport(
        pdf_path=path,
        total_pages=total_pages,
        embedded_assets=embedded_assets,
        speaker_annotations=speaker_annotations,
        answer_layers=answer_layers,
        hide_actions=hide_actions,
    )


def _get_action(annot: Any) -> Any | None:
    """Extract standard /A action or /AA mouse-down (/D) action from an annotation."""
    if "/A" in annot:
        return annot["/A"]
    aa = annot.get("/AA")
    if aa and "/D" in aa:
        return aa["/D"]
    return None


def _flash_vars(annotation: Any) -> Iterator[str]:
    """Yield FlashVars from each RichMedia activation configuration instance."""
    settings = annotation.get("/RichMediaSettings")
    activation = settings.get("/Activation") if settings else None
    configuration = activation.get("/Configuration") if activation else None
    for instance in configuration.get("/Instances", []) if configuration else []:
        params = instance.get("/Params")
        flash_vars = params.get("/FlashVars") if params else None
        if flash_vars:
            yield str(flash_vars)


def _audio_source(flash_vars: str) -> str | None:
    """Read the ``source`` value from a FlashVars query string."""
    for key, value in parse_qsl(flash_vars, keep_blank_values=True):
        if key.casefold() == "source" and Path(value).suffix.casefold() in {
            ".mp3",
            ".wav",
            ".m4a",
            ".ogg",
        }:
            return Path(value).name
    return None


def _rect(value: Any) -> tuple[float, float, float, float] | None:
    if value is None or len(value) != 4:
        return None
    return tuple(float(coordinate) for coordinate in value)  # type: ignore[return-value]


def main() -> None:
    """Print a human-readable Phase 2 PDF interactivity report."""
    parser = argparse.ArgumentParser(description="Inspect interactive elements in a PDF.")
    parser.add_argument("pdf", type=Path, help="PDF to inspect")
    args = parser.parse_args()

    report = inspect_pdf_interactivity(args.pdf)
    print(f"=== Phase 2 Interactivity Report for {report.pdf_path.name} ===")
    print(f"Total pages: {report.total_pages}")
    print(f"Embedded assets: {len(report.embedded_assets)}")
    for asset in report.embedded_assets:
        print(f"  Asset: {asset.name} ({asset.mime}) -> {asset.path}")

    print(f"\nSpeaker Audio Triggers: {len(report.speaker_annotations)}")
    for item in report.speaker_annotations:
        btn = f" [{item.button_name}]" if item.button_name else ""
        print(f"  Page {item.page}{btn}: rect={item.rect}, audio={item.audio}")

    print(f"\nAnswer Overlay Layers: {len(report.answer_layers)}")
    for layer in report.answer_layers:
        status = "hidden" if layer.hidden else "visible"
        print(f"  Page {layer.page}: field='{layer.field_name}', rect={layer.rect}, status={status}")

    print(f"\nHide/Show Action Buttons: {len(report.hide_actions)}")
    for action in report.hide_actions:
        verb = "Hide" if action.hide else "Show"
        print(
            f"  Page {action.page}: btn='{action.button_name}', rect={action.rect} -> {verb} field '{action.target_field}'"
        )


if __name__ == "__main__":
    main()
