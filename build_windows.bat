@echo off

echo building scd for windows...

pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo pyinstaller not found. installing...
    pip install pyinstaller
)

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

pyinstaller scd.spec

if %errorlevel% equ 0 (
    echo.
    echo ✓ build successful!
    echo executable: dist\scd.exe
    echo.
    echo to test:
    echo   dist\scd.exe --help
) else (
    echo ✗ build failed
    exit /b 1
)
