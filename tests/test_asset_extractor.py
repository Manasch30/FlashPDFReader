from flashpdf.annotation_parser import _audio_source
from flashpdf.asset_extractor import _unique_filename


def test_unique_filename_sanitizes_and_disambiguates() -> None:
    names: set[str] = set()
    assert _unique_filename("folder/lesson 1.mp3", names) == "lesson_1.mp3"
    assert _unique_filename("lesson 1.mp3", names) == "lesson_1-2.mp3"


def test_unique_filename_keeps_extension() -> None:
    names: set[str] = set()
    assert _unique_filename("AudioPlayer.swf", names) == "AudioPlayer.swf"


def test_audio_source_reads_flashvars() -> None:
    assert _audio_source("source=3lesson1.mp3&autoPlay=true&volume=1.00") == "3lesson1.mp3"


def test_audio_source_ignores_non_audio_values() -> None:
    assert _audio_source("source=AudioPlayer.swf") is None
