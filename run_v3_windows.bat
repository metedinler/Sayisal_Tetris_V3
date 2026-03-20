@echo off
cd /d "%~dp0"
set "APP_PY=%LocalAppData%\Programs\Python\Python312\python.exe"
if exist "%APP_PY%" (
  "%APP_PY%" tetris_v3_windows_ai.py
) else (
  python tetris_v3_windows_ai.py
)
if errorlevel 1 (
  echo.
  echo V3 Windows oyunu baslatilirken hata olustu.
  pause
)
