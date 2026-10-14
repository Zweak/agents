#!/usr/bin/env bash
# Start the Streamlit Web Application
set -e

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
