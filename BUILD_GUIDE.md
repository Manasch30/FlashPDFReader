# Standalone Executable Build Guide

Packaging **FlashPDF Reader** into a single standalone `.exe` (Windows) or Linux binary using **PyInstaller** can be done locally or automatically in the cloud via GitHub Actions.

---

## ⚡ Method 1: Automated Builds via GitHub Actions (Recommended)

Every push or pull request to the `main` branch automatically triggers GitHub Actions to compile standalone executables for both **Windows (`.exe`)** and **Linux**.

### How to Download Pre-Built Executables:
1. Go to your repository on GitHub.
2. Click the **Actions** tab.
3. Click the latest workflow run under **Build Standalone Executables**.
4. Scroll down to **Artifacts** to download `FlashPDFReader-Windows-x64` (`.exe`) or `FlashPDFReader-Linux-x64`.

---

## 💻 Method 2: Building Locally

### Building on Windows (`FlashPDFReader.exe`)

1. **Install project dependencies & PyInstaller**:
   ```cmd
   pip install -e .
   pip install pyinstaller
   ```

2. **Run the automated build script**:
   ```cmd
   python build_exe.py
   ```

3. **Run your standalone app**:
   - The compiled executable will be created at `dist\FlashPDFReader.exe`.
   - You can copy `FlashPDFReader.exe` anywhere—it runs without needing Python installed on the target machine!

---

### Building on Linux (`FlashPDFReader`)

1. **Install project dependencies & PyInstaller**:
   ```bash
   pip install -e .
   pip install pyinstaller
   ```

2. **Run the automated build script**:
   ```bash
   python build_exe.py
   ```

3. **Run your standalone app**:
   - The compiled executable will be created at `dist/FlashPDFReader`.
   - Run directly: `./dist/FlashPDFReader`.
