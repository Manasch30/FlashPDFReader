# Standalone Executable Build Guide (`pyinstaller-binary` branch)

This branch contains pre-configured build specifications for packaging **FlashPDF Reader** into a single standalone `.exe` (Windows), Linux binary, or macOS application bundle using **PyInstaller**.

> [!NOTE]
> Tested & Verified: PyInstaller packages all PySide6, PyMuPDF, pikepdf, and QtMultimedia libraries seamlessly into a single executable binary.

---

## Building on Windows

1. **Clone or checkout the `pyinstaller-binary` branch**:
   ```cmd
   git checkout pyinstaller-binary
   ```

2. **Install project dependencies & PyInstaller**:
   ```cmd
   pip install -e .
   pip install pyinstaller
   ```

3. **Run the automated build script**:
   ```cmd
   python build_exe.py
   ```
   *(Or run PyInstaller directly: `pyinstaller flashpdf.spec`)*

4. **Run your standalone app**:
   - The compiled standalone executable `FlashPDFReader.exe` will be generated in **`dist/FlashPDFReader.exe`**.
   - You can copy `FlashPDFReader.exe` anywhere—it runs without needing Python installed on the target machine!
