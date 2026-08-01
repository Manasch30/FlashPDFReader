"""Native audio playback for extracted textbook clips."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer


class AudioPlayer:
    """Small, UI-independent wrapper around Qt Multimedia."""

    def __init__(self) -> None:
        self._output = QAudioOutput()
        self._output.setVolume(1.0)
        self._player = QMediaPlayer()
        self._player.setAudioOutput(self._output)

    @property
    def is_playing(self) -> bool:
        return self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState

    def play(self, path: str | Path) -> None:
        self._player.setSource(QUrl.fromLocalFile(str(Path(path).resolve())))
        self._player.play()

    def pause(self) -> None:
        self._player.pause()

    def stop(self) -> None:
        self._player.stop()

    def replay(self) -> None:
        self._player.setPosition(0)
        self._player.play()

    def set_playback_rate(self, rate: float) -> None:
        self._player.setPlaybackRate(rate)
