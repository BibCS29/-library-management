#!/bin/bash

# Library Management System - Quick Start Script

echo ""
echo "==================================="
echo "Library Management System"
echo "==================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python from https://www.python.org/"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "Virtual environment created!"
fi

# Activate virtual environment
source venv/bin/activate

# Install requirements
echo ""
echo "Installing dependencies..."
pip install -q -r requirements.txt

# Run the app
echo ""
echo "Starting Flask server..."
echo ""
echo "==================================="
echo "Server is running at:"
echo "http://localhost:5000"
echo "==================================="
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python3 app.py
