@echo off
echo installing scd dependencies...
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo error: python is not installed or not in path
    echo please install python 3.10 or higher from https://www.python.org/
    pause
    exit /b 1
)

echo installing required packages...
pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo error: failed to install dependencies
    pause
    exit /b 1
)

echo.
echo ========================================
echo installation complete.
echo ========================================
echo.
echo usage:
echo   python main.py ^<username^>
echo.
echo example:
echo   python main.py myusername
echo.
echo for more options, run:
echo   python main.py --help
echo.
pause
