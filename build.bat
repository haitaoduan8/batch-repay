@echo off
echo Installing dependencies...
pip install pyinstaller flet flet-desktop requests certifi

echo Getting certifi CA bundle path...
for /f "delims=" %%i in ('python -c "import certifi; print(certifi.where())"') do set CERT_PATH=%%i
echo CA bundle: %CERT_PATH%

echo Building EXE...
pyinstaller --onefile --windowed --name "BatchRepay" --hidden-import flet.desktop --add-data "%CERT_PATH%;certifi" batch_repay_app.py

echo.
echo Build complete! EXE is in: dist\BatchRepay.exe
pause
