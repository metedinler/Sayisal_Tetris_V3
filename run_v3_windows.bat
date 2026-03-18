@echo off
cd /d "%~dp0"
py tetris_v3_windows_ai.py
if errorlevel 1 (
  echo.
  echo V3 Windows oyunu baslatilirken hata olustu.
  pause
)
