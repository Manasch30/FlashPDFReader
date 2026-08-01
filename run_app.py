"""Top-level launcher for PyInstaller packaging and standalone execution."""

import sys
from pathlib import Path

# Handle PyInstaller frozen bundle runtime path vs development runtime path
if getattr(sys, "frozen", False):
    bundle_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    for p in [bundle_dir, bundle_dir / "src"]:
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
else:
    root_dir = Path(__file__).resolve().parent
    src_dir = root_dir / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

from flashpdf.app import main

if __name__ == "__main__":
    main()
