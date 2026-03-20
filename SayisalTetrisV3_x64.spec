# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path


base_prefix = Path(sys.base_prefix)
tcl_root = base_prefix / "tcl"
tcl_lib = tcl_root / "tcl8.6"
tk_lib = tcl_root / "tk8.6"
py_tk_lib = base_prefix / "Lib" / "tkinter"

if tcl_lib.exists():
    os.environ["TCL_LIBRARY"] = str(tcl_lib)
if tk_lib.exists():
    os.environ["TK_LIBRARY"] = str(tk_lib)

tk_datas = []
if tcl_lib.exists():
    tk_datas.append((str(tcl_lib), "_tcl_data"))
if tk_lib.exists():
    tk_datas.append((str(tk_lib), "_tk_data"))
if py_tk_lib.exists():
    tk_datas.append((str(py_tk_lib), "tkinter"))


a = Analysis(
    ['tetris_v3_windows_ai.py'],
    pathex=[],
    binaries=[],
    datas=tk_datas,
    hiddenimports=['_tkinter'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SayisalTetrisV3_x64',
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
)
