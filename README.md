# 📖 FlashPDF Reader

> **Bringing Classic Interactive Flash PDFs Back to Life**

**FlashPDF Reader** is an open-source educational PDF reader and web platform that restores full audio interactivity, embedded media playback, and interactive answer layers in legacy PDFs originally created with Adobe Flash `/RichMedia` annotations.

---

## 🎯 Motivation & Purpose

For over a decade, educational publishers created interactive PDF textbooks with embedded audio buttons (`🔊`), listening comprehension exercises, and expandable answer fields (`💡 Show Answer`). These features relied on Adobe Flash Player embedded inside PDF files.

When Adobe Flash was officially deprecated, **every major PDF viewer (Adobe Acrobat, Foxit, PDF-XChange, Chrome, Edge) stripped Flash support**. As a result, millions of classic interactive textbooks and language workbooks became broken, static "dead" documents where clicking audio buttons or revealing answers no longer worked.

**FlashPDF Reader resurrects these OG interactive textbooks:**
- **Zero Flash Runtime Required**: Safely parses raw PDF `/RichMedia` annotation streams and extracts embedded MP3 audio streams directly from PDF object structures.
- **100% Non-Destructive**: Never modifies the original PDF file—all asset extraction and interactivity overlay mapping happen on-the-fly.
- **Cross-Platform Access**: Works as a native desktop application, a standalone single-file `.exe` binary, or a containerized Docker web app accessible on phones, tablets, and PCs.

---

## ✨ Key Features

- 🔊 **Native Embedded Audio Playback**: Automatically extracts embedded audio streams and renders interactive speaker buttons (`🔊`) directly on PDF pages with variable speed playback (`0.75×` to `2.0×`).
- 💡 **Universal Answer Layer Unhiding**: Generic spatial bounding-box proximity and group stem extraction engine that reveals hidden answer layers and table answer cells across any Flash textbook without hardcoded rules.
- 🌙 **Smart Dark Mode**: High-contrast pixel-level dark mode pipeline (`numpy` + `PyMuPDF`) that converts bright page backgrounds to slate (`#1e2026`) while preserving vibrant red answer text with anti-aliased edge smoothing.
- 📜 **Continuous Scroll & Single Page Modes**: Vertical page stacking synchronized with interactive thumbnail sidebar navigation.
- 📋 **Native Text Selection**: Mouse drag selection rectangle with automatic coordinate transformation for quick text copying to system clipboard.
- 🐳 **Docker & FastAPI Web Interface**: Containerized headless web server (`src/flashpdf/web_server.py`) and responsive HTML5 frontend (`src/flashpdf/static/index.html`) for streaming interactive textbooks to mobile browsers.
- 📦 **1-Click Standalone Executable**: Pre-configured PyInstaller spec (`flashpdf.spec`) and automated build script (`build_exe.py`) for creating standalone binary executables (`FlashPDFReader.exe` / `FlashPDFReader`).
- 🛠️ **Audio Inspector**: Built-in asset auditing dialog for inspecting embedded media resources and clearing extraction caches.

---

## 🚀 Quick Start

### 1. Installation

Clone the repository and install dependencies in editable mode:

```bash
git clone https://github.com/Manasch30/JReader.git
cd JReader
pip install -e ".[dev]"
```

### 2. Run Desktop App

Launch the native PySide6 desktop GUI reader:

```bash
python -m flashpdf.app
```

*(If `Lesson 1-3.pdf` is present in the working directory, it will automatically load on startup).*

---

## 📦 Standalone Executable (`build_exe.py`)

To generate a single-file executable (`.exe` on Windows or native binary on Linux) that runs without needing Python installed:

```bash
pip install pyinstaller
python build_exe.py
```

The compiled standalone binary will be created in **`dist/FlashPDFReader`** (or `dist/FlashPDFReader.exe` on Windows).

See [BUILD_GUIDE.md](BUILD_GUIDE.md) for detailed compilation instructions.

---

## 🐳 Docker Container & Web Reader

Run FlashPDF Reader as a web service accessible across all devices on your local network:

```bash
docker compose up -d
```

Open **`http://localhost:8000`** in any web browser (PC, iPad, iPhone, Android) to read textbooks, play audio, and toggle answers interactively!

---

## 🛠️ Architecture & Tech Stack

- **Core Engine**: Python 3.10+
- **PDF Parsing & Rendering**: `PyMuPDF` (`fitz`), `pikepdf`, `numpy`
- **Desktop UI**: `PySide6` (Qt 6), `QtMultimedia`
- **Web API & Frontend**: `FastAPI`, `uvicorn`, HTML5 / Vanilla CSS / JS
- **Packaging & Containerization**: `PyInstaller`, `Docker`, `docker-compose`

---

## 🧪 Running Tests & Linting

Run the automated unit test suite and strict code quality checks:

```bash
pytest
ruff check .
```

---

## 📜 License

Distributed under the MIT License. See `LICENSE` for more information.
