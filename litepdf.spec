# -*- mode: python ; coding: utf-8 -*-
# litepdf.spec  —  PyInstaller build spec
# Produces a single-file Windows executable with minimal bloat.

import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Include the app icon if present
        ('icon.ico', '.') if __import__('os').path.exists('icon.ico') else ('', '.'),
    ],
    hiddenimports=[
        'PIL._tkinter_finder',
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'tkinter.simpledialog',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Strip heavy unused stdlib modules to keep EXE slim
        'unittest', 'doctest', 'pdb', 'profile', 'cProfile',
        'distutils', 'setuptools', 'pkg_resources',
        'xml', 'xmlrpc', 'email', 'html', 'http', 'urllib',
        'multiprocessing', 'concurrent', 'asyncio',
        'numpy', 'pandas', 'scipy', 'matplotlib',
        'IPython', 'jupyter',
    ],
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
    name='LitePDF',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,                   # Compress with UPX if available
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,              # No console window (windowed app)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico' if __import__('os').path.exists('icon.ico') else None,
    version='version_info.txt' if __import__('os').path.exists('version_info.txt') else None,
)
