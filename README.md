# 📖 FlashPDF Reader

> A high-performance, cross-platform viewer designed to revive interactive legacy Flash-based educational PDFs (such as Japanese textbook series) with native audio playback, dynamic answer layer toggles, smart dark mode, and smooth continuous scrolling.

---

## ✨ Features

- **🔊 Native Audio Playback**: Automatically extracts embedded Flash MP3 assets and places clickable audio triggers (`🔊`) directly on the PDF pages.
- **💡 Universal Answer Unhiding**: Seamlessly toggles native vector answer layers (`💡 Answer` / `❌ Close`), including multi-cell tables and complex exercise blocks.
- **🌙 Smart Dark Mode**: Custom color transformation that converts white page backgrounds to dark slate (`#1e2026`), black text to white, and smooth anti-aliased red answer text (`#ff5a5a`).
- **📜 Continuous Scroll & Single Page View**: Switch effortlessly between focused single-page view and vertical continuous scrolling (`📜 Scroll Mode`).
- **🔍 Ctrl + Scroll Wheel Zoom**: Hold `Ctrl` and scroll your mouse wheel to zoom in and out smoothly (`40%` – `400%`).
- **✂️ Interactive Text Selection**: Click and drag across text to highlight and automatically copy extracted PDF text to your system clipboard (`QApplication.clipboard()`).
- **🎵 Audio File Inspector**: Dedicated audio inspector dialog to browse, preview, and inspect extracted MP3 assets.
- **⚡ Speed Control**: Adjust audio playback speed (`0.75×`, `1.0×`, `1.25×`, `1.5×`, `2.0×`).
- **📁 Isolated Caching**: Extracted audio files are cached per PDF in `cache/<pdf_name>/` to prevent asset conflicts.

---

## 📦 Download Portable Executable

Standalone portable binaries are bundled with Python, PySide6, PyMuPDF, and ffmpeg Qt Multimedia runtimes—no Python installation required!

| Platform | Download / Binary Location | Notes |
| :--- | :--- | :--- |
| **Linux (x86_64)** | `dist/flashpdf` | Portable standalone binary |
| **Windows (x64)** | `dist/flashpdf.exe` | Portable standalone binary |

To run the Linux portable binary:
```bash
./dist/flashpdf
```

---

## 🛠️ How to Compile / Build from Source

### Prerequisites
- **Python 3.10** or higher
- `pip` package manager

### 1. Clone Repository & Setup Virtual Environment
```bash
git clone https://github.com/your-username/jreader.git
cd jreader

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
pip install pyinstaller
```

### 3. Run Application from Source
```bash
PYTHONPATH=src python3 -m flashpdf.app
```

---

## 🔨 Building Portable Standalone Binaries (PyInstaller)

### Building on Linux
Run PyInstaller with the provided `flashpdf.spec`:
```bash
pyinstaller flashpdf.spec
```
The output executable will be generated at:
```
dist/flashpdf
```

### Building on Windows
1. Open PowerShell or Command Prompt in the project folder.
2. Ensure your virtual environment is activated:
   ```cmd
   venv\Scripts\activate
   ```
3. Install dependencies and PyInstaller:
   ```cmd
   pip install -r requirements.txt pyinstaller
   ```
4. Build the Windows executable:
   ```cmd
   pyinstaller flashpdf.spec
   ```
The standalone Windows binary will be created at:
```
dist\flashpdf.exe
```

---

## 🧪 Running Tests & Code Quality

Run the automated unit test suite with `pytest`:
```bash
pytest
```

Run code formatting checks with `ruff`:
```bash
ruff check .
```

---

## 📁 Project Architecture

```
jreader/
├── dist/                      # Portable executable outputs (Linux / Windows)
├── src/
│   └── flashpdf/              # Main application package
│       ├── annotation_parser.py # Parses RichMedia audio triggers & /Hide answer layers
│       ├── app.py              # Application entry point
│       ├── asset_extractor.py  # Extracts embedded MP3 assets into cache/
│       ├── audio_dialog.py     # Audio File Inspector dialog
│       ├── audio_player.py     # Qt Multimedia audio playback engine
│       ├── main_window.py      # Main GUI window, layout, and toolbar
│       ├── models.py           # Data classes (SpeakerAnnotation, AnswerLayer, etc.)
│       ├── page_view_widget.py # Individual rendered PDF page widget with overlays
│       ├── pdf_renderer.py     # PyMuPDF rendering engine & Smart Dark Mode
│       └── utils.py            # Utility functions (cache directory management)
├── tests/                     # Pytest test suite
├── flashpdf.spec              # PyInstaller compilation specification
├── pyproject.toml             # Project metadata and dependencies
├── requirements.txt           # Pip requirements file
└── README.md                  # Documentation
```

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for details.
