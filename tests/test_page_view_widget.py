"""Tests for PageViewWidget rendering, overlay creation, and text extraction."""

from pathlib import Path

from PySide6.QtWidgets import QApplication, QPushButton

from flashpdf.audio_player import AudioPlayer
from flashpdf.models import HideActionAnnotation, SpeakerAnnotation
from flashpdf.page_view_widget import PageViewWidget
from flashpdf.pdf_renderer import PdfRenderer

# Ensure QApplication exists for Qt widget tests
_app = QApplication.instance() or QApplication([])

SAMPLE_PDF = Path("Lesson 1-3.pdf")


def test_page_view_widget_creation() -> None:
    renderer = PdfRenderer()
    renderer.open(SAMPLE_PDF)
    audio_player = AudioPlayer()

    annotations = [
        SpeakerAnnotation(
            page=1, rect=(10.0, 10.0, 50.0, 50.0), audio="test.mp3", button_name="spk1"
        )
    ]
    hide_actions = [
        HideActionAnnotation(
            page=1,
            rect=(100.0, 100.0, 150.0, 130.0),
            button_name="ans1",
            target_field="target1",
            hide=False,
        )
    ]
    assets = {"test.mp3": Path("/tmp/test.mp3")}

    toggled_actions = []

    widget = PageViewWidget(
        page_number=0,
        renderer=renderer,
        annotations=annotations,
        answer_layers=[],
        hide_actions=hide_actions,
        visible_answers=set(),
        assets=assets,
        audio_player=audio_player,
        zoom=1.0,
        toggle_callback=lambda act: toggled_actions.append(act),
        dark_mode=False,
    )

    assert widget.page_number == 0
    buttons = widget.findChildren(QPushButton)
    assert len(buttons) == 2  # 1 speaker button + 1 answer toggle button

    renderer.close()


def test_page_view_widget_dark_mode() -> None:
    renderer = PdfRenderer()
    renderer.open(SAMPLE_PDF)
    audio_player = AudioPlayer()

    widget = PageViewWidget(
        page_number=0,
        renderer=renderer,
        annotations=[],
        answer_layers=[],
        hide_actions=[],
        visible_answers=set(),
        assets={},
        audio_player=audio_player,
        zoom=1.0,
        toggle_callback=lambda act: None,
        dark_mode=True,
    )

    assert widget.page_number == 0
    img_light = renderer.render_page(0, scale=1.0, dark_mode=False)
    img_dark = renderer.render_page(0, scale=1.0, dark_mode=True)
    assert not img_light.isNull()
    assert not img_dark.isNull()
    assert img_light.bits() != img_dark.bits()

    renderer.close()


def test_extract_text_in_rect() -> None:
    renderer = PdfRenderer()
    renderer.open(SAMPLE_PDF)

    # Extract text from upper portion of Page 1
    w, h = renderer.page_size(0)
    text = renderer.extract_text_in_rect(0, (0.0, 0.0, w, h))

    assert len(text) > 0
    renderer.close()
