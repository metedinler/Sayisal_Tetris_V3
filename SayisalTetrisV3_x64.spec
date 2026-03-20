# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


base_prefix = Path(sys.base_prefix)
tcl_root = base_prefix / "tcl"
tcl_lib = tcl_root / "tcl8.6"
tk_lib = tcl_root / "tk8.6"

if tcl_lib.exists():
    os.environ["TCL_LIBRARY"] = str(tcl_lib)
if tk_lib.exists():
    os.environ["TK_LIBRARY"] = str(tk_lib)

tk_datas = []
for folder_name in ("tcl8.6", "tk8.6", "tcl8", "tix8.4.3", "dde1.4", "reg1.3", "nmake"):
    source = tcl_root / folder_name
    if source.exists():
        tk_datas.append((str(source), f"tcl/{folder_name}"))


a = Analysis(
    ['tetris_v3_windows_ai.py'],
    pathex=[],
    binaries=[],
    datas=tk_datas,
    hiddenimports=collect_submodules('tkinter') + ['_tkinter'],
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
