# 📖 FlashPDF Reader

> **Bringing Classic Interactive Flash PDFs Back to Life**

**FlashPDF Reader** is an open-source educational PDF reader that restores full audio interactivity, embedded media playback, and interactive answer layers in legacy PDFs originally built with Adobe Flash `/RichMedia` annotations.

---

## 🎯 Motivation & Story

The motivation for creating **FlashPDF Reader** came while studying for the **JLPT (Japanese Language Proficiency Test)** using free textbook resources from **Nihongo Library**. 

For years, educational publishers created interactive PDF workbooks with embedded audio listening exercises (`🔊`), dialogue buttons, and expandable answer fields (`💡 Show Answer`). These features relied on Adobe Flash Player embedded directly inside the PDF files.

When Adobe Flash was officially deprecated, **every major PDF reader (Adobe Acrobat, Foxit, PDF-XChange, Chrome, Edge) stripped Flash support**. Overnight, millions of free interactive learning materials became static, broken "dead" documents where clicking audio buttons or checking answers no longer worked.

**FlashPDF Reader was created to solve this problem:**
- **Zero Flash Runtime Required**: Safely parses raw PDF `/RichMedia` annotation streams and extracts embedded MP3 audio streams on-the-fly directly from PDF object structures.
- **100% Non-Destructive**: Never modifies original PDF files—all audio extraction and interactive overlays are rendered dynamically.
- **Made for Learners**: Gives life back to classic JLPT textbooks, language workbooks, and interactive Flash PDFs so anyone can study seamlessly without software limitations!

---

## ✨ Key Features

- 📑 **Multi-Tab PDF Reader**: Open and switch between multiple textbooks side-by-side in separate closable tabs without losing your active page position.
- 🕒 **Recent PDFs History**: Quick-access **"Recent PDFs ▾"** toolbar menu that remembers previously opened books across sessions for 1-click re-opening.
- 🔊 **Native Embedded Audio Playback**: Automatically extracts embedded audio streams and renders interactive speaker buttons (`🔊`) directly on PDF pages with variable speed playback control (`0.75×` to `2.0×`).
- 💡 **Universal Answer Layer Unhiding**: Generic spatial bounding-box proximity and group stem extraction engine that reveals hidden answer layers and table answer cells across any Flash textbook without hardcoded rules.
- 🌙 **Smart Dark Mode**: High-contrast pixel-level dark mode pipeline (`numpy` + `PyMuPDF`) that converts bright page backgrounds to slate (`#1e2026`) while preserving vibrant red answer text with anti-aliased edge smoothing.
- 📜 **Continuous Scroll & Single Page View**: Vertical page stacking synchronized with interactive thumbnail sidebar navigation.
- 📋 **Native Text Selection**: Mouse drag selection rectangle with automatic coordinate transformation for quick text copying to system clipboard.
- 📦 **1-Click Standalone Executable**: Pre-configured PyInstaller spec (`flashpdf.spec`) and automated build script (`build_exe.py`) for creating standalone single-file executables (`FlashPDFReader.exe` / `FlashPDFReader`).
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

### 2. Run Desktop Application

Launch the native PySide6 desktop GUI reader:

```bash
python -m flashpdf.app
```

*(If `Lesson 1-3.pdf` is present in the working directory, it will automatically load on startup).*

---

## 📦 Standalone Executable (`build_exe.py`)

To generate a standalone single-file executable (`.exe` on Windows or native binary on Linux) that runs without requiring Python installed:

```bash
pip install pyinstaller
python build_exe.py
```

The compiled standalone executable will be created in **`dist/FlashPDFReader`** (or `dist/FlashPDFReader.exe` on Windows).

See [BUILD_GUIDE.md](BUILD_GUIDE.md) for detailed compilation instructions.

---

## 🛠️ Tech Stack

- **GUI Framework**: `PySide6` (Qt 6), `QtMultimedia`
- **PDF Engine**: `PyMuPDF` (`fitz`), `pikepdf`
- **Image Processing**: `numpy`
- **Packaging**: `PyInstaller`

---

## 🧪 Running Tests & Linting

Run the unit test suite and code formatting checks:

```bash
pytest
ruff check .
```

---

## 📜 License

Distributed under the G.P.L License. See `LICENSE` for more information.
