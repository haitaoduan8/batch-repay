@echo off
echo Installing dependencies...
pip install pyinstaller flet flet-desktop requests

echo Building EXE...
pyinstaller --onefile --windowed --name "BatchRepay" --hidden-import flet.desktop batch_repay_app.py

echo.
echo Build complete! EXE is in: dist\BatchRepay.exe
pause
