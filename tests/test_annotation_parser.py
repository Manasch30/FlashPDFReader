from pathlib import Path

from flashpdf.annotation_parser import (
    inspect_pdf_interactivity,
    parse_answer_layers,
    parse_hide_actions,
    parse_speaker_annotations,
)
from flashpdf.pdf_renderer import PdfRenderer
from flashpdf.utils import default_cache_dir

PDF_PATH = Path("Lesson 1-3.pdf")
LESSON_7_9_PATH = Path("Lesson 7-9.pdf")


def test_default_cache_dir_isolates_by_pdf_stem() -> None:
    cache_path = default_cache_dir(PDF_PATH)
    assert cache_path == Path("cache/Lesson 1-3")


def test_parse_speaker_annotations_discovers_widget_triggers() -> None:
    annotations = parse_speaker_annotations(PDF_PATH)
    assert len(annotations) > 0
    widget_triggers = [a for a in annotations if a.button_name.startswith("ボタン")]
    assert len(widget_triggers) > 0
    sample = widget_triggers[0]
    assert sample.page > 0
    assert len(sample.rect) == 4
    assert sample.audio.endswith(".mp3")


def test_parse_answer_layers_discovers_fields() -> None:
    layers = parse_answer_layers(PDF_PATH)
    assert len(layers) >= 6
    field_names = {layer.field_name for layer in layers}
    assert "answer01" in field_names
    assert "answer02" in field_names
    answer01 = next(layer for layer in layers if layer.field_name == "answer01")
    assert answer01.hidden is True


def test_parse_hide_actions_discovers_show_hide_toggles() -> None:
    actions = parse_hide_actions(PDF_PATH)
    assert len(actions) >= 12
    show_buttons = [a for a in actions if not a.hide]
    hide_buttons = [a for a in actions if a.hide]
    assert len(show_buttons) > 0
    assert len(hide_buttons) > 0

    show_ans1 = next(a for a in show_buttons if a.target_field == "answer01")
    assert show_ans1.button_name == "answerbttn"
    assert show_ans1.hide is False

    hide_ans1 = next(a for a in hide_buttons if a.target_field == "answer01")
    assert hide_ans1.button_name == "close"
    assert hide_ans1.hide is True


def test_inspect_pdf_interactivity_generates_report() -> None:
    report = inspect_pdf_interactivity(PDF_PATH)
    assert report.pdf_path == PDF_PATH
    assert report.total_pages == 7
    assert len(report.embedded_assets) > 0
    assert len(report.speaker_annotations) > 0
    assert len(report.answer_layers) > 0
    assert len(report.hide_actions) > 0


def test_pdf_renderer_unhides_answer_layer_pixmap() -> None:
    renderer = PdfRenderer()
    renderer.open(PDF_PATH)

    img_hidden = renderer.render_page(2, scale=1.0, visible_answers=set())
    img_visible = renderer.render_page(2, scale=1.0, visible_answers={"answer01"})
    thumb = renderer.render_thumbnail(2, max_height=140)

    assert not img_hidden.isNull()
    assert not img_visible.isNull()
    assert not thumb.isNull()
    assert thumb.height() <= 150
    assert img_hidden.bits() != img_visible.bits()

    renderer.close()


def test_pdf_renderer_unhides_table_answer_layers_lesson_7_9() -> None:
    if not LESSON_7_9_PATH.exists():
        return
    renderer = PdfRenderer()
    renderer.open(LESSON_7_9_PATH)

    # Render Page 7 (index 6) with hidden vs unhidden table field 'ボタン288'
    img_hidden = renderer.render_page(6, scale=1.0, visible_answers=set())
    img_table_visible = renderer.render_page(6, scale=1.0, visible_answers={"ボタン288"})

    assert not img_hidden.isNull()
    assert not img_table_visible.isNull()
    assert img_hidden.bits() != img_table_visible.bits()

    renderer.close()
