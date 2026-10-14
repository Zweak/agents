#!/usr/bin/env bash
# Start the Streamlit Web Application
set -e

# Auto-activate venv if it exists
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
elif [ -f ".venv/Scripts/activate" ]; then
    source .venv/Scripts/activate
elif [ -f "venv/bin/activate" ]; then
    source "venv/bin/activate"
elif [ -f "venv/Scripts/activate" ]; then
    source "venv/Scripts/activate"
fi

echo "=================================================="
echo "🚀 Starting SQL Debugging & Optimization Agent Web UI"
echo "=================================================="

# Check if streamlit is installed
if ! command -v streamlit &> /dev/null; then
    echo "Streamlit not found in PATH. Using python -m streamlit..."
    python -m streamlit run app.py --server.headless=true
else
    streamlit run app.py
fi
