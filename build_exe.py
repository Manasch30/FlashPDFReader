"""Build script for creating standalone FlashPDFReader binary using PyInstaller."""

import subprocess
import sys


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    print("[BUILD] Building FlashPDFReader standalone executable...")
    cmd = [sys.executable, "-m", "PyInstaller", "--clean", "flashpdf.spec"]
    res = subprocess.run(cmd, check=False)
    if res.returncode == 0:
        print("[SUCCESS] Build successful! Executable is located in the dist/ folder.")
    else:
        print("[ERROR] Build failed. Ensure pyinstaller is installed: pip install pyinstaller")


if __name__ == "__main__":
    main()
