@echo off
title NetSpeed Monitor Launcher
echo Starting NetSpeed Monitor...
python main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo If PyQt5 is not installed, trying lightweight Tkinter version...
    python tkinter_app.py
)
pause
