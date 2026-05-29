@echo off
REM Library Management System setup script

echo.
echo ===================================
echo Library Management System Setup
echo ===================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python from https://www.python.org/
    pause
    exit /b 1
)

if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

call venv\Scripts\activate.bat

echo.
echo Installing dependencies...
python -m pip install -r requirements.txt

echo.
echo Setup complete! Ready to run.
echo.
echo To start the server, run: python app.py
echo Or use: run.bat
echo.
pause
