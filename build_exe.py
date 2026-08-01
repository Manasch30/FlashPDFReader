"""Build script for creating standalone FlashPDFReader binary using PyInstaller."""

import subprocess
import sys


def main() -> None:
    print("🚀 Building FlashPDFReader standalone executable...")
    cmd = [sys.executable, "-m", "PyInstaller", "--clean", "flashpdf.spec"]
    res = subprocess.run(cmd, check=False)
    if res.returncode == 0:
        print("✅ Build successful! Executable is located in the dist/ folder.")
    else:
        print("❌ Build failed. Ensure pyinstaller is installed: pip install pyinstaller")


if __name__ == "__main__":
    main()
