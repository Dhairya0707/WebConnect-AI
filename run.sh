#!/bin/bash
# Helper script to run WebConnect AI using the virtual environment

if [ -d "venv" ]; then
    echo "--- 🚀 Launching WebConnect AI ---"
    ./venv/bin/python main.py
else
    echo "❌ Error: Virtual environment 'venv' not found."
    echo "Please run the setup commands from the README first:"
    echo "python3 -m venv venv && ./venv/bin/pip install -r requirements.txt"
    exit 1
fi
