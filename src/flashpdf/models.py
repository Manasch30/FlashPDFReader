"""Data structures shared across FlashPDF Reader modules."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class EmbeddedAsset:
    """A supported file extracted from a PDF."""

    name: str
    path: Path
    mime: str


@dataclass(frozen=True, slots=True)
class SpeakerAnnotation:
    """A PDF region whose legacy Flash action points to an audio asset."""

    page: int
    rect: tuple[float, float, float, float]
    audio: str
    button_name: str = ""


@dataclass(frozen=True, slots=True)
class AnswerLayer:
    """An interactive answer field layer in the PDF."""

    page: int
    field_name: str
    rect: tuple[float, float, float, float]
    hidden: bool = True


@dataclass(frozen=True, slots=True)
class HideActionAnnotation:
    """An interactive button that toggles visibility of an answer field."""

    page: int
    rect: tuple[float, float, float, float]
    button_name: str
    target_field: str
    hide: bool  # True to hide, False to unhide/show


@dataclass(frozen=True, slots=True)
class DocumentInteractivityReport:
    """Detailed summary of all interactive elements discovered in a PDF document."""

    pdf_path: Path
    total_pages: int
    embedded_assets: list[EmbeddedAsset]
    speaker_annotations: list[SpeakerAnnotation]
    answer_layers: list[AnswerLayer]
    hide_actions: list[HideActionAnnotation]

