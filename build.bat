@echo off
echo Installing dependencies...
pip install flet flet-desktop requests certifi

echo Building EXE with flet pack...
flet pack --name BatchRepay --onefile --windowed batch_repay_app.py

echo.
echo Build complete! EXE is in: dist\BatchRepay.exe
pause
