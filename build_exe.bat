@echo off
title Build NetSpeed Monitor Executable
echo ======================================================
echo    Building NetSpeed Monitor Standalone Executable
echo ======================================================
echo.

pip install pyinstaller psutil PyQt5 Pillow

echo.
echo Compiling main app to dist/NetSpeedMonitor.exe...
pyinstaller --noconfirm --onedir --windowed --name "NetSpeedMonitor" --icon="icon.ico" --add-data "config.py;." --add-data "network_monitor.py;." --add-data "sparkline.py;." --add-data "icon.png;." main.py

echo.
echo ======================================================
echo    Build Completed! Check the 'dist' folder.
echo ======================================================
pause
