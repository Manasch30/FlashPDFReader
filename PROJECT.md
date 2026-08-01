# FlashPDF Reader

> A modern replacement for Adobe Flash-based interactive educational PDFs.

## Vision

Many educational PDFs created between ~2008–2018 use Adobe RichMedia annotations with embedded SWF players (typically `AudioPlayer.swf`) to play pronunciation audio.

Since Adobe Flash reached end-of-life, these PDFs have become partially unusable despite still containing all embedded assets.

The goal of this project is to build a modern, cross-platform desktop application that preserves the original interactive learning experience without requiring Flash.

This project is **not** a generic PDF reader.

It is an interactive educational PDF reader optimized for language textbooks.

---

# Primary Goals

- Render PDF pages with high fidelity.
- Detect RichMedia annotations.
- Ignore Flash.
- Extract embedded audio automatically.
- Replace Flash interactions with native audio playback.
- Preserve the original study workflow.

---

# Initial Target

Current test document:

```
Lesson 1-3.pdf
```

Known properties:

- PDF 1.7
- Created with Adobe InDesign CC 2015
- Uses RichMedia annotations
- Embeds:

    AudioPlayer.swf

    many lesson*.mp3 files

Current interaction:

Speaker icon

↓

RichMediaExecute

↓

AudioPlayer.swf

↓

FlashVars:

source=lessonX.mp3

↓

Embedded MP3

Desired interaction:

Speaker icon

↓

Native audio playback

↓

Embedded MP3

No Flash.

---

# Technology Stack

Python 3.12+

GUI

- PySide6

PDF

- PyMuPDF (fitz)

PDF inspection

- pikepdf

Audio

- Qt Multimedia (QMediaPlayer)

Packaging

- PyInstaller

Testing

- pytest

Formatting

- ruff
- black

---

# Project Structure

flashpdf-reader/

    PROJECT.md

    README.md

    pyproject.toml

    src/

        flashpdf/

            app.py

            main_window.py

            pdf_renderer.py

            annotation_parser.py

            asset_extractor.py

            audio_player.py

            models.py

            utils.py

    tests/

    assets/

    docs/

---

# Architecture

Application

↓

Open PDF

↓

Inspect document

↓

Locate RichMedia annotations

↓

Extract embedded assets

↓

Map annotations to audio

↓

Render page

↓

Overlay clickable regions

↓

Play audio

---

# Core Components

## pdf_renderer.py

Responsibilities

- open PDF
- render pages
- zoom
- page navigation

Uses

PyMuPDF

---

## annotation_parser.py

Responsibilities

Read

- annotations
- RichMedia
- Launch actions
- Execute actions
- rectangles
- FlashVars

Output

Python objects

Example

```python
SpeakerAnnotation(
    page=2,
    rect=(510,312,526,328),
    audio="3lesson1.mp3"
)
```

---

## asset_extractor.py

Responsibilities

Extract

- MP3
- SWF
- embedded files

Output

```
cache/

    1lesson1.mp3

    2lesson1.mp3
```

Must avoid extracting duplicates.

---

## audio_player.py

Responsibilities

Native playback

Requirements

- play
- pause
- stop
- replay
- playback speed

Backend

QMediaPlayer

---

## overlay system

Transparent clickable buttons placed over rendered PDF.

The overlay coordinates come directly from annotation rectangles.

Never hardcode positions.

---

# Phase Roadmap

## Phase 1

Project setup

- GUI window
- open PDF
- render first page

Success criteria

Application displays Lesson 1.

---

## Phase 2

PDF inspection

Discover

- embedded assets
- annotations

Generate debug output

```
Page 2

Speaker 1

Rect

Audio

3lesson1.mp3
```

---

## Phase 3

Extraction

Extract every embedded MP3

Maintain cache folder

---

## Phase 4

Audio replacement

Click speaker

↓

play MP3

No Flash involved.

---

## Phase 5

Viewer

Zoom

Scroll

Page thumbnails

Bookmarks

---

## Phase 6

Quality of life

Playback speed

Repeat sentence

Keyboard shortcuts

Dark mode

---

## Phase 7

Universal support

Automatically support any Flash-based educational PDF that follows Adobe RichMedia conventions.

No per-book configuration.

---

# Design Principles

Do not modify the original PDF.

Do not rewrite annotations.

Treat the PDF as immutable.

All interaction replacement happens in the application layer.

---

# Future Features

Sentence repeat

Loop mode

Dictionary popup

Kanji lookup

Anki export

Subtitle mode

Audio waveform

Study statistics

Bookmarks

Session restore

---

# Coding Standards

- Type hints everywhere.
- Dataclasses preferred.
- No global state.
- Keep modules under ~500 lines.
- Separate GUI from parsing logic.
- Write unit tests for parsing code.

---

# Performance Goals

PDF open

<500ms

Page render

<100ms

Speaker click latency

<50ms

Audio start

Instant

---

# Non Goals

Not a PDF editor.

Not a PDF converter.

Not a Flash emulator.

Flash is never executed.

The application extracts the information Flash used and performs the equivalent behavior natively.

---

# Development Philosophy

Whenever possible:

Do not reverse engineer Adobe.

Reverse engineer the document.

The PDF already contains all the information needed.

Our job is simply to expose it using modern libraries.

---

# Immediate Next Task

Implement

asset_extractor.py

Requirements

1. Open PDF using pikepdf.

2. Enumerate embedded files.

3. Identify

- mp3
- swf

4. Extract them into

cache/

5. Return

```python
[
    EmbeddedAsset(
        name="1lesson1.mp3",
        path="cache/1lesson1.mp3",
        mime="audio/mpeg"
    ),
    ...
]
```

After extraction succeeds, implement annotation parsing.
