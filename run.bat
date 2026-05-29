@echo off
REM Library Management System - Quick Start Script

echo.
echo ===================================
echo Library Management System
echo ===================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python from https://www.python.org/
    pause
    exit /b 1
)

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    echo Virtual environment created!
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install requirements
echo.
echo Installing dependencies...
pip install -q -r requirements.txt

REM Run the app
echo.
echo Starting Flask server...
echo.
echo ===================================
echo Server is running at:
echo http://localhost:5000
echo ===================================
echo.
echo Press Ctrl+C to stop the server
echo.

python app.py

pause
