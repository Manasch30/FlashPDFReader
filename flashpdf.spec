# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import collect_all, collect_submodules

# Collect all binaries, datas, hiddenimports for core dependencies
numpy_datas, numpy_binaries, numpy_hiddenimports = collect_all('numpy')
flashpdf_datas, flashpdf_binaries, flashpdf_hiddenimports = collect_all('flashpdf')
pikepdf_datas, pikepdf_binaries, pikepdf_hiddenimports = collect_all('pikepdf')
fitz_datas, fitz_binaries, fitz_hiddenimports = collect_all('fitz')

flex_binaries = []
flex_dir = '/usr/lib64/flexiblas'
if os.path.exists(flex_dir):
    for f in os.listdir(flex_dir):
        fp = os.path.join(flex_dir, f)
        if os.path.isfile(fp):
            flex_binaries.append((fp, 'flexiblas'))

block_cipher = None

a = Analysis(
    ['src/flashpdf/app.py'],
    pathex=['src'],
    binaries=numpy_binaries + flashpdf_binaries + pikepdf_binaries + fitz_binaries + flex_binaries,
    datas=numpy_datas + flashpdf_datas + pikepdf_datas + fitz_datas,
    hiddenimports=list(set(
        [
            'flashpdf',
            'flashpdf.app',
            'flashpdf.main_window',
            'flashpdf.pdf_renderer',
            'flashpdf.page_view_widget',
            'flashpdf.annotation_parser',
            'flashpdf.asset_extractor',
            'flashpdf.audio_player',
            'flashpdf.audio_inspector',
            'flashpdf.utils',
            'numpy',
            'pikepdf',
            'fitz',
            'PySide6',
            'PySide6.QtCore',
            'PySide6.QtGui',
            'PySide6.QtWidgets',
            'PySide6.QtMultimedia',
        ]
        + numpy_hiddenimports
        + flashpdf_hiddenimports
        + pikepdf_hiddenimports
        + fitz_hiddenimports
        + collect_submodules('flashpdf')
        + collect_submodules('numpy')
        + collect_submodules('pikepdf')
        + collect_submodules('fitz')
    )),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='FlashPDFReader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
